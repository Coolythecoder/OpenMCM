# Mouse interaction and option font colors

User supplied Nexus bug titles for mouse support and font coloring, then
confirmed that mouse problems affect MCM selection, settings and dialogs,
and that color issues are not restricted to one MCM.

## Findings

- `MCMCompatUtil.applyText` assigned `.text` and reapplied the complete default
  format. Option headers/labels/values used it. SkyUI Community's
  `OptionsListEntry` uses `SetText(..., true)` for these fields (HTML), including
  input-option display values. Assigning plain text prevents HTML colors.
- Changed hover/rollout rebuilt side and option rows with `removeMovieClip`.
  Menu hover rebuilt the whole modal layer. Updating a slider during its
  press/drag also rebuilt that layer, deleting the pressed track.
  An early return only protected hover on an already selected row, not entry
  into a different row. SkyUI updates existing list renderers' state instead.
- `ConfigPanelFader` is dynamically created at the root's next highest depth,
  above the authored `QuestJournalFader`. Both host implementations swapped
  these layers on open, incorrectly placing MCM below the Journal. The vanilla
  Journal's `DoHideMenu` plays `fadeOut`, which fades alpha to zero but does not
  set visibility false or remove its controls. Closing swapped them again.

The last point was verified through FFDec export of the rc.3 SWF:
`build/diagnostics/journal-mouse-audit-rc3.xml`. Root placement names
`QuestJournalFader`, character 705, authored depth 1. Sprite 705's `fadeOut`
ends with `Menu_mc` alpha multiplier 0 and only a `stop()` frame action.
The generated AS class calls `gotoAndPlay("fadeOut")`. This is evidence of
incorrect layer ordering, not a live recording of Skyrim input dispatch.

## rc.4 changes

- Raise only the dynamic MCM layer if it is behind the Journal. Never swap
  the vanilla layer on open/close. Use the same helper in patched and fallback
  host methods; keep existing focus, lifecycle and sound ordering.
- Refresh selection visuals on live row clips. Retain slider track, text field
  and buttons throughout live value updates. Rebuild for genuine data/window
  changes, not hover.
- Explicit HTML helper at the three option-rendering call sites only.
  Restore spacing/kerning without flattening per-run colors/fonts/sizes.
  Preserve authored defaults for later updates and plain-text field behavior.
- No Papyrus ABI, registration changes, save changes or new input/native hook.
  The optional rc.3 native precache logic is unchanged except release logging.

## Verification scope

The tests execute actual small AS2 bodies in Node with display-list and text
format mocks. They cover object identity, event dispatch, depth invariants,
mixed color spans and plain-text resets. These mocks are not the Flash HTML
parser, Scaleform hit testing or Skyrim. The full build compiles actual AS2
and verifies the resulting SWF/PEX/plugin/native package contracts.

In-game retest is still required for all three mouse areas and colored options.
No installed game/mod-manager files or Nexus records are changed by this work.

## Primary references

- [SkyUI Community OptionsListEntry at the pinned compatibility revision](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/ModConfigPanel/OptionsListEntry.as)
- [SkyUI Community ConfigPanel at the same revision](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/ModConfigPanel/ConfigPanel.as)
- Local official SkyUI source: `.tools/skyui-source/src/Common/Shared/GlobalFunc.as`
  and list renderers; vanilla Journal extracted from the owner's local game.
