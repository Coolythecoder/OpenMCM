# OpenMCM 1.2.0-alpha.5 browser integration verification

Built 19 September 2026. Preview only; no Skyrim deployment, mod-manager change,
Nexus upload or in-game verification was performed.

## Artifact

- `dist/OpenMCM-1.2.0-alpha.5-FOMOD.zip`: 7,193,054 bytes, 60 files.
- SHA-256: `BBB5B1B6353FCBC21B222C2A31239351072E35D4F30AB5D9D3BC4CDCB0AE387F`.
- Packaged Journal SHA-256:
  `D0EFDA637FF5FE86C29C99768C0B048E8C2A78277AB330A786E3A2CA1C8B80C6`.
- Browser DLL SHA-256:
  `A7F9B9C5BD1C0C3A408C066DF99F62B579ECB3A009CCD0D05B5EB7DDBB59C865`.
- Corresponding native source ZIP SHA-256:
  `753308EA5D147F9AB0BB111F3EBB58AC29C83F09EDF50372903BCB223D75883B`.

The source archive and GPL/dependency licences are inside the same FOMOD,
outside installed Data. Source-package audit checked 2,785 manifest entries,
fresh-path native test compilation and byte-identical offline repackaging.
Full DLL reproducibility in a fresh compiler environment was not established.

## Integrated scope

Independent browser UI provides search, All/Favourites/Hidden tabs, reversible
hiding, custom names, priorities, sort and scroll preferences. Optional native
storage adapts MCM Menu Redone 2.3.0's original profile code, not its registry,
Papyrus manager, SkyUI-derived ConfigPanel, artwork or prebuilt assets.

The legacy 128-slot registry and MCM Helper array/index ABI are unchanged.
Additional API 1 helpers provide scoped page navigation and grouped disabled
flags. Neither browser profiles nor these helpers export provider settings.
Page navigation does not redirect from inside OnPageReset.

Persistence review found and fixed early-close/default overwrite, temporary
empty-list scroll loss, early tab edits before the preference reply, and stale
shared state overriding a failed-write local fallback. The local-only recovery
marker is validated, survives reloads when the game is saved, and is never sent
to the native writer. See OpenMCM-Browser.md for recovery precedence tradeoffs.

## Verification

- Full build: `build/browser-alpha5-build.log`.
- Python suite: 461 cases, 460 passed, one existing opt-in integration skip.
- Existing optional chargen component: 82 native regression checks passed.
- Browser component: 48 persistence checks and original profile-codec suite passed.
- Static source contract: 354; staged legacy contract: 312; API package: 67.
- SkyUI coexistence selected-payload contract: 690 checks passed.
- Final ZIP: 4,788 checks, including all eight combinations of host mode,
  optional chargen component and optional shared browser storage.
- Both installer XML files passed Nexus's quote-sensitive preprocessing and
  .NET XML reader checks; the known single-quoted declaration regression fails
  in the test harness as expected.
- Compiled AVM1 browser: 22 checks, plus native mouse clicks/text entry and
  filtering-to-raw-provider-ID selection, passed.
- Compiled AVM1 API: 77 checks passed, including page navigation and groups.
- Packaged Journal text fixture: 80 rows executed, 72 asserted, 936 characters
  checked for native text formatting. Journal bytes unchanged by testing.

Compiled-runtime evidence is under `build/diagnostics/avm1-mouse/`:
`openmcm-browser-final-results.json`, `openmcm-api-alpha5-final-results.json`,
`text-format-host-alpha5-final-formats.json`, and
`openmcm-browser-final-browser.png` (toolbar layout inspected).

Ruffle uses substitute fonts and a mocked SKSE/Papyrus transport. These checks
do not prove Skyrim Scaleform, real DLL loading, save migration, gamepad text
entry or shutdown behavior. Native versions are source-supported allowlists,
not game-tested certifications. The previous exit-crash cause is unresolved.

## Required game retest

Use a separate mod profile and backed-up saves. Install this full FOMOD instead
of the prior OpenMCM preview; do not install MCM Menu Redone alongside it.
Start with save-local storage and the chargen component omitted. Test original
MCM mouse/keyboard/controller selection, settings/dialogs, colours, browser
actions, save/reload and quit. Then separately test optional shared storage and
the opt-in API example. The old standalone 1.1 compatibility list is historical
evidence only; it does not certify these new changes.
