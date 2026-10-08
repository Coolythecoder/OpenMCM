# OpenMCM API 1 — experimental SDK

Included in OpenMCM 2.1.0; originally introduced in the 1.2 previews. This is an
opt-in extension, not a replacement for SkyUI's MCM API 4. The host package is
version 2.1.0, this experimental extension is API 1, and the legacy interface is
API 4. The extension adds named page options, automatic help
and guarded live text updates. New SDK providers require OpenMCM; they will not
run on unmodified SkyUI alone simply because their base class inherits its API.

## Compatibility and adoption

- Existing `SKI_ConfigBase` providers, numeric option IDs, ST callbacks, option
  types, registration, and MCM Helper-facing fields retain their existing ABI.
- For a new or migrated Papyrus menu, use `extends OpenMCM_ConfigBase`. Keep
  the same quest, registration and `OnConfigInit`/`OnPageReset` workflow.
- Define options in `OnPageReset`. Its callback does not need a `Parent` call.
  Ordinary and ST callbacks remain the standard SkyUI events; the SDK does not
  substitute key strings for numeric callback arguments or change event order.
- Do not override the manager bridge (`SetPage`, `OpenConfig`, `CloseConfig`,
  `AddOption`, `HighlightOption`) or `OpenMCM_` internal helpers. If you override
  `OnGameReload` or `OnConfigManagerReset`, call the parent implementation.
- An existing MCM Helper `MCM_ConfigBase` provider should keep its base class.
  Papyrus has no multiple inheritance; this SDK does not automatically extend
  Helper's JSON schema or let a script derive from both bases. Keep using Helper
  for its persistence, JSON controls and other features.
- The optional native OpenMCMRuntime component is not required for this API.

## Player enable option

Open **OpenMCM > Status > Runtime > Enable OpenMCM API**. It is off by default
for new games and saves upgraded from earlier previews. The choice is stored
with the savegame and restored whenever the Journal is recreated; save after
changing it if you want to retain the choice across a reload.

This switch controls automatic help, optional live text/status updates, page
navigation, conditional groups and public asynchronous page tokens. It does not change SkyUI API 4, disable normal
MCMs/MCM Helper, install a native DLL, or convert an existing mod to use API 1.
Only authors who use the extension gain those features. This is not an
exit-crash fix or an OpenMCMRuntime precache setting.

Named option construction, bindings and numeric IDs still work when off, so a
provider's normal controls/callbacks can remain usable. Explicit standard
`SetInfoText` in normal/ST highlight callbacks and synchronous SkyUI value
setters still work. Automatic bound help is suppressed, live update functions
return false, and `GetPageToken()` returns zero. Provide a synchronous fallback
or clearly disable an extension-only action, rather than silently doing nothing.
Toggling invalidates outstanding scoped work; re-enabling never revives old
tokens. A full page flush is required for fresh tokens.

## Small example

For an installable, practical teaching mod, see
[OpenMCM Field Guide](../examples/field-guide/README.md). It includes a real
carry-load readout, manual trip checklist, all standard control types, optional
hotkey, guarded delayed refresh and editable quest/plugin source. Select the
optional Field Guide in the main 2.0 FOMOD (off by default), or use its separate
sample ZIP with an existing compatible host. Do not install both copies. It
depends on OpenMCM and does not replace SDK or host files.

```papyrus
Scriptname MyConfig extends OpenMCM_ConfigBase
Int clicks = 0

Event OnConfigInit()
    ModName = "My Config"
EndEvent

Event OnPageReset(String a_page)
    AddNamedText("action", "Count a click", "Select", "Updates without a page reset.")
    AddNamedText("status", "Clicks", clicks as String, "", OPTION_FLAG_DISABLED)
EndEvent

Event OnOptionSelect(Int a_option)
    Int token = GetPageToken()
    If a_option == GetOptionID("action")
        clicks += 1
        If token > 0
            SetOptionText("status", clicks as String, token)
            SetLiveInfoText("The status row has been updated.", token)
        Else
            ; Synchronous legacy fallback: never use this after delayed work.
            SetTextOptionValue(GetOptionID("status"), clicks as String)
        EndIf
    EndIf
EndEvent
```

The complete `examples/OpenMCMApiExample.psc` also covers ST callbacks, coloured
labels, ordinary SkyUI toggle setters, explicit help overrides and delayed work.
Its one-shot mod event returns from the selection callback before waiting, so
the manager can unlock navigation. The example's reload handler calls `Parent`
and registers its own event; the SDK itself does not schedule background work.
Both that file and the traditional `OpenMCMExample.psc` are compiled by the build.
Their PEX files are build-time fixtures, not installed scripts.

