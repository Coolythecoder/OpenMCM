#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <ShlObj.h>

#include <cstdio>
#include <cstring>
#include <filesystem>
#include <string>
#include <system_error>

#include "PrecachePatch.h"
#include "SkseAbi.h"

#ifndef OPENMCM_VERSION_STRING
#define OPENMCM_VERSION_STRING "2.1.0"
#endif
#ifndef OPENMCM_VERSION_PACKED
// SKSE/CommonLib packed version: major:8, minor:8, patch:12, build:4.
#define OPENMCM_VERSION_PACKED 0x02010000u
#endif

namespace {

std::FILE* g_log = nullptr;
int g_moduleAnchor = 0;
std::uint32_t g_runtime = 0;
bool g_enabled = false;
bool g_startupHandled = false;

void Log(const char* message) noexcept
{
    if (g_log) {
        std::fprintf(g_log, "%s\n", message);
        std::fflush(g_log);
    }
    OutputDebugStringA("[OpenMCMRuntime] ");
    OutputDebugStringA(message);
    OutputDebugStringA("\n");
}

void OpenLog()
{
    PWSTR documents = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_Documents, KF_FLAG_DEFAULT, nullptr, &documents))) return;
    const std::filesystem::path directory = std::filesystem::path(documents) /
        L"My Games" / L"Skyrim Special Edition" / L"SKSE";
    CoTaskMemFree(documents);
    std::error_code error;
    std::filesystem::create_directories(directory, error);
    if (!error) _wfopen_s(&g_log, (directory / L"OpenMCMRuntime.log").c_str(), L"w");
}

bool ReadConfiguration()
{
    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(&g_moduleAnchor), &module)) {
        Log("DISABLED: cannot resolve plugin's own configuration path");
        return false;
    }
    std::wstring path(32768, L'\0');
    const DWORD length = GetModuleFileNameW(module, path.data(), static_cast<DWORD>(path.size()));
    if (!length || length >= path.size()) return false;
    path.resize(length);
    auto config = std::filesystem::path(path).replace_extension(L".ini");
    wchar_t value[16]{};
    // Missing/invalid configuration is conservative: no engine modification.
    GetPrivateProfileStringW(L"Patches", L"DisableChargenPrecache", L"0",
                             value, static_cast<DWORD>(std::size(value)), config.c_str());
    if (std::wcscmp(value, L"1") == 0) return true;
    if (std::wcscmp(value, L"0") != 0) Log("DISABLED: invalid DisableChargenPrecache value (expected 0 or 1)");
    return false;
}

class ImageMemory {
public:
    ImageMemory() noexcept : base_(reinterpret_cast<std::uint8_t*>(GetModuleHandleW(nullptr))) {}

    bool Read(std::uint32_t rva, std::array<std::uint8_t, 32>& bytes) const noexcept
    {
        if (!ValidImage(rva, bytes.size())) return false;
        MEMORY_BASIC_INFORMATION region{};
        const auto address = base_ + rva;
        if (!VirtualQuery(address, &region, sizeof(region)) || region.State != MEM_COMMIT ||
            region.Type != MEM_IMAGE || region.AllocationBase != base_ ||
            (region.Protect & (PAGE_GUARD | PAGE_NOACCESS)) != 0) return false;
        const DWORD access = region.Protect & 0xFF;
        if (access != PAGE_EXECUTE_READ && access != PAGE_EXECUTE_READWRITE &&
            access != PAGE_EXECUTE_WRITECOPY) return false;
        const auto offset = reinterpret_cast<std::uintptr_t>(address) -
                            reinterpret_cast<std::uintptr_t>(region.BaseAddress);
        if (offset > region.RegionSize || bytes.size() > region.RegionSize - offset) return false;
        std::memcpy(bytes.data(), address, bytes.size());
        return true;
    }

    bool BeginWrite() noexcept
    {
        // Both audited entries belong to the same Windows page; do not combine
        // pages with different protections or restore one page twice.
        SYSTEM_INFO info{};
        GetSystemInfo(&info);
        const auto first = reinterpret_cast<std::uintptr_t>(base_ + openmcm::kSites[0].rva);
        const auto last = reinterpret_cast<std::uintptr_t>(base_ + openmcm::kSites[1].rva);
        if (!info.dwPageSize || first / info.dwPageSize != last / info.dwPageSize) return false;
        return VirtualProtect(base_ + openmcm::kSites[0].rva, Span(),
                              PAGE_EXECUTE_READWRITE, &oldProtection_) != FALSE;
    }

