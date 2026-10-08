# OpenMCM 1.0.1-rc.2 — input ownership correction, not crash-verified

## Confirmed defect and correction

OpenMCM used SKSE's shared text-input counter as though it were a Boolean:
ordinary dialog redraws and Journal unloads called `AllowTextInput(false)`
without a matching acquisition. Text acceptance/cancellation also released
once before the callback and again during teardown. This could consume another
menu's outstanding text-input request.

The panel now tracks its own acquisition and releases it idempotently. The
bridge reports whether it was actually available; failed acquisition/release
does not falsely change ownership. Cleanup after a callback cannot consume a
request that another menu acquired during that callback. Existing focus and
remapping behavior is unchanged.

References: the local SkyUI 6 TextInputDialog and SearchWidget use paired
acquisition/release; [SKSE's implementation](https://github.com/ianpatt/skse64/blob/master/skse64/GameInput.cpp)
confirms that the underlying API changes a shared counter.

## What remains unresolved

The user reported a new-game crash and a whole-image freeze that clears when
Ctrl is pressed. Deployed files matched rc.1. No Skyrim crash dump or matching
Windows fault record was found; SKSE initialization/save logs are not a crash
stack. Crash Logger was present in Vortex staging but absent from the active
SKSE plugin load log.

There is no evidence yet connecting the input ownership defect to the whole-game
freeze or crash. This candidate is built for verification only and is not
deployed automatically. Do not publish it as a crash/stall fix or remove other
mods based on this source audit.

The original registration ABI, saved-field layout, plugin identities, provider
requirements, and rc.1 registration optimizations are unchanged. Automated
input tests execute actual AS2 method bodies with a mocked SKSE counter; they
do not reproduce Skyrim, native input, rendering, or crash behavior.

## Prepared local hang capture

`scripts/Capture-SkyrimHang.ps1` can capture two mini dumps of the running,
configured Skyrim executable after the user reproduces the freeze, before Ctrl
clears it. It verifies the hash and Microsoft signature of ProcDump 12.01,
uses process-clone snapshots, and writes only to a uniquely named local folder
under `build/diagnostics`. It does not start Skyrim, change game files, install
a system-wide debugger, overwrite earlier dumps, or upload anything. Dumps
can contain game-process data and should remain local unless sharing is
explicitly approved. Preparing the tool does not start capture or monitoring.

[Microsoft's ProcDump documentation](https://learn.microsoft.com/en-us/sysinternals/downloads/procdump)
describes its snapshot, hang, and exception capture modes.
