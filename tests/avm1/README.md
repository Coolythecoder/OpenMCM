# OpenMCM AVM1 mouse-dispatch diagnostic

## Opt-in OpenMCM API v1

`AVM1OpenMCMApiFixture` exercises the actual production panel and native AVM1
TextFields. Its 77 checks cover read-only discovery, blank/filtered page
identity, stale-token rejection, label/TEXT-value updates, HTML colors and
legacy uppercase values, retained renderer/field identity and scroll/selection,
conditional tooltip/rollout publication, registry refresh and panel recreation.
This fixture supplies provider buffers and page choices: it is not a mouse
input test or an in-game Scaleform check. Papyrus separately owns author-facing
page generations so a wholly reloaded Journal cannot reuse a public handle.
Alpha.5 also covers atomic conditional groups and queued, scope-checked page
navigation, including dialogs, remap, disabled API and reset precedence.

## Browser integration (alpha.5)

`AVM1BrowserFixture` compiles the production browser and panel. Its 22 initial
assertions verify filtering, raw provider identity, sorting, stored state and
early-close/shared-write recovery races.
The runner then sends native mouse clicks and keyboard text into real AVM1
controls to exercise favourite/hide/unhide/search/clear and provider selection.
Browser input dialogs must not emit provider setting callbacks.

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp src/actionscript -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/diagnostics/avm1-mouse/openmcm-browser.swf -header 1280:720:30 -version 8 -main tests/avm1/AVM1BrowserFixture.as
$env:NODE_PATH='C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-browser.cjs
```

This fixture uses substitute fonts and a mock transport, not Skyrim/SKSE.
It does not establish live native DLL loading, controller keyboard support or
full-game text/input compatibility. Save/load and shared storage need a game test.

### API fixture command

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp src/actionscript -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/diagnostics/avm1-mouse/openmcm-api-v1.swf -header 1280:720:30 -version 8 -main tests/avm1/AVM1OpenMCMApiFixture.as
$env:NODE_PATH='C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-openmcm-api.cjs
```

Results are written to
`build/diagnostics/avm1-mouse/openmcm-api-v1-results.json`. The 16 automated
AS2-method-body lifetime/transport tests in `tests/test_openmcm_api_ui.py` also
cover malformed IDs, disabled/non-TEXT rows, removed pages and token exhaustion.

## Native text semantics (rc.8)

The owner's rc.7 game retest still showed unreadable option text. The rc.8
helper uses plain assignment for markup/entity-free options and explicit
inherited HTML defaults otherwise. The native fixture now captures 80 rows:
72 are asserted, and eight sparse-format comparison rows are diagnostic only.
It checks 936 characters, each with font/color/size/spacing/kerning/alignment/
leading/bold/italic/underline checks, plus field identity and future defaults.
Coverage includes entities, nested markup, nonstrings, plain-to-HTML-to-plain
reuse, actual font roles, paragraph alignment and native CR/line-break output.

Use the host compilation/runner commands below with `rc8` in the output name.
Final results are `build/diagnostics/avm1-mouse/text-format-host-rc8-formats.json`.
No TextField method or native HTML parser is replaced. The fixture found and
prevented a generated closing paragraph tag adding an extra line break.
The final production result omits only that generated closing tag; provider
paragraph endings are unchanged. This is not Skyrim visual verification.

The current fixture/runner expect the expanded case set. Earlier counts below
are historical results from earlier fixture revisions.

## Native text-format regression (rc.7)

The owner confirmed the rc.6 mouse fix in Skyrim on 2026-09-12. For the later
text/color report, `AVM1TextFormatFixture` captures native `getTextFormat` for
each character and the future format, with embedded fonts on and off. It
does not replace TextField, its HTML parser or its formatting methods.

