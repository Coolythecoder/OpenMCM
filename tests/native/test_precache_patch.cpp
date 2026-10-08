#include "PrecachePatch.h"
#include "SkseAbi.h"

#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>

namespace {

using openmcm::PatchResult;

void Check(bool condition, const char* description)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", description);
        std::exit(1);
    }
}

struct Memory {
    static constexpr std::uint32_t kBase = 0x96A000;
    std::array<std::uint8_t, 4096> bytes{};
    int reads = 0;
    int writes = 0;
    int begins = 0;
    int ends = 0;
    int flushes = 0;
    int unreadableSite = -1;
    int flushFailures = 0;
    int endFailures = 0;
    bool beginFailure = false;
    bool mutateOnBegin = false;
    bool writable = false;

    Memory()
    {
        bytes.fill(0xA5);
        for (const auto& site : openmcm::kSites) {
            std::copy(site.expected.begin(), site.expected.end(), bytes.begin() + site.rva - kBase);
        }
    }

    bool Read(std::uint32_t rva, std::array<std::uint8_t, 32>& value) noexcept
    {
        ++reads;
        if (unreadableSite >= 0 && rva == openmcm::kSites[static_cast<std::size_t>(unreadableSite)].rva) return false;
        if (rva < kBase || rva - kBase > bytes.size() - value.size()) return false;
        std::copy_n(bytes.begin() + rva - kBase, value.size(), value.begin());
        return true;
    }

    bool BeginWrite() noexcept
    {
        ++begins;
        if (beginFailure) return false;
        writable = true;
        if (mutateOnBegin) bytes[openmcm::kSites[1].rva - kBase] = 0xE9;
        return true;
    }

    void WriteEntry(std::uint32_t rva, std::uint8_t value) noexcept
    {
        Check(writable, "writing must require acquired page protection");
        ++writes;
        bytes[rva - kBase] = value;
    }

    bool Flush() noexcept { ++flushes; return flushes > flushFailures; }
    bool EndWrite() noexcept
    {
        ++ends;
        if (ends <= endFailures) return false;
        writable = false;
        return true;
    }
};

PatchResult Apply(Memory& memory)
{
    return openmcm::ApplyPrecachePatch(memory, openmcm::kSupportedRuntime, true, false);
}

} // namespace

