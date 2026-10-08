# rc.8 explicit text defaults after failed rc.7 game retest

## What is known

The screenshot `SkyrimSE 2026-09-12 15-32-50_1.png` still shows nearly black,
missing-glyph option text. It follows the rc.7 change; that change did not
resolve the reported problem.

Read-only Vortex evidence confirms the test, rather than an older add-on:
rc.7 was imported at 15:31:14 local and deployed at 15:31:18, before the
15:32:50 screenshot. The old diagnostic/mouse add-ons had already been
removed. Skyrim exited at 15:33:05; rc.7 was removed/undeployed at 15:34:02–03.
The imported archive MD5 matches the workspace rc.7 archive. Its removal
explains why no deployed Journal was available for a direct hash comparison.
No mod-manager state or game files were modified by this investigation.

## Source difference and correction

SkyUI's authored option TextFields have both font/color DefineEditText
metadata and explicit initial HTML. In the pinned Community source,
`source/swf/skyui/configpanel.xml` lines 1309, 1428 and 1644 declare:

- Labels: white, 22px `$EverywhereFont`, left aligned.
- Values: white, 20px `$EverywhereBoldFont`, right aligned with `<b>`.
- Headers: white, 22px `$EverywhereMediumFont`, left aligned.

Dynamic OpenMCM fields lack that authored state. Merely reading parsed
formatting back (rc.7) cannot correct an already wrong HTML document default.
The exact game-internal default failure is not captured, but this missing
initialization differs concretely from the reference.

The helper now:

1. Resolves leading translation tokens before adding generated markup.
   Option buffers already translate nested strings; this does not repeat
   nested substitution on already translated text.
2. Uses `applyText` when neither markup nor entities are present. This is
   the same explicit font-setting path as the readable sidebar and covers
   the installed Skyrim Unbound English labels in the screenshot.
3. Supplies explicit inherited font, size, color, baseline styles, alignment
   and leading for HTML/entity content. It escapes generated attribute values,
   not the mod's payload. Nested mod tags can override the inherited defaults.
4. Retains parsed-format readback for spacing/kerning and restores clean
   insertion defaults after formatting, preserving pooled-field reuse.

Native tests caught an explicit generated `</p>` appending a CR to multiline
inline content. The generated paragraph end is now implicit, avoiding that
extra break without modifying any provider-authored closing tags.

Only `MCMCompatUtil.as` production text behavior changed. Mouse/list/panel
and bootstrap sources retain their previous hashes. Registration, provider
data and native behavior/configuration defaults are unchanged.

## Verification

- Full build: **187 tests passed, one environment-dependent skip**.
- Source/staged/ZIP contracts: **354 / 312 / 441 checks passed**.
- Existing optional native component: **82 regression cases passed**, with
  PE/INI artifact checks. No shutdown-crash fix is claimed.
- Compiled SWF checks require translation before use, plain dispatch,
  explicit HTML font/paragraph defaults and parsed-format readback order.
- Final packaged-Journal TextField test: **72 asserted cases**, checking
  **936 characters** with ten format attributes each. Eight additional
  sparse-format comparison rows are captured but not asserted. Coverage:
  embedded fonts on/off, font roles, entities, explicit black, nested colors/
  styles, right-bold values, paragraphs/alignment/CR semantics, nonstrings,
  clean defaults and pooled plain-to-HTML-to-plain identity.
- Final packaged-Journal mouse regression: **30 snapshots passed** in the
  explicitly labelled emulator-reentry mode. This retains the existing test
  allowance for Ruffle's focus-rollout limitation; the owner's rc.6 in-game
  mouse confirmation remains separate evidence. Output:
  `build/diagnostics/avm1-mouse/host-rc8-final-fixture-flow-reentry-events.json`.

The native fixture preserves the packaged utility with MTASC `-keep` and has
no static production-class references. It does not replace TextField or its
parser. Evidence: `build/diagnostics/avm1-mouse/text-format-host-rc8-formats.json`.
Baseline Ruffle tests did not reproduce the original game fault, so the new
game appearance still requires confirmation. Do not call the emulator's
fallback-font screenshots proof of Skyrim font rendering.

## Complete package

`dist/OpenMCM-1.0.1-rc.8.zip` is one complete replacement mod, not an add-on.
It contains the corrected Journal, compatibility plugin, scripts, and existing
optional native component. Package inventories/checksums and version/upgrade
instructions were checked. No deployment or upload was performed.

ZIP SHA-256:
`BB888BE710944CCA18330196B989C7A1A76ABED607D8012C8D7E70A785AEDBD1`

Journal SHA-256:
`24B69DDC956ED3543607384BFC4F356CF05D5625A4853CFC75BEE33FBAD5B8A8`

Install the complete package with Skyrim closed; do not retain an old mouse
add-on as a conflict winner. Keep `SkyUI_SE.esp` enabled and deploy. Preserve
intentional native INI settings or omission of the optional DLL. No new game
is required. Recheck Skyrim Unbound Main and an MCM with colored text.