`AVM1TextFormatStandalone` compiles the utility from source.
`AVM1TextFormatHost` has no static reference to a production class, so MTASC
`-keep` tests the utility already embedded in the packaged Journal.

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/staging/Data/Interface/quest_journal.swf -out build/diagnostics/avm1-mouse/text-format-host-rc7.swf -keep -version 8 -main tests/avm1/AVM1TextFormatHost.as
$env:NODE_PATH='C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-text-format.cjs text-format-host-rc7.swf
```

The final rc.7 host passed 48 cases and checks over 688 characters, including
header/label/value font roles, mixed colors/fonts/sizes, explicit black, plain
literal markup, clean future defaults and pooled-field identity. These are
format-data assertions, not proof of Skyrim's font rendering. Baseline rc.6
also retained fonts/colors in Ruffle; its fresh TextFormat attributes were
null. The screenshot's black/missing-glyph fault was **not reproduced there**.
The rc.7 correction removes a confirmed SkyUI source mismatch, but still needs
an in-game text check. Raw baseline and final results are separate JSON files
under `build/diagnostics/avm1-mouse/text-format-*-formats.json`.

The optional wrapper/sparse-format modes are diagnostic comparisons only;
they are not shipped production implementations. The layered diagnostic
screenshot is not a visual-parity test.

This fixture compiles the real `MCMCompatPanel` and `MCMCompatUtil` ActionScript
classes with MTASC. It runs the resulting SWF in the official
`@ruffle-rs/ruffle` 0.6.0 runtime inside headless Microsoft Edge. Playwright
sends an actual browser mouse move and click. The runner does **not** call
ActionScript press/hover handlers manually.

The fixture supplies a diagnostic SKSE transport object and wraps the existing
row handlers to record entry before forwarding the original arguments and
receiver. The panel's production layout, hitArea objects, prototype installation,
state machine, focus flags, and event handlers otherwise run unchanged.

## Result

On 2026-09-08, a genuine click at `(220, 144)` produced:

1. `rowOver`, index 1.
2. Global `mouseDown`, stage `(220, 144)`.
3. `rowPress`, index 1.
4. Exactly one `SKICP_modSelected` event, number 1 (XPMSE).
5. Global `mouseUp`, panel mode `pages`, state 1 (waiting for option data).

The initial `SKICP_modSelected(-1)` is the normal registration-list request.
The deliberately minimal SKSE mock does not answer page/option requests.

This standalone case rules out a general AVM1 inability to click these
dynamically drawn, hidden-hitArea rows. The host-level case below additionally
tests the final packaged Journal in Ruffle. Neither case establishes that
Skyrim's Scaleform input dispatch works: Ruffle is a different runtime and
lacks Scaleform's picking extensions. Ruffle also uses substitute fonts and
cannot verify the Skyrim font appearance.

## Re-run

From the workspace root in PowerShell:

```powershell
npm install --prefix build/diagnostics/avm1-mouse --no-audit --no-fund --ignore-scripts @ruffle-rs/ruffle@0.6.0
& .tools/mtasc-1.15/mtasc.exe -cp src/actionscript -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/diagnostics/avm1-mouse/fixture.swf -header 1280:720:30 -version 8 -main tests/avm1/AVM1MouseFixture.as
$env:NODE_PATH='C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs
```

Node 20+ is required by the bundled Playwright. The runner starts an ephemeral
localhost-only HTTP server, closes its browser and server when finished, saves
`probe-off-events.json` and `probe-off-after-click.png` (with a SWF-name prefix
for alternate fixtures), and exits nonzero unless exactly one XPMSE selection
event was emitted.

## Final packaged Journal host test

`AVM1HostFixture.as` is injected into a diagnostic copy of the final rc.4 Journal
SWF, without recompiling/replacing its production classes or its authored
display-list symbols. This fixture invokes the host initialization, platform
selection, saved System tab restoration, and `ConfigPanelOpen()`, then provides
two registered MCM names. It does not replace any mouse handler.

Only missing Scaleform multi-controller queries are supplied in Ruffle:
`Selection.getControllerFocusGroup`, `Selection.getControllerMaskByFocusGroup`,
and `System.capabilities.numControllers`. Native `Selection.setFocus/getFocus`,
all mouse APIs, display-list hit testing, and production handlers are untouched.
`gfxfontlib.swf` is copied from the build's vanilla BSA extraction to satisfy
the Journal's authored font import. Ruffle still falls back on some fonts.

The tested final Journal SHA-256 was:
`20ADF3525516F9C45DDA91C5A61BA2C8646AB1583A63EC860DCADFEBD5206BC7`.

The host test also emitted **exactly one** `SKICP_modSelected(1)` in response to
the real browser click at `(220, 144)`. At mouse-down, the authored Journal was
visible with alpha 100 at depth -16383, and the dynamic MCM fader was visible at
depth 0. The panel was ready with side index 1. At mouse-up, it had transitioned
to page mode and was waiting for option data. `Mouse.getTopMostEntity` is not
implemented by Ruffle and is explicitly reported as unavailable, not mocked.

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/staging/Data/Interface/quest_journal.swf -out build/diagnostics/avm1-mouse/host-fixture.swf -keep -version 8 -main tests/avm1/AVM1HostFixture.as
Copy-Item -LiteralPath build/work/vanilla-interface/interface/gfxfontlib.swf -Destination build/diagnostics/avm1-mouse/gfxfontlib.swf
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs host-fixture.swf
```