int main()
{
    int cases = 0;
    {
        Memory memory;
        auto expected = memory.bytes;
        for (const auto& site : openmcm::kSites) expected[site.rva - Memory::kBase] = openmcm::kReturn;
        Check(Apply(memory) == PatchResult::Applied, "verified runtime applies paired patch");
        Check(memory.bytes == expected, "only the TWO entry bytes change; selected-head loader/page retained");
        Check(memory.writes == 2 && memory.flushes == 1 && memory.ends == 1 && !memory.writable,
              "successful patch restores protection and flushes instructions");
        Check(Apply(memory) == PatchResult::UnexpectedBytes, "duplicate application does not rewrite existing returns");
        Check(memory.bytes == expected && memory.writes == 2, "duplicate application is non-mutating");
        ++cases;
    }
    for (const auto runtime : {0U, 0x01064920U, 0x01070630U, 0x01070681U, 0x01070690U}) {
        Memory memory;
        const auto before = memory.bytes;
        Check(openmcm::ApplyPrecachePatch(memory, runtime, true, false) == PatchResult::UnsupportedRuntime,
              "unknown, older, newer and non-Steam runtimes are rejected");
        Check(memory.reads == 0 && memory.begins == 0 && memory.bytes == before, "version guard precedes memory access");
        ++cases;
    }
    {
        Memory memory;
        Check(openmcm::ApplyPrecachePatch(memory, openmcm::kSupportedRuntime, false, false) == PatchResult::Disabled,
              "configuration disables patch");
        Check(memory.reads == 0 && memory.writes == 0, "disabled component performs no code access");
        ++cases;
    }
    {
        Memory memory;
        Check(openmcm::ApplyPrecachePatch(memory, openmcm::kSupportedRuntime, true, true) == PatchResult::OtherProvider,
              "other precache provider is respected");
        Check(memory.reads == 0 && memory.writes == 0, "competing provider prevents code access");
        ++cases;
    }
    // Every byte of BOTH signatures must be checked, not just the prologue.
    for (const auto& site : openmcm::kSites) {
        for (std::size_t i = 0; i < site.expected.size(); ++i) {
            Memory memory;
            memory.bytes[site.rva - Memory::kBase + i] ^= 0xFF;
            const auto before = memory.bytes;
            Check(Apply(memory) == PatchResult::UnexpectedBytes, "any signature mismatch rejects entire pair");
            Check(memory.bytes == before && memory.begins == 0 && memory.writes == 0,
                  "mismatched second site must not partially patch first site");
            ++cases;
        }
    }
    for (int site = 0; site != 2; ++site) {
        Memory memory;
        memory.unreadableSite = site;
        const auto before = memory.bytes;
        Check(Apply(memory) == PatchResult::Unreadable, "unmapped/non-executable/truncated target rejected");
        Check(memory.bytes == before && memory.begins == 0, "unreadable target cannot trigger writes");
        ++cases;
    }
    {
        Memory memory;
        memory.beginFailure = true;
        const auto before = memory.bytes;
        Check(Apply(memory) == PatchResult::ProtectionFailed, "failed protection acquisition is safe");
        Check(memory.bytes == before && memory.writes == 0 && !memory.writable, "no partial write after protection failure");
        ++cases;
    }
    {
        Memory memory;
        memory.mutateOnBegin = true;
        auto expected = memory.bytes;
        expected[openmcm::kSites[1].rva - Memory::kBase] = 0xE9;
        Check(Apply(memory) == PatchResult::ChangedDuringPreparation, "changes during protection acquisition are respected");
        Check(memory.bytes == expected && memory.writes == 0 && !memory.writable, "do not roll back somebody else's change");
        ++cases;
    }
    for (int failures = 1; failures <= 2; ++failures) {
        Memory memory;
        memory.mutateOnBegin = true;
        memory.endFailures = failures;
        auto expected = memory.bytes;
        expected[openmcm::kSites[1].rva - Memory::kBase] = 0xE9;
        Check(Apply(memory) == (failures == 1 ? PatchResult::ChangedDuringPreparation : PatchResult::RollbackFailed),
              "changed-code branch retries protection without claiming application");
        Check(memory.bytes == expected && memory.writes == 0 && memory.ends == 2,
              "protection-only recovery cannot overwrite a competing patch");
        Check(memory.writable == (failures == 2), "failed protection retry must not be reported as restored");
        ++cases;
    }
    {
        Memory memory;
        memory.flushFailures = 1;
        const auto before = memory.bytes;
        Check(Apply(memory) == PatchResult::FlushFailed, "instruction cache failure triggers rollback");
        Check(memory.bytes == before && memory.writes == 4 && !memory.writable, "rollback restores both entries and protection");
        ++cases;
    }
    {
        Memory memory;
        memory.endFailures = 1;
        const auto before = memory.bytes;
        Check(Apply(memory) == PatchResult::ProtectionRestoreFailed, "failed protection restore triggers rollback and retry");
        Check(memory.bytes == before && memory.writes == 4 && memory.ends == 2 && !memory.writable,
              "rollback retries protection after restoring both entries");
        ++cases;
    }
    for (int mode = 0; mode != 2; ++mode) {
        Memory memory;
        if (mode == 0) memory.flushFailures = 2;
        else memory.endFailures = 2;
        const auto before = memory.bytes;
        Check(Apply(memory) == PatchResult::RollbackFailed, "repeated OS failure is not misreported as success");
        Check(memory.bytes == before && memory.writes == 4, "original byte pair retained even if OS rollback operation fails");
        ++cases;
    }
    std::printf("PASS: %d native precache-patch cases; x64 SKSE ABI layout assertions passed\n", cases);
    return 0;
}
