# Exit-to-desktop crash — 2026-09-08

## Evidence and scope

The reported crash is recorded by trainwreck 1.4.0 in
`Documents/My Games/Skyrim Special Edition/SKSE/Crashlogs/2026-09-08-14-56-16.log`
on Skyrim 1.7.104. The user confirmed it happened when exiting to desktop,
not while clicking an MCM. The mouse-input problem is being investigated
separately.

The fault is an access violation at `SkyrimSE.exe+0x199FC3`:

```text
cmp dword ptr [rdi], eax
RDI = 0x1F8
```

The logger produced a text report, not a crash dump. Function identities and
instruction flow were checked against the installed executable and its
1.7.104 address library. Earlier hang dumps were used only as an offline
debugger context for reading the same executable's instructions; their
registers and heap contents are not evidence about this later crash.

## Resolved sequence

1. The main loop tests `Main.quitGame` at `0x651494`. Its quit branch calls
   the whole-game teardown routine at `0x654610`, from `0x6514AE`.
2. Late in teardown, `0x6553A8` calls `0x227C10`, which walks the global
   reference-handle table and releases remaining objects.
3. The captured stack enters the `Character` destructor at `0x73ABC0`,
   the `Actor` destructor at `0x670E20`, and its pre-destruction/clear-data
   path. It eventually calls `Actor::Set3D` at `0x6715D0`, then
   `TESObjectREFR::Set3D` at `0x2EAD30`.
4. While clearing the actor's old 3D, `0x2EB1B8` loads the first
   `BSShaderManager::State.shadowSceneNode` pointer from `0x20D68B0` and
   `0x2EB1BF` calls the scene-removal routine at `0x150E1F0`.
5. That routine calculates its spinlock address with
   `lea rdx, [rcx+0x1F8]` at `0x150E218`. The lock guard at `0x199FA0`
   copies that address to `rdi` and faults on the comparison above.

The crash registers and this straight-line instruction sequence establish
that the scene-removal routine received a null scene pointer. It tried to
lock address `0x1F8` while destroying a character that still had a
`BSFadeNode`. This is a shutdown-lifetime/order failure, not a Scaleform
button handler fault.

## What this does and does not establish

The exception stack contains no OpenMCM, Scaleform, or third-party native
plugin frames. That observation does **not** prove that every mod is
unrelated: an earlier lifetime or timing change can affect later teardown.
The text log does not identify which character retained its 3D, why it was
still present during late handle-table cleanup, or which component caused
that state. There is no proven causal mod or offending asset.

`OpenMCMRuntime.log` identifies release candidate 1.0.1-rc.4 and reports the
paired character-creation precache patch as applied. The patch only returns
early from the bulk precache routine (`0x96AB10`) and its resource-cache
cleanup routine (`0x96ADA0`). That cleanup normally releases three
model/resource arrays at `0x32584A0`, `0x32584B8`, and `0x32584D0`; it does
not itself destroy Actors or ShadowSceneNodes. No direct connection to the
captured actor-teardown crash was found. Indirect effects remain untested.

Engine Fixes has a similarly named ShadowSceneNode null-pointer fix, but
its source targets address-library ID 106342 plus `0x16`, before a virtual
call through `rax+0x18`. This crash instead passes through ID 106339 and
the null object's lock at offset `0x1F8`. The similarly named fix must not
be represented as a verified remedy for this report. See the
[primary implementation](https://github.com/aers/EngineFixesSkyrim64/blob/master/src/fixes/shadowscenenode_nullptr_crash.h).

No production crash patch was added. Skipping arbitrary teardown calls or
terminating the process early would mask this failure without establishing
correct object cleanup.

## Targeted comparison test

This test isolates the optional precache patch while leaving the same MCM
host, other mods, load order, and saved game in place. It is a proposed
in-game test; it has not been performed automatically.

1. Preserve the existing crash report and `OpenMCMRuntime.log` before
   launching again; the runtime log is replaced on each startup.
2. With Skyrim fully closed, edit OpenMCM's deployed
   `Data/SKSE/Plugins/OpenMCMRuntime.ini` through the mod manager's normal
   configuration workflow. Preserve its original value, then set:

   ```ini
   [Patches]
   DisableChargenPrecache=0
   ```

3. Redeploy if required by the mod manager. Launch Skyrim, load the same
   existing saved game, perform the same short interaction sequence, and
   exit to desktop normally. Do not save over the test save. Check that
   `OpenMCMRuntime.log` reports `DISABLED`, and retain any new crash report.
   Disabling this setting leaves the MCM interface and registration intact;
   ordinary engine character-creation precaching is restored.
4. Fully close the game, restore `DisableChargenPrecache=1`, redeploy if
   needed, and repeat the same saved-game sequence. Confirm `APPLIED` in
   the new runtime log and preserve that result separately.
5. Compare the fault stacks, not just whether a logger file exists. A
   reproducible difference isolates a useful variable; one successful exit
   does not establish that an intermittent crash is fixed. Do not combine
   this comparison with other plugin or load-order changes.

If the same exit crash occurs with the precache patch disabled, that is
evidence against this optional patch being necessary for the failure. If
it only reproduces with the patch enabled, investigate its resource
lifetimes before shipping another native change. Neither result alone
identifies a different mod as responsible.

## Local verification artifacts

Offline disassembly is retained in these workspace files:

- `build/diagnostics/crash-disassembly-0908-a.txt`
- `build/diagnostics/crash-disassembly-0908-b.txt`
- `build/diagnostics/crash-precache-lifecycle-0908.txt`

No installed game files, Vortex staging files, load order, or saves were
changed during this investigation. No crash report or process memory was
uploaded.
