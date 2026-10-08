# SkyUI-pattern input implementation and final verification

Completed 2026-09-12 for OpenMCM 1.0.1-rc.6. Reference basis is the pinned
SkyUI Community source audit in `2026-09-08-skyui6-input-reference-audit.md`.

## Implemented

- New independent `MCMCompatList` controls own mod/page/options/menu selection,
  scrolling, stable pooled renderers and row-to-list selection/press events.
  Legacy private panel fields are accessors into that state, not separate
  mutable copies. Original provider registration/page/option IDs are retained.
- Row trigger geometry remains visible with an alpha-zero transform over an
  opaque shape, matching the authored SkyUI trigger model. Hidden replacement
  `hitArea` assignments are no longer used for these rows.
- Keyboard activation uses the same list press path. Native rollover owns
  selection; press consumes the list's selected entry. Disabled, stale and
  inactive list/renderer cases are rejected. Scroll updates re-hit-test the
  rows under a stationary mouse while retaining row identities.
- Focus follows the active list/control. The existing vanilla Journal
  FocusHandler supplies Scaleform's focus-rollover suppression. Its logical
  focus bookkeeping is respected, independently of native Selection state.
- Dialogs save/restore focus and disable the underlying lists. Repainting an
  existing dialog does not reacquire modal focus or recreate the entire view.
  Menu choices, slider targets and color swatches retain their interaction
  targets; text input preserves balanced ownership and printable spaces.
- Removed the rejected rc.5 whole-Journal visibility/hit-testing suspension
  and the full-screen modal mouse blocker. The dynamic-host depth adaptation
  is retained: it raises the MCM only if necessary, rather than inverting the
  initially higher dynamic fader with an unconditional authored-depth swap.
- Fixed review findings: hidden list data synchronization, header/label depth
  collisions and stale opacity in pooled options, custom-content input gates,
  and failed key-remap capture leaving every list disabled.
- Source checks now exclude cached reference trees from source candidate
  selection; release ZIP safety/inventory/checksum checks remain unfiltered.

No SkyUI UI classes, authored SWFs or artwork were bundled. No native input
hooks or registration-manager changes were added by this update.

## Final build

Command: `build.ps1 -SkyrimPath <installed Skyrim directory> -Version 1.0.1-rc.6`.

- 181 unit tests executed: **180 passed, one environment-dependent skip**.
- Source contract: **354 checks passed**.
- Staged release contract: **312 checks passed**.
- Final release archive contract: **441 checks passed**.
- Existing optional native component: **82 regression cases passed** and
  artifact validation passed. This does not establish a shutdown-crash fix.
- Final compiled-SWF checks require the new list class/native callbacks,
  transparent row geometry, component focus/restoration and the host's real
  FocusHandler. They reject the removed Journal/input-blocker methods.

Final production Journal SHA-256:

`1E24247683923DA69541A246281D621A43264F6011307C637C3ACE68923C302A`

The full rebuilt archive is `dist/OpenMCM-1.0.1-rc.6.zip`. The earlier,
pre-review archive is preserved at
`build/diagnostics/archives/OpenMCM-1.0.1-rc.6-before-remap-review.zip`.

## Real AVM1 input tests and limits

The final production SWF was instrumented with `AVM1HostFixture` using MTASC
`-keep`, without recompiling/replacing the production classes. Test provider
responses use the public UI ABI. Mouse, dragging, scrolling and text input
are actual headless-browser actions; input handlers are not called directly
by the runner. SKSE transport and unavailable multi-controller queries are
fixture adapters, not real Skyrim services.

- Ordinary `--flow`: **does not pass** the first cross-pane hover/click in
  Ruffle. A native rollout follows the focus change and clears selection even
  though the real host sets `Selection.disableFocusRolloverEvent=true`.
- Separately labelled `--flow --emulator-reentry`: **30 snapshots passed**.
  Physical pointer reentry allows downstream coverage of sparse mod/page/option
  IDs, wait-state duplicate gating, dialog gating/focus restoration, slider
  dragging, menu choices and scrolling, color selection, text with spaces,
  mod/options scrolling without mouse movement after the wheel event, and
  reopening. This is not a passing ordinary first-hover result.
- Basic final-host XPMSE selection passed with diagnostics off and on; enabled
  diagnostics also passed listener-detachment and overlay-fit checks.
- An independent minimal AVM1 fixture with no OpenMCM code reproduced the
  focus-generated rollout at unchanged pointer coordinates, despite
  `Selection.disableFocusRolloverEvent=true`. This confirms that this Ruffle
  run does not honor the suppression in that case; it does not establish
  Skyrim behavior. See `build/diagnostics/skyui6-authored/FOCUS-DIAGNOSTIC.md`
  and `selection-focus-results.json`. An attempted full authored SkyUI replay
  was inconclusive because its XML-generated SWF failed before list
  initialization; it is not counted as a successful SkyUI runtime test.

Evidence lives in `build/diagnostics/avm1-mouse/` under the prefixes
`host-rc6-final-fixture-flow-`, `host-rc6-final-fixture-flow-reentry-`, and
`host-rc6-final-fixture-probe-{off,on}-`. Font rendering in these emulator
screenshots is not evidence of Skyrim's localized font rendering.

**Skyrim first-hover behavior, controller behavior and universal MCM
compatibility remain unverified.** The code follows the audited ownership
pattern, but source parity and emulator results do not prove the reported
in-game problem resolved. Forced external closure during active key capture
also remains an unverified edge case. The separate exit-to-desktop crash is
not attributed to or claimed fixed by this work.

## Handoff artifact

`dist/OpenMCM-Mouse-Update-rc6.zip` contains exactly:

- `Data/Interface/quest_journal.swf`
- `Data/Scripts/OpenMCM_ConfigMenu.pex`
- `README-MOUSE-ADDON.md`
- `LICENSE`

Each extracted ZIP payload was hash-checked against the staged input.
Archive SHA-256:

`EE3FF64DFC9202ED5A931F2853FA63543C50117706F2416FD03DAA8406D046E4`

This addon contains no DLL, INI, ESP or manager script. It has not been
deployed to the game or uploaded. Keep the main mod enabled, disable older
mouse add-ons, install this addon as the winner for its two file conflicts,
and test on an existing save after fully restarting Skyrim.