MTASC's missing-class warnings during this diagnostic injection refer to
existing host classes preserved by `-keep`. The existing host class functions
are verified to be present and exercised by the fixture. Ruffle additionally
reports its existing `scale9Grid` stub and a stack-underflow warning while
initializing the final host; neither prevents this tested click from dispatching.

The initial rc.4 baseline outputs are preserved as
`build/diagnostics/avm1-mouse/host-fixture-events.json` and
`host-fixture-after-click.png`. The promoted runner saves newer runs with
`probe-off-` or `probe-on-` in the filename to keep these cases separate.

## Optional diagnostic overlay does not capture clicks

After compiling a SWF containing the diagnostic probe, run both cases:

```powershell
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs fixture.swf
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs fixture.swf --diagnostics
```

The same two commands accept `host-fixture.swf` to exercise a newly built final
Journal host. Re-inject `AVM1HostFixture.as` after rebuilding the package so it
contains the current production classes. The old rc.4 SWF has no diagnostic
probe and therefore should not pass the `--diagnostics` test.

With diagnostics enabled, the fixture calls `setMouseDiagnostics(true)` before
the real mouse click. The runner verifies exactly one live probe listener in
the runtime's actual `Mouse._listeners` array. After selecting XPMSE it calls a
test-only ExternalInterface callback to stop diagnostics, then checks that the
listener and overlay were removed. An additional genuine click must not change
the stopped probe's counter. These assertions do not stub or dispatch mouse
callbacks. Both probe-off and probe-on standalone tests passed on 2026-09-08.

The current-source runs are preserved as `fixture-current-probe-off-events.json`
and `fixture-current-probe-on-events.json` under the diagnostic output directory.

The final diagnostic host was also tested with probe off and on. Its production
SWF SHA-256 was
`42489019D658D6709180A5D88A914F5AEABBF565CB13B4F275EA5408356A6EC1`.
Both cases selected XPMSE exactly once. The probe-on case verified listener
detachment and no post-stop counter changes. The overlay contained four lines,
with measured text height 65 in a 72-pixel field and measured text width 590 in
an 810-pixel field. All four lines were also checked in the generated screenshot.
These metrics are Ruffle fallback-font measurements, not an in-game font claim.
Outputs use the prefix `host-diagnostic-fixture-probe-off-` or
`host-diagnostic-fixture-probe-on-`.

No installed game files are changed by either test. Neither launches Skyrim.

## Retired rc.5 faded-Journal isolation experiment

This section records the rejected rc.5 experiment, not a SkyUI parity test.
The subsequent SkyUI 6.11 audit established that SkyUI does **not** blanket-hide
the Journal fader or disable that entire fader's hit testing. The current
`--boundary` test therefore expects the independent injected canary to receive
all six presses, while the genuine MCM row still emits exactly one selection.
This is intentionally different from ordinary Journal lists, whose own input
flags may prevent actions. It verifies removal of the rejected global behavior;
it is not proof that either background picking or Skyrim mouse dispatch is fixed.

Historical rc.5 experiment:

`--boundary` runs a separate final-host scenario. Before opening MCM, the
fixture adds one transparent canary MovieClip beneath the existing authored
`QuestJournalFader`, above that fader's children, at stage coordinates
`(506, 288)`. The fader is explicitly visible with alpha zero, matching the
important distinction between faded graphics and disabled hit testing. No
existing production handlers are replaced. No mouse API or `hitTestDisable`
implementation is stubbed.

The runner sends genuine browser clicks and requires the following counts:

