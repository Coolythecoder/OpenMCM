# OpenMCM 2.0.0 publication record

- Date: 23 September 2026.
- Nexus mod: https://www.nexusmods.com/skyrimspecialedition/mods/190822
- New main file ID: **809664**, display name **OpenMCM 2.0.0 - Full FOMOD**.
- Public mod version: **2.0.0**.
- Previous file **804111 / 1.1** retained under Old files; not deleted.
- Updated public short/full description and version changelog, retaining AI
  development disclosure and explicit testing/runtime/migration limits.
- Upload accepted and publicly listed. Nexus virus scanning was still in
  progress at verification; downloads were not yet available at that moment.

## Uploaded artifact

- File: `dist/OpenMCM-2.0.0-FOMOD.zip`
- Size: **7,252,330 bytes**.
- SHA-256: `9F61A244687F1B2C382EA06858373D8E7145A7F304A34F9AF8622517384EBBB9`
- Unified installer with optional Field Guide and author source, optional
  shared browser storage and corresponding GPL source, and optional narrowly
  runtime-specific chargen component. No separate required add-on uploads.

## Validation

- Full build completed with tests enabled.
- Final Python suite: **517 run, 516 passed, 1 skipped**.
- Final ZIP: **9,448 archive/selected-install checks passed**, including all
  **16** FOMOD combinations and Field Guide reconstruction/byte verification.
- Both XML documents passed Nexus/Vortex preprocessing checks.
- Native regression tests passed (82 chargen patch cases; 48 browser checks,
  plus codec tests).
- Scanned 3,300 archive entries including nested source: no save/dump/log/PDB
  files or scanned private builder path/identity patterns found.
- User reported the current setup working and approved publication. This is
  not exhaustive in-game certification of every optional component/runtime,
  and no fix for the earlier exit crash is claimed.

No installed Skyrim files, saves, load order or mod-manager deployment changed
during this release build/upload. Generated build intermediates were rebuilt.