To run the example in a development profile, compile it with the shipped SDK
sources and your normal Skyrim/SKSE headers. Attach it to a start-game-enabled
quest. Use the normal SkyUI setup: a player reference alias with
`SKI_PlayerLoadGameAlias` on the same quest. That alias forwards reload events
to its owning quest; it has no `QuestScript` property to fill.
Generate the plugin's SEQ if needed for its startup quest, enable the plugin,
and test with SKSE in a separate profile. Enable API 1 in OpenMCM's Runtime
section before running the live-update actions. These small source examples
are not installed as quests. The separate practical Field Guide quest is
installed only if its optional FOMOD component is selected.

## Capability discovery

| Global function | Meaning |
| --- | --- |
| `OpenMCM.GetAPIVersion()` | Installed SDK version: `1`. Not your mod's version. |
| `OpenMCM.HasCapability(String a_capability)` | Installed SDK supports `named_options`, `automatic_help`, `live_text`, `page_tokens`, `page_navigation`, or `conditional_groups`, independent of the enable choice; unknown names return false. |
| `OpenMCM.IsAPIEnabled()` | Save-local enable preference; false if the manager is unavailable. Also readable with Journal closed. |
| `OpenMCM.GetHostAPIVersion()` | Active Journal movie's enabled extension version, or `0` if disabled/unavailable. Not an installed-plugin detector while the Journal is closed. |

Keep your existing `GetVersion()` for your own menu's save migration. Do not
change SkyUI's API version or use a provider's `GetVersion()` as SDK detection.

## Page navigation and conditional groups

```papyrus
Bool Function SetCurrentPage(String a_page, Int a_token)
Bool Function SetOptionsEnabled(String[] a_keys, Bool a_enabled, Int a_token)
```

Both require an enabled API and a current `GetPageToken()`. A true return means
the Papyrus request was submitted while its token remained current; it is not
an acknowledgement from the asynchronous UI. The UI independently validates
provider, page and generation before accepting it.

`SetCurrentPage` selects an existing entry in your `Pages` array by its **raw**
name/translation key. It does not add pages. Call it from an option callback or
later scoped work after the current page is published, not `OnPageReset`.
During a selection/default callback it waits for the normal manager unlock,
then revalidates the token and uses the ordinary page-selection event. It does
not interrupt a dialog/remap or a page build. An accepted navigation takes
precedence over a pending reset of the old page; stale requests are discarded.
This does not implement redirects while `OnPageReset` is building a page.

`SetOptionsEnabled` applies the disabled flag to 1–128 named current-page
options in one repaint. It validates every key/ID before changing any row and
preserves other flags, including hidden/unmap flags. This is a presentation
helper, not an automatic condition language: update your own condition/setting
and rebuild the same flags in `OnPageReset`. It does not persist settings or
cancel a dialog that is already open. Re-check your mod's conditions in its
callbacks before applying gameplay changes.

Both are off with the Runtime API switch. Keep ordinary SkyUI callbacks and
page-building fallbacks for players who leave it off.

## Named options

These methods return the same full numeric ID as a SkyUI `Add*Option`, or `-1`
on failure. The argument names/defaults below are part of the experimental interface.

```papyrus
Int Function AddNamedHeader(String a_key, String a_text, String a_help = "", Int a_flags = 0)
Int Function AddNamedText(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
Int Function AddNamedToggle(String a_key, String a_text, Bool a_checked, String a_help = "", Int a_flags = 0)
Int Function AddNamedSlider(String a_key, String a_text, Float a_value, String a_formatString = "{0}", String a_help = "", Int a_flags = 0)
Int Function AddNamedMenu(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
Int Function AddNamedColor(String a_key, String a_text, Int a_color, String a_help = "", Int a_flags = 0)
Int Function AddNamedKeyMap(String a_key, String a_text, Int a_keyCode, String a_help = "", Int a_flags = 0)
Int Function AddNamedInput(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
```

To keep existing option-creation code, bind the returned ID instead:

```papyrus
Int id = AddTextOption("Status", "Ready")
BindOption("status", id, "Automatic help.")

AddTextOptionST("ApplyState", "Apply", "Select")
BindStateOption("apply", "ApplyState", "Automatic help for an ST option.")
```

`Bool BindOption(String a_key, Int a_option, String a_help = "")` and
`Bool BindStateOption(String a_key, String a_stateName, String a_help = "")`
are valid during `OnPageReset` only. Both reject empty/duplicate keys and a slot
already bound to another key. A failed named addition does not consume a slot
when its key is invalid. Do not use keys differing only by case.

