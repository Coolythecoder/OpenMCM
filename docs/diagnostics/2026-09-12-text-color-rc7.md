# Text/color correction and complete rc.7 package

## Report and reference

The owner confirmed the rc.6 mouse fix in-game, then supplied
`SkyrimSE 2026-09-12 15-17-33_1.png`: Skyrim Unbound's page list is readable,
while option headers, labels and values are nearly black/missing-glyph boxes.
These are the three HTML surfaces in OpenMCM; sidebar text is plain text.

The installed Skyrim Unbound Reborn 3.0.17 Main-page source and English
translations contain ordinary text for the affected entries, not intentional
black/font markup. No provider assets or translations were modified.

Reference comparison used the pinned SkyUI Community revision
`b7a24a936647e815269e34f4899e4b09768eff29`:

- [OptionsListEntry](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/ModConfigPanel/OptionsListEntry.as)
  uses HTML for option text and separates selection/disabled opacity.
- [GlobalFunc.MaintainTextFormat](https://github.com/doodlum/SkyUI-Community/blob/b7a24a936647e815269e34f4899e4b09768eff29/source/actionscript/Vanilla/Shared/GlobalFunc.as)
  reads the parsed format after HTML assignment, restores spacing/kerning,
  then reapplies that format.
- Authored `source/swf/skyui/configpanel.xml` defaults are white, 22px
  Everywhere labels, 22px EverywhereMedium headers and 20px EverywhereBold
  right-aligned values. OpenMCM's intended defaults already match those roles.

## Change

Only the production HTML helper changed: use `field.getTextFormat()` after
HTML parsing instead of a fresh `new TextFormat()` for the typography write.
The parsed aggregate carries existing attributes; mixed-run attributes are
null, so reapplication retains individual colors/fonts/styles. Restore the
clean future format last, so pooled fields do not inherit the previous row.

No blanket recoloring, HTML wrapper, provider rewrite, mouse-handler changes,
registration changes or native-behavior changes were made. The full package's
version/status metadata is now `1.0.1-rc.7`.

## Verification and limits

- Focused regression tests failed on the previous implementation and pass on
  the correction. The model now supports mixed-format null attributes and a
  deliberately default-bearing constructor; the latter is a defensive model,
  not an observation of Skyrim's native constructor.
- Final build: **183 tests passed, one environment-dependent skip**.
- Source/staged/ZIP contracts: **354 / 312 / 441 checks passed**.
- Existing optional native component: **82 regression cases passed** plus
  artifact checks; no claim about fixing the separate shutdown crash.
- Final decompiled SWF checks enforce HTML assignment, parsed-format
  readback, current-text formatting and future-default restoration order,
  rejecting a fresh TextFormat in the HTML helper.
- Final packaged-Journal native AVM1 fixture: **48 cases passed**, checking
  eight format attributes on **688 characters**, plus correct host, field
  identity, font embedding flag and future defaults. Includes plain text,
  explicit black, mixed colors/fonts/sizes and actual header/label/value roles.
- Final packaged-Journal mouse flow: **30 snapshots passed** in the explicitly
  labelled emulator-reentry mode. The known Ruffle focus-rollout limitation
  remains; the owner's rc.6 in-game mouse confirmation is separate evidence.

Baseline rc.6 also retained the expected formats in Ruffle, whose fresh
TextFormat attributes were null. Thus the game screenshot's exact native
failure is **not reproduced or proven here**. This correction addresses the
identified SkyUI source mismatch; Skyrim text/color appearance still needs
verification. Emulator fallback-font screenshots are not visual-parity proof.

Evidence: `build/diagnostics/avm1-mouse/text-format-host-rc7-formats.json`
and `host-rc7-final-fixture-flow-reentry-events.json`. The baseline utility
and separate baseline outputs are preserved in that diagnostic directory.

## Complete package

`dist/OpenMCM-1.0.1-rc.7.zip` is the full mod, **not an add-on**. It includes
the compatibility plugin, scripts, corrected Journal, and existing optional
native component. The ZIP inventory/checksums and bundled upgrade instructions
were checked. No installed game/mod-manager files were changed or uploaded.

ZIP SHA-256:
`2296BD5B1BE08E4902A0DC95D73357BF2DC2633DADB73C92B1B28BA26AA4E8D9`

Journal SHA-256:
`5F0F09256AA87F9613B96CAAE3ACDDB160899A9F5DF05BBDC6343962D132D87C`

Fully exit Skyrim, disable old mouse/diagnostic add-ons, and replace the main
mod with rc.7. Keep `SkyUI_SE.esp` enabled and deploy through the mod manager.
Preserve deliberate INI settings or omission of the optional native DLL.
No new game is required. Check Skyrim Unbound Main, colored options and mouse
navigation after restarting.
