# Character-creation stall: captured cause and remaining verification

Status: native wait chain identified; the user authorized incorporating the
targeted fix into OpenMCM. Version 1.0.1-rc.3 adds an optional, guarded native
component. No game fix has been installed or verified in-game by this build.
Do not describe the earlier input-ownership fix as a fix for this captured
stall, or describe the new candidate as a confirmed fix for every crash.

## Evidence

Two local ProcDump snapshots of Skyrim 1.7.104, PID 20000, were captured on
2026-09-06 at approximately 08:42 while the user reported the entire picture
frozen. The user subsequently had to close the game; Ctrl did not resolve this
instance. Dumps are private and must not be uploaded.

Location: `build/diagnostics/skyrim-hang-20260906-084226-447/`.
Files: `SkyrimSE.exe_260906_084227.dmp` and
`SkyrimSE.exe_260906_084231.dmp`.

- Main thread 16184 waits indefinitely for unnamed event `0x1078`, through
  executable RVA `0x6568f8` and the tail-call helper `0xec1dd0(0, 2)`.
- Worker thread 38952 is inside the UI job at RVA `0x6e4e80`. That job signals
  event 2 in its current thread-local event bank after completing UI processing.
  The captured TLS bank is 0, matching the event awaited by the main thread.
- The worker is executing `RaceSexMenu::PostCreate`: address-library ID
  215885 maps its vtable to RVA `0x197edb0`; virtual slot 2 points to
  `0x967d40`, which is present in the captured call chain.
- Its routine at `0x96ab10` enumerates head parts, checks race/gender flags,
  and synchronously loads qualifying models through `0x96a860`.
- The pending model path is `meshes\KS Hairdo's\Enchantress.nif`.
  While processing the model queue, the active `NiStream.inputFilePath`
  changes from `data\MESHES\KS Hairdo's\Butterfly101.nif` to
  `data\MESHES\KS Hairdo's\Sugar.nif` between snapshots. These are live
  buffers validated against the loader's stack layout, not simply arbitrary
  strings found somewhere in process memory.
- Another model-loading thread is in `BSShaderManager::GetTexture`
  (ID 105640, RVA `0x14ec0a0`), with stack buffers identifying
  `textures\ks hairdo's\hello_n.dds` and `HelloHl.nif`.

Primary local evidence is in `wait-semantic-2.txt`, `wait-semantic-5.txt`,
`wait-semantic-6.txt`, `wait-semantic-7.txt`, `wait-semantic-second.txt`,
`asset-paths-first.txt`, and `texture-load-0908.txt` in the capture directory.
`build/diagnostics/map_offsets.py` provides offline address/vtable lookup.

Conclusion: the captured main-thread stall is the vanilla character menu
waiting for bulk head-part precaching, including KS Hairdos assets. Loading
was still progressing. This does not establish corrupt assets, a disk fault,
a permanent deadlock, or the cause of every separately reported crash.

OpenMCM's source review found no additional provable defect responsible for
this path. The captured and installed rc.2 package has no RaceSexMenu
replacement or native DLL. Both installed OpenMCM manager PEX and Journal SWF
still matched rc.2 on September 8.
Other installed mods have changed since the capture, so a new symptom may
need new evidence.

## Targeted remedy and scope boundary

The remedy to test is disabling all-headparts character-creation precaching
while preserving on-demand loading of the selected head. This is an engine/
character-menu fix, not an MCM registration or ActionScript fix.

RaceMenu's author documents a precache fix including gender changes:
https://www.nexusmods.com/skyrimspecialedition/mods/19080
Its current Nexus main file explicitly targets game 1.6.1170, not 1.7.104:
https://www.nexusmods.com/skyrimspecialedition/mods/19080?tab=files
Engine Fixes documents DisableChargenPrecache:
https://www.nexusmods.com/skyrimspecialedition/mods/17230
Neither RaceMenu nor Engine Fixes was loaded in the captured session.
Do not enable an incompatible DLL or bypass its version check.

The user subsequently requested that the fix be incorporated into this mod.
The rc.3 package therefore includes `OpenMCMRuntime.dll` and
`OpenMCMRuntime.ini` in `Data/SKSE/Plugins`. The MCM core remains independent
of this optional native component. Building the package does not install it,
alter any hair assets, or change the load order.

The candidate supports only Skyrim 1.7.104.0 and verifies the original
instructions before applying its in-memory patch. Unsupported runtimes and
unrecognized bytes are not patched. A loaded `skee64.dll` or
`EngineFixes.dll` also disables this component's patch to avoid combining
implementations. The check runs after native plugins load and before game UI
creation, without a periodic, input, or slider hook.

`[Patches] DisableChargenPrecache=1` is the packaged default. Setting it to
`0` and restarting, or omitting this DLL, restores normal engine precaching
without affecting the MCM host. It preserves selected-head loading on demand;
it does not promise instantaneous loading of every modded model. On a
supported runtime, inspect `Documents/My Games/Skyrim Special Edition/SKSE/
OpenMCMRuntime.log` for the applied/disabled result. An unsupported runtime can
be rejected by SKSE before the component's logger starts.

Required in-game validation remains: new-game character-menu entry, repeated
sex changes, hair selection, face/body sliders, normal interfaces, and MCM
registration/page/dialog operation. Confirm the patch status in the log.
The captured loading sequence does not establish the cause of a separate
crash, so do not claim that crash has been fixed without new evidence.

### Implemented patch and offline verification

The paired one-byte entry patches are `0x96AB10 -> C3` (bulk precache,
address-library ID 52369) and `0x96ADA0 -> C3` (precache cleanup, ID 52381).
Both routines have void return semantics. Initial `PostCreate` calls the first;
the registered `ChangeRace` and `ChangeSex` callbacks call cleanup then
precache. The underlying selected-head loader at `0x96A860` is unchanged.
Upstream Engine Fixes also disables this pair; this implementation does not
copy its code or fill the rest of either routine with trap instructions.

All 32 expected bytes at each site were independently compared with the
installed executable through its PE section mappings. Both matched exactly.
SKSE ABI sizes, field offsets, metadata and messaging IDs were checked against
the local official SKSE 2.3.1 SDK. That SDK dispatches `PostPostLoad` during
its pre-WinMain initialization, after all plugin Load/PostLoad callbacks and
before character UI creation. The patch uses this one-time callback.

The native transaction suite passes 82 cases, including every byte of both
signatures, wrong versions/distributions, other providers, repeated application,
changed code during preparation, OS protection/cache failures and rollback.
The complete Python suite passes 149 tests with one explicitly skipped live
package integration test; separate checks inspect the actual staged and zipped
MCM and native artifacts. These are offline checks, not a live Skyrim test.

Source: `src/native/`; native build, test executable, symbols and logs:
`build/native/`. Release candidate: `dist/OpenMCM-1.0.1-rc.3.zip`.
No installed game files, Vortex staging files, load order or saves were changed.

## Diagnostic tooling

The capture wrapper now verifies dump file structure rather than reporting
failure solely because ProcDump returned code 2 after writing two valid files.
Nine regression tests pass, and both original dumps validate. Optional full
memory/direct capture modes are available if needed, but were not executed.
Full dumps contain private data and may occupy several GB; direct capture
may pause the game. No new capture is required merely to repeat the evidence
already established above.