`Int GetOptionID(String a_key)` resolves a current-page key, or returns `-1`
with a diagnostic. It is not a durable handle for later pages. Keys are rebuilt
each page reset; the same key may be used on different pages. Replacing a row
after `SetCursorPosition` removes its previous binding, help and ST association.
The existing 128-slot limit and SkyUI cursor fill modes still apply.

Sliders, menus, colours, keymaps and input use their existing SkyUI dialog
callbacks and typed value setters. These wrappers do not add automatic setting
storage or eliminate those callbacks in this initial SDK.

## Automatic and explicit help

With the extension enabled, help supplied at creation/binding is the default
for the row. A normal
`OnOptionHighlight` or `OnHighlightST` callback may override it using the normal
`SetInfoText`. An explicitly empty string clears it. Authors do not have to
forward a parent highlight callback to get default help.

New live methods:

```papyrus
Bool Function SetOptionLabel(String a_key, String a_text, Int a_token)
Bool Function SetOptionText(String a_key, String a_text, Int a_token)
Bool Function SetOptionHelp(String a_key, String a_text, Int a_token)
Bool Function SetLiveInfoText(String a_text, Int a_token)
```

- `SetOptionLabel`: updates the label/header of a named nonempty row.
- `SetOptionText`: updates a **TEXT** row's displayed value. Other types are
  rejected; use their existing typed SkyUI setters in ordinary synchronous callbacks.
- `SetOptionHelp`: replaces the cached automatic help, and immediately updates
  the footer only if that row is still highlighted. A future explicit highlight
  callback still has precedence.
- `SetLiveInfoText`: explicit page-level footer/status, independent of which
  row is highlighted. Normal subsequent highlighting can replace this status.

Labels and text values use the existing translation/HTML colour/font pipeline.
Help/footer text keeps the SkyUI plain-text/nested-translation behavior. Live
updates repaint existing rows without flushing buffers, resetting the page,
changing selection/scroll or closing dialogs. They only change presentation:
update your own variables and rebuild from those variables in `OnPageReset`.
Do not call the internal `WriteOptionBuffers` to refresh an existing page.

These functions return `false` on SDK validation failure. `true` means the
guarded update was submitted, not an acknowledgement that the player has seen
it: the host rejects it if the page changes before application.

## Safe delayed updates

`Int GetPageToken()` returns a positive token for this provider's ready page,
or `0` while disabled, unavailable or building. `Bool IsPageTokenValid(Int a_token)`
checks enable state, provider, page and current host publication. Tokens are deliberately
invalidated on reset, close, manager reset and game reload. The host separately
rejects work after Back, page switches, close or unload—even if Papyrus has not
yet received a close event. A same-page rebuild also changes the token.

```papyrus
Int token = GetPageToken() ; capture BEFORE waiting or starting work
Utility.WaitMenuMode(0.5)
If IsPageTokenValid(token)
    SetOptionText("status", "Finished", token)
EndIf
```

Never fetch a replacement token at the end of old work. Never persist tokens
as configuration or transfer them between providers. The SDK uses a persistent
per-provider generation in addition to the UI's token, so closing/recreating
the entire Journal does not make old author tokens valid again. Token counters
fail closed at exhaustion instead of wrapping. There is no polling/background
worker added by the SDK.

An inline wait inside `OnOptionSelect`/`OnSelectST` keeps the normal SkyUI
selection lock until that callback returns. If an operation should allow page
navigation while running, schedule it separately as the full example does.

The guards apply to the **new extension calls**. They do not make arbitrary
legacy SkyUI setters or mod gameplay work cancellation-safe.

## Diagnostics and limitations

Papyrus traces include `OpenMCM API 1 [ModName/PageName]` and identify invalid
keys, slots, types or stale tokens. Failed calls do not display repeated player
notifications or trigger automatic registration loops.

This is a small first API, not a completed declarative settings framework. It
does not implement presets, persistence, searchable lists, progress-bar widgets,
typed validation schemas or insertion/removal/reflow of controls. MCM Helper
still supplies its existing authoring and storage features separately.

Verification includes script/example compilation, the unchanged SkyUI ABI
contract, SDK source/lifecycle-model tests, actual compiled AS2 execution in
AVM1, and both FOMOD install projections. Ruffle/AVM1 tests are not Skyrim's
Scaleform or Papyrus runtime. Test the example and existing MCMs in Skyrim
before publishing new compatibility claims. The 2.0 host release number does
not make API 1 non-experimental or certify these features in-game.