| Phase | Additional canary presses |
| --- | --- |
| Before MCM opens | 1 |
| While MCM is open | 0 |
| After a repeated open | 0 |
| After MCM closes | 1 |
| After reopening and calling panel `endPage()` alone | 1 |
| After reopening and removing the panel clip | 1 |

Between repeated open and close, a genuine click on XPMSE must still emit
exactly one `SKICP_modSelected(1)` event. While open, the runner additionally
checks that the Journal is hidden, has its hit-test-disable flag set, and has
an owned saved-state record. After close, the Journal must be visible again,
not hit-test-disabled, with that ownership record cleared.
The last case uses `removeMovieClip()` and lets AVM1 dispatch the real unload
event; the runner never invokes `onUnload()` manually.

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/staging/Data/Interface/quest_journal.swf -out build/diagnostics/avm1-mouse/host-boundary-fixture.swf -keep -version 8 -main tests/avm1/AVM1HostFixture.as
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs host-boundary-fixture.swf --boundary
```

The previous diagnostic host (`42489019...`) **failed** this regression: all
four canary clicks arrived, including both clicks through blank MCM content.
XPMSE still selected once. The baseline evidence is preserved as
`host-before-boundary-fixture-boundary-events.json`. This reproduces the
specific Journal click-through defect; it is not proof that every reported
failure to click an MCM row has the same cause.

OpenMCM rc.5 production SWF
`7FC72B9685CD3CF3B243B9FE6CBC93AC13787C970D1117F6E0E00F01500C76E7`
**passed** the final six-phase regression with press counts `[1, 0, 0, 1, 1, 1]`.
The original visible state survived repeated opens, and ownership was cleared
after close, direct `endPage()`, and the real unload event. XPMSE selected once.
Normal final-host clicks also passed with the probe disabled and enabled, and
the enabled probe passed its detach and four-line-layout assertions.

Final results are `host-boundary-fixture-boundary-events.json` and
`host-boundary-fixture-probe-{off,on}-events.json` under the diagnostic output
directory. Ruffle does not implement the native Scaleform `hitTestDisable`
extension: the test checks its assigned property value, but the physical
blocking is exercised through real AVM1 visibility semantics. In-game testing
is still required for Skyrim's native Scaleform path.

## Independent-list interaction regression

`AVM1InteractionFixture.as` compiles the real current production panel and list
classes. It provides deterministic provider responses through the public
Papyrus UI ABI. The runner calls these response helpers, but **never** an input
handler. Clicking, dragging, wheel scrolling and text entry use actual browser
input. Passive wrappers observe each list's native row-event, selection-change
and item-press callbacks, then call the original callback with its original
receiver and argument.

The `--flow` scenario covers sparse registration identity after label sorting;
row stability through hover and scrolling; separate persistent mod/page/options
lists; duplicate-click gating while waiting for provider data; sparse page IDs;
registration refresh without losing the active page; toggle and slider/menu/input
actions; disabled/hidden options; underlying list gating while dialogs are open;
saved list focus after acceptance; live slider target stability; balanced text
input; wheel reselection under a stationary pointer; and reopening.

```powershell
& .tools/mtasc-1.15/mtasc.exe -cp src/actionscript -cp tests/avm1 -cp .tools/mtasc-1.15/std8 -swf build/diagnostics/avm1-mouse/interaction-fixture.swf -header 1280:720:30 -version 8 -main tests/avm1/AVM1InteractionFixture.as
& 'C:\Users\josep\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/avm1/run-fixture.cjs interaction-fixture.swf --flow
```

The standalone fixture enables the optional raw-key fallback (disabled by
default in game) to verify that it does not consume spaces during native
TextField editing. It does not reproduce Skyrim's input dispatcher. Its focus
snapshots use native AVM1 Selection; final Journal host fixtures separately
exercise the real packaged FocusHandler. Neither runtime is Skyrim's Scaleform.
The JSON and screenshots are regression evidence, not an in-game compatibility
claim.

`--emulator-reentry` is a separately labelled diagnostic mode. It physically
moves the browser pointer out and back before each click to continue downstream
tests after Ruffle synthesizes a rollout on changed focus. It does not replace
Selection or row handlers. Its results must not be presented as passing the
ordinary first-hover flow: the normal `--flow` run is retained independently.
