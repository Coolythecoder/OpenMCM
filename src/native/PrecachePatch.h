#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace openmcm {

// SKSE's packed executable version, including the distribution sub-version.
inline constexpr std::uint32_t kSupportedRuntime = 0x01070680; // Steam 1.7.104.0
inline constexpr std::uint8_t kReturn = 0xC3;

struct PatchSite {
    std::uint32_t rva;
    std::array<std::uint8_t, 32> expected;
};

// Verified against the owner's 1.7.104 executable and two captured UI stacks.
// Both functions return void. ChangeRace/ChangeSex call Clear then Precache;
// PostCreate calls Precache. Leave the selected-head loader (0x96A860) intact.
// Only entry bytes are replaced: no game structures, wait hooks or detours.
inline constexpr std::array<PatchSite, 2> kSites{{
    {0x96AB10, {0x48, 0x83, 0xEC, 0x48, 0x48, 0x8B, 0x0D, 0x5D,
                0x5C, 0x8C, 0x02, 0x48, 0x85, 0xC9, 0x0F, 0x84,
                0x81, 0x01, 0x00, 0x00, 0xE8, 0xA7, 0x31, 0xD3,
                0xFF, 0x48, 0x85, 0xC0, 0x0F, 0x84, 0x73, 0x01}},
    {0x96ADA0, {0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83,
                0xEC, 0x20, 0x48, 0x8B, 0x1D, 0xEF, 0xD6, 0x8E,
                0x02, 0x48, 0x85, 0xDB, 0x74, 0x28, 0x8B, 0x05,
                0xF4, 0xD6, 0x8E, 0x02, 0x85, 0xC0, 0x74, 0x14}}
}};

enum class PatchResult {
    Applied, Disabled, UnsupportedRuntime, OtherProvider, Unreadable,
    UnexpectedBytes, ProtectionFailed, ChangedDuringPreparation,
    FlushFailed, ProtectionRestoreFailed, RollbackFailed
};

inline const char* Describe(PatchResult result) noexcept
{
    switch (result) {
    case PatchResult::Applied: return "APPLIED: bulk chargen precache and its cleanup disabled; selected-head loading unchanged";
    case PatchResult::Disabled: return "DISABLED: DisableChargenPrecache is not enabled";
    case PatchResult::UnsupportedRuntime: return "SKIPPED: unsupported runtime (only Steam 1.7.104.0 is verified)";
    case PatchResult::OtherProvider: return "SKIPPED: RaceMenu/Engine Fixes module present; no overlapping patch attempted";
    case PatchResult::Unreadable: return "SKIPPED: target is not readable executable image memory";
    case PatchResult::UnexpectedBytes: return "SKIPPED: unexpected code or existing patch; neither entry modified";
    case PatchResult::ProtectionFailed: return "SKIPPED: cannot acquire write protection; neither entry modified";
    case PatchResult::ChangedDuringPreparation: return "SKIPPED: code changed during preparation; neither entry modified";
    case PatchResult::FlushFailed: return "FAILED: instruction-cache flush failed; both original entries restored";
    case PatchResult::ProtectionRestoreFailed: return "FAILED: protection restore failed; original entries restored and protection retried";
    case PatchResult::RollbackFailed: return "ERROR: rollback cache/protection operation failed; memory state requires investigation (patch not reported as applied)";
    }
    return "ERROR: unknown patch result";
}

// The production backend only grants write access to one verified executable
// page. The same transaction runs against a fake backend in the native tests.
// Call once at SKSE PostPostLoad, before any character menu/cache can exist.
template<class Memory>
PatchResult ApplyPrecachePatch(Memory& memory, std::uint32_t runtime,
                              bool enabled, bool otherProvider) noexcept
{
    if (!enabled) return PatchResult::Disabled;
    if (runtime != kSupportedRuntime) return PatchResult::UnsupportedRuntime;
    if (otherProvider) return PatchResult::OtherProvider;
    for (const auto& site : kSites) {
        std::array<std::uint8_t, 32> actual{};
        if (!memory.Read(site.rva, actual)) return PatchResult::Unreadable;
        if (actual != site.expected) return PatchResult::UnexpectedBytes;
    }
    if (!memory.BeginWrite()) return PatchResult::ProtectionFailed;
    // Do not overwrite a competing change between validation and protection.
    for (const auto& site : kSites) {
        std::array<std::uint8_t, 32> actual{};
        if (!memory.Read(site.rva, actual) || actual != site.expected) {
            // No code belongs to us here: retain the competing change and
            // retry protection restoration without writing either entry.
            return (memory.EndWrite() || memory.EndWrite())
                ? PatchResult::ChangedDuringPreparation : PatchResult::RollbackFailed;
        }
    }
    for (const auto& site : kSites) memory.WriteEntry(site.rva, kReturn);
    const bool flushed = memory.Flush();
    if (flushed && memory.EndWrite()) return PatchResult::Applied;

    // BeginWrite succeeded; a failed VirtualProtect restore leaves that page
    // writable. Roll back BOTH entry bytes before retrying cache/protection.
    for (const auto& site : kSites) memory.WriteEntry(site.rva, site.expected[0]);
    const bool rollbackFlushed = memory.Flush();
    const bool restored = memory.EndWrite();
    if (!rollbackFlushed || !restored) return PatchResult::RollbackFailed;
    return flushed ? PatchResult::ProtectionRestoreFailed : PatchResult::FlushFailed;
}

} // namespace openmcm
