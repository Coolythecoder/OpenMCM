# SkyUI 6 input reference audit

Date: 2026-09-08. Scope: the user's request to set aside the preceding workaround and investigate how SkyUI implements MCM input. This is a source/artifact comparison, not an in-game verification or a new fix.

## Reference and provenance

Audited [SkyUI Community](https://github.com/doodlum/SkyUI-Community) commit `b7a24a936647e815269e34f4899e4b09768eff29`. Its `Version.cmake` identifies version 6.11, release index 2026, SE. The checkout is `.tools/skyui-community-reference`.

The audit covers current ActionScript under `source/actionscript`, authored UI definitions under `source/swf`, and common classes recovered from that commit's ConfigPanel XML under `build/diagnostics/skyui6-authored/configpanel/scripts/__Packages`. Embedded classes are not assumed to supersede newer standalone source imported during SkyUI's build. Older classic SkyUI checkouts were not treated as version 6 evidence.

No production source, game files, installed configuration or release package was changed during this audit. The previous rc.5 candidate remains on disk; it has not been reverted by this audit and is not established as the solution. No deployment was performed.

## Actual mouse-selection path

1. `Common/skyui/components/list/BasicListEntry.as:25` forwards row rollover/out/press to the parent list with the row's item index. The authored mod/page symbols are linked to `ButtonListEntry`, which inherits these methods.
2. `Common/skyui/components/list/BasicList.as:281` rejects presses when input/selection is disabled or nothing is selected. It emits `itemPress` carrying the list's **currently selected entry**. It does not simply activate the index supplied to the press handler. Rollover changes selection first; all three authored MCM lists enable auto-unselection.
3. `ModConfigPanel/ConfigPanel.as:497` receives distinct mod, page and option events. Mod/page presses pass the event entry to `selectMod`/`selectPage`; options use the option index. Selection-change events change focus and update highlights/buttons.
4. `ConfigPanel.as:545` checks the READY state, changes to a waiting state, then sends `SKICP_modSelected` with the entry's original registration index. Page selection similarly sends page name/index and stores a separate active-entry marker. Display sorting does not replace registry identity.

Primary source: [BasicList](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/Common/skyui/components/list/BasicList.as), [ConfigPanel](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/ModConfigPanel/ConfigPanel.as).

## Verified differences from OpenMCM

| Area | SkyUI 6.11 | Current OpenMCM |
| --- | --- | --- |
| Hit geometry | Ordinary alpha-zero authored trigger/background children; no replacement `hitArea` assignment in the reconstructed MCM scripts | Generated trigger child is hidden with `_visible=false` and assigned to `row.hitArea` (`MCMCompatPanel.as:1659`, `1833`) |
| Components | Linked/authored panel and persistent separate mod, page and option lists | Empty clip with replaced prototype; one side-list layer switches between mods/pages |
| Row lifetime | Pooled renderers with item-to-clip mappings | Whole row layers recreated on data/page/scroll changes; current hover repaint already preserves rows |
| Focus | `ModListPanel` or options list owns focus (`ConfigPanel.as:704`) | Whole panel normally owns focus (`MCMCompatPanel.as:1427`) |
| Scrolling | Re-hit-tests visible rows after updates, including a stationary pointer | No equivalent post-scroll reselection |
| Transitions | Separate list input/selection flags, saved mod selection, and explicit entering/exiting states | Central panel guards without equivalent independent list-transition state |
| Dialogs | Save focus, focus the dialog/control, disable underlying lists, restore previous focus | Panel-managed dialog data, manual handlers, transparent full-screen blocker, then panel focus |

The authored mod-row rectangle composes to approximately x=90.6..329.2, y=108..132 for the first row. OpenMCM's x=91..330 is essentially the same. Gross hit-rectangle placement is therefore not an obvious explanation for the failed clicks. The transparent-child versus hidden-`hitArea` distinction is real, but is not by itself proof of causation.

Authored details: `source/swf/skyui/configpanel.xml:3554` (page trigger), `3584` (mod trigger), `1758` (option background), `7050` (row class registrations). All three list instances set `isAutoUnselect=true`; the class default alone is not the instance configuration. No clipping-depth mask tags occur in that ConfigPanel XML.

Primary source: [authored ConfigPanel](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/swf/skyui/configpanel.xml), [ModListPanel](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/ModConfigPanel/ModListPanel.as).

## Journal and dialog corrections

`PauseMenu/Quest_Journal.as:273` opens MCM by disabling tabs, ending the System page, fading the Journal, showing the MCM fader, swapping the two faders' depths, and focusing/starting ConfigPanel. Closing reverses this. It does **not** hide the whole Journal fader or set its `hitTestDisable` flag as the rc.5 workaround does.

Current 6.11 `SystemPage.endPage` removes listeners and handles bottom-bar state. It does **not** set `CategoryList.disableInput=true`; that earlier claim came from an older reference. The current System page separately disables inactive Creations/Help/Settings lists and controls them through its own states.

The raw Journal XML has duplicate initial raw-depth placements for the two faders. This audit does not infer a valid released-binary initial depth order from those tags. The verified runtime `swapDepths` code is a distinct finding.

`ConfigPanel.dimOut` disables underlying list selection/input. The embedded `DialogManager` saves/restores FocusHandler focus and attaches the authored dialog. Neither it nor `BasicDialog` creates the global transparent button claimed by the comment at OpenMCM `_addModalInputBlocker`. Slider/menu/color/text dialogs focus their own actual controls. Text input also sets Selection focus and balances `AllowTextInput` on accept/cancel.

Primary source: [Quest_Journal](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/PauseMenu/Quest_Journal.as), [SystemPage](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/PauseMenu/SystemPage.as).

## What the user's screenshots establish

The diagnostic saw mouse movement/down/up and at least one MCM row press. The pictured background Creations entry was the picked target under a **blank welcome-panel area**, not under a mod-name row. That establishes background picking there; it does not prove that the background won a hit test over a real MCM row. Neither screenshot traces a failed row press all the way through list selection and `SKICP_modSelected`.

The shutdown crash is a separate investigation. This comparison neither attributes it to input handling nor fixes it.

## Basis for the next implementation

Follow SkyUI's component ownership model: stable separate lists with pooled row controls and ordinary transparent geometry; list-owned selection/scroll/input flags; selection and press events; appropriate component focus; explicit transition/dialog gating and saved-focus restoration. Preserve the independent Papyrus/API surface and applicable cleanup safeguards.

Validate a real in-game mod-row interaction at each boundary: row rollover/press, list selection and itemPress, ConfigPanel READY-state dispatch, `SKICP_modSelected`, and subsequent page data. Cover mod/page/options mouse input, scrolling under a stationary cursor, dialogs, keyboard navigation, reopening and returning to the Journal. Source parity and emulator tests alone cannot establish Skyrim runtime success.