    void WriteEntry(std::uint32_t rva, std::uint8_t byte) noexcept
    {
        *reinterpret_cast<volatile std::uint8_t*>(base_ + rva) = byte;
    }

    bool Flush() const noexcept
    {
        return FlushInstructionCache(GetCurrentProcess(), base_ + openmcm::kSites[0].rva, Span()) != FALSE;
    }

    bool EndWrite() const noexcept
    {
        DWORD discarded = 0;
        return VirtualProtect(base_ + openmcm::kSites[0].rva, Span(), oldProtection_, &discarded) != FALSE;
    }

private:
    static constexpr SIZE_T Span() noexcept
    {
        return openmcm::kSites[1].rva - openmcm::kSites[0].rva + 1;
    }

    bool ValidImage(std::uint32_t rva, std::size_t length) const noexcept
    {
        if (!base_) return false;
        // The Windows loader already validated this mapped main executable.
        const auto dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base_);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew < 0 || dos->e_lfanew > 0x1000) return false;
        const auto nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(base_ + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64 ||
            nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) return false;
        if (rva > nt->OptionalHeader.SizeOfImage || length > nt->OptionalHeader.SizeOfImage - rva) return false;
        const auto sections = IMAGE_FIRST_SECTION(nt);
        for (WORD i = 0; i < nt->FileHeader.NumberOfSections; ++i) {
            const auto& section = sections[i];
            if (rva >= section.VirtualAddress && rva - section.VirtualAddress < section.Misc.VirtualSize &&
                length <= section.Misc.VirtualSize - (rva - section.VirtualAddress)) {
                return (section.Characteristics & IMAGE_SCN_MEM_EXECUTE) != 0;
            }
        }
        return false;
    }

    std::uint8_t* base_;
    DWORD oldProtection_ = 0;
};

void OnSkseMessage(openmcm::skse::Message* message) noexcept
{
    if (!message || !message->sender || std::strcmp(message->sender, "SKSE") != 0 ||
        message->type != openmcm::skse::kPostPostLoad || g_startupHandled) return;
    g_startupHandled = true;
    // All plugin Load/PostLoad callbacks have finished; caches cannot yet exist.
    // Conservatively defer even if that other provider's own patch is disabled.
    const bool otherProvider = GetModuleHandleW(L"skee64.dll") != nullptr ||
                               GetModuleHandleW(L"EngineFixes.dll") != nullptr;
    ImageMemory memory;
    Log(openmcm::Describe(openmcm::ApplyPrecachePatch(memory, g_runtime, g_enabled, otherProvider)));
}

} // namespace

extern "C" {

__declspec(dllexport) openmcm::skse::VersionData SKSEPlugin_Version = {
    1, OPENMCM_VERSION_PACKED, "OpenMCMRuntime", "OpenMCM contributors", "",
    0, 0, {openmcm::kSupportedRuntime, 0}, 0
};

__declspec(dllexport) bool SKSEPlugin_Load(const openmcm::skse::Interface* skse) noexcept
{
    // No DllMain work, worker thread, polling, UI hook, Papyrus or save data.
    try {
        OpenLog();
        Log("OpenMCMRuntime " OPENMCM_VERSION_STRING " (optional startup-only precache patch)");
        if (!skse || skse->isEditor || skse->runtimeVersion != openmcm::kSupportedRuntime) {
            Log(openmcm::Describe(openmcm::PatchResult::UnsupportedRuntime));
            return true; // defensive guard if a loader ignores version metadata
        }
        g_runtime = skse->runtimeVersion;
        g_enabled = ReadConfiguration();
        if (!g_enabled) {
            Log(openmcm::Describe(openmcm::PatchResult::Disabled));
            return true;
        }
        if (!skse->queryInterface || !skse->getPluginHandle) {
            Log("SKIPPED: SKSE messaging API unavailable");
            return true;
        }
        const auto messaging = static_cast<const openmcm::skse::Messaging*>(
            skse->queryInterface(openmcm::skse::kMessagingInterface));
        if (!messaging || messaging->interfaceVersion < 2 || !messaging->registerListener ||
            !messaging->registerListener(skse->getPluginHandle(), "SKSE", OnSkseMessage)) {
            Log("SKIPPED: cannot register startup message; no patch applied");
            return true;
        }
        Log("READY: waiting for SKSE PostPostLoad before validating both precache entries");
    } catch (...) {
        Log("SKIPPED: native initialization failed; MCM core remains independent");
    }
    return true;
}

} // extern "C"
