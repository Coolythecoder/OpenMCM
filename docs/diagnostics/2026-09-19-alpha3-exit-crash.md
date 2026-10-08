# Alpha.3 exit-to-desktop crash report reviewed 2026-09-19

## Identifying the supplied report

The user supplied a trainwreck 1.4.0 report for Skyrim Steam 1.7.104 after
exiting to desktop. After normalizing line endings and trimming trailing
whitespace, it exactly matches the local report
`SKSE/Crashlogs/2026-09-12-19-11-02.log`. It is not a capture of the latest
September 19 game session.

The pasted attachment's SHA-256 is
`9B8475F0BA6CC68F7746C8BBC206E8D72A77F444B9E51ED33B76853F9FABBDAF`.

The report's SHA-512 fingerprints match both the currently installed
`SkyrimSE.exe` and the `OpenMCMRuntime.dll` inside
`dist/OpenMCM-1.2.0-alpha.3-FOMOD.zip`. The deployed runtime DLL also matches
that archive member, which is 720,384 bytes. This establishes which optional
runtime binary was loaded; it does not establish whether its startup patch
was applied in that particular session.

The current `OpenMCMRuntime.log` is dated September 19, 01:48:51 and says
`SKIPPED: RaceMenu/Engine Fixes module present; no overlapping patch attempted`.
That later log cannot be used to infer the patch state during the supplied
September 12 crash. Neither competing module appears in the supplied crash's
loaded-module list.

## Failure signature

The report repeats the previously investigated September 8 shutdown failure:

```text
SkyrimSE.exe+0199FC3  cmp dword ptr [rdi],eax
RDI = 0x1F8

+150E229 -> +02EB1C4 -> +0671619 -> +017FD3E
-> +02DDF6A -> +02DDC0D -> +0671389 -> +0670ED2
-> +073ABD4 -> +0227C89 -> +06553AD -> +06514B3
```

The stored instruction evidence in
`build/diagnostics/crash-disassembly-0908-a.txt` and
`build/diagnostics/crash-disassembly-0908-b.txt` resolves the relevant path:

1. The main loop's `Main.quitGame` branch invokes whole-game shutdown.
2. Late shutdown releases remaining reference handles and destroys a
   character/actor that still has 3D (`BSFadeNode`).
3. `TESObjectREFR::Set3D` loads the first shadow-scene pointer and calls its
   scene-removal routine.
4. That routine computes `scene + 0x1F8`, the scene's spinlock address.
5. The lock guard faults reading address `0x1F8`: the scene pointer was null.

The cached CommonLib `Main` and `ShadowSceneNode` definitions corroborate
the quit flag at `0x10` and spinlock at `0x1F8`. The older dump was used for
instruction disassembly only; its heap and registers are not evidence about
this later crash.

This is a shutdown object-lifetime/order failure. No OpenMCM, Scaleform, or
third-party native plugin frame appears in the supplied probable call stack.
That does not prove a mod had no earlier indirect effect, and the text log
does not identify the actor or the component responsible for its lifetime.

## OpenMCM scope and next step

The optional native plugin runs once at SKSE PostPostLoad and can replace
the entry bytes of the paired bulk character-creation precache functions
at `0x96AB10` and `0x96ADA0`. It has no shutdown callback, worker thread,
scene/actor patch, or Scaleform hook. Its presence in a loaded-module list
alone is not a causal stack frame. The new Papyrus/UI API is independent of
that native patch; enabling or disabling API extensions is not an exit-crash
fix.

No speculative production native patch was added. In particular, forcing
process termination or skipping unrelated teardown calls would only conceal
this report without validating object cleanup.

The useful bounded comparison remains the one documented in
`2026-09-08-exit-to-desktop-crash.md`: with the same saved game and otherwise
unchanged mod configuration, compare normal exits with only
`DisableChargenPrecache=0` versus `1`, preserving each session's runtime log
and crash report before launching again. Use an existing save and do not
overwrite it. If the runtime log says `SKIPPED` in both runs, the patch is
not varying and that comparison does not test its effect. A fresh crash
from such a skipped/disabled run would nevertheless establish that the
patch is not necessary for that occurrence.

If the same signature remains without OpenMCM's patch applied, a targeted
crash dump and controlled mod isolation are needed to investigate the
retained actor/scene lifetime. The supplied text log is insufficient to
justify blaming a particular mod or declaring this crash fixed.

No game files, saves, mod-manager state, or settings were changed during
this read-only investigation. No crash log or memory dump was uploaded.
