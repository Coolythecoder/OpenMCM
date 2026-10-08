# OpenMCM API 1 / alpha.2 implementation and verification

## Result

Built `dist/OpenMCM-1.2.0-alpha.2-FOMOD.zip`: 56 files, 1,197,869 bytes.

SHA256: `399704C273DFD8C9D9B2516A8EC0E8F1892D48BC18B451A195656EBDEDFD13E6`

The full installer retains both host modes and its optional native selection.
Both modes contain `OpenMCM.pex` and `OpenMCM_ConfigBase.pex` plus their sources.
The API guide and ordinary/extended example sources ship as documentation.
Neither example creates an automatically installed quest.

## Implementation boundaries

- SkyUI API 4 remains the legacy contract; OpenMCM SDK version 1 is separate.
- Named bindings and convenience additions retain existing option types/IDs.
- The base highlight bridge has additive default hooks. For legacy providers
  they preserve empty default help and the original footer publication. The
  opt-in base supplies default help before normal/ST callbacks, permitting an
  explicit callback to override or clear it.
- Extended live updates validate provider/page/host token in a single UI call;
  public author tokens use persistent per-provider generations, guarding full
  Journal recreation even if its AVM1 token counter restarts.
- Opt-in slot replacement clears previous names/help and ST associations.
- Live updates preserve presentation state and do not replace mod-owned values,
  MCM Helper persistence or its JSON schema. Dynamic reflow/new widgets/presets
  are not implemented in this increment.
- The example schedules its delayed work via its own mod event, allowing the
  normal selection callback to return and the manager to unlock navigation.
  Its enable toggle gates the example action.

## Verification

Final full build: `build/api-alpha2-build.log`.

- All Papyrus scripts and both examples compiled successfully with Caprica.
- 341 Python-discovered tests: 340 passed, one existing opt-in test skipped.
  These include source contracts, explicitly labeled behavioral models and
  JavaScript execution of actual extracted AS2 methods; not a Papyrus VM test.
- 82 native precache-patch regression cases passed; native behavior unchanged.
- Legacy source ABI: 354 checks; standalone staged ABI: 312 checks.
- New packaged SDK: 61 checks; SkyUI coexistence staged payload: 684 checks.
- Final FOMOD archive/projection validation: 2,543 checks. Selected installs
  contain 29/31 files standalone and 13/15 with SkyUI, without/with native.
- Actual compiled AVM1 API fixture: 30 assertions passed, covering scoped live
  text, native TextField formats/colors, renderer/selection/scroll preservation,
  stale updates, and delayed help/clear guards. Evidence:
  `build/diagnostics/avm1-mouse/openmcm-api-v1-results.json`.
- Mouse regression injected into a diagnostic copy of the final Journal:
  one real browser click selected XPMSE exactly once. Evidence:
  `build/diagnostics/avm1-mouse/host-api-alpha2-probe-off-events.json`.
  MTASC `-keep` host warnings and Ruffle fallback-font/Scaleform-stub warnings
  are expected for this fixture; this is not in-game verification.

Final production Journal SHA256:
`012A2E16029318367A085597DCFCCCF9EEE50C1F21CC61C3729C059FECDEB8B7`.

Source/staged SDK, example and guide hashes were compared and matched after
the final rebuild. The initial integrated run caught two legacy test harnesses
missing the new invalidation helper; both now execute the real helper body and
assert cleanup rather than bypassing it.

## Preserved artifacts and remaining testing

Published 1.1.0 remains unchanged:
`4DB3F3C8A41E9F16565350DBA6B2BE5392C52FD12971498D70E5EDB8B0A2CCE4`.

Alpha.1 remains unchanged:
`63AD03F4D32935908215356415241BE9224C925C594622409F2909D4A8A5E656`.

No game/mod-manager deployment, save modification or Nexus upload was performed.
The owner's prior in-game verification applies to standalone 1.1.0 only. New
SDK providers, ordinary/ST callback execution in Skyrim, SkyUI coexistence and
mod-manager installer behavior require an in-game/profile test before release.
