# OpenMCM Field Guide — a practical API 1 example

**Field Guide 1.0.0** is a small, usable expedition planner and a commented
authoring example. It adds one MCM with **Overview**, **Checklist**, and
**Preferences** pages. Use it to name a trip, choose a travel style, set a
personal packing target, and tick off your preparations. The overview reads
your character's current carried weight and carry capacity without changing
either value.

The example is deliberately self-contained: saved Papyrus variables are its
settings, ordinary SkyUI callbacks handle the controls, and OpenMCM API 1 adds
named options, automatic help, live presentation, conditional groups, and safe
page navigation. It does **not** alter inventory, actor values, movement,
quests, survival mechanics, or other mods' settings. The optional hotkey only
shows a summary notification.

## Requirements and compatibility

- OpenMCM **2.1.0** is the current host; the sample uses the API introduced in
  1.2.0-alpha.5. Use SKSE matching your game.
- The optional **Field Guide** component in `OpenMCM-2.1-FOMOD.zip`, or the
  same example supplied separately in `OpenMCM-Field-Guide-1.0.0.zip`.
- SkyUI itself only if you chose OpenMCM's **With SkyUI** installation mode.
  OpenMCM's standalone mode supplies the compatibility master used by the
  example.

MCM Helper is not required. The sample adds no DLL and does not require either
optional OpenMCM native component or Address Library. Those components' own
requirements still apply if you install them for another reason.

This is an **OpenMCM-dependent** example, not a mod that runs on stock SkyUI
alone. Its class extends `OpenMCM_ConfigBase`; inheriting SkyUI's API does not
make that class available without OpenMCM. The API remains experimental, and
successful compilation or automated checks are not a substitute for an
in-game test.

## Install and try it

1. Back up your saves and mod-manager profile. Prefer a separate development
   profile and a disposable save for inspecting or modifying the example.
2. Install the full OpenMCM host. In the 2.0 FOMOD's **Practical API example**
   step, select **Install Field Guide - practical API example**; it is omitted
   by default. Keep whichever OpenMCM host mode you
   already use; the sample works with standalone and With SkyUI modes.
3. Enable `OpenMCM_FieldGuide.esp` after its `SkyUI_SE.esp` master. Alternatively,
   with a compatible host already installed, install the separate
   `OpenMCM-Field-Guide-1.0.0.zip` through your manager. Use **one** copy of the
   sample, not both the FOMOD component and separate archive. It is a teaching
   mod, not a patch or component required by OpenMCM itself.
4. Launch through SKSE, load your test save or start a test game, and let the
   MCM register. Open **OpenMCM Field Guide** in the MCM list.
5. To examine the extensions, enable **OpenMCM > Status > Runtime > Enable
   OpenMCM API**. The host leaves this switch off by default. Return to Field
   Guide so its page is rebuilt with the new enable state.
6. Save only to your test save if you want to retain the sample's settings and
   the API enable choice.

The sample payload does not replace OpenMCM's SDK scripts, manager, Journal
interface, or SkyUI files. Installing and enabling the sample is the point at
which its startup quest and settings become part of your game; merely building
or reading the example does not deploy anything to the game directory.

### A practical walkthrough

On **Preferences**, name a trip such as `Whiterun supply run`, choose a travel
style, and set a packing budget below your character's actual carry capacity.
The budget is your own planning threshold: changing it does not raise or lower
the game's carry limit. Return to **Overview**, read the weight/capacity snapshot and use the explicit
refresh action after changing what you carry.

Open **Checklist** and tick off supplies, equipment, and route preparation.
These are manual reminders, not automatic inventory or map checks. Changing
the checklist enable setting makes its dependent controls available or
unavailable together; the setting is also used when rebuilding the page, so
the result survives closing and reopening the MCM.

On **Preferences**, choose the load-heading accent colour and optionally assign
an unused keyboard key for summary notifications. The hotkey is
unbound by default and does not start background monitoring or gameplay work.
Use **Checklist > Clear checklist** to inspect a standard SkyUI state-based
confirmation dialog; cancel it first, then confirm it. Only the three
checkmarks are cleared. The hotkey accepts keyboard scan codes 1–255; mouse
and controller bindings are deliberately rejected. A conflicting assignment
requires confirmation; cancelling retains the previous key. Unmap stops the
listener, and disabling the guide also unregisters its key.

With the API enabled, use the navigation buttons rather than the sidebar to
see `SetCurrentPage` in action. Trigger the delayed refresh and immediately
switch pages or close the MCM. Old delayed work must not overwrite the new
page. Trigger it again and stay on the same page to observe the live status,
value, help, and footer updates without a full page rebuild.

### What happens with the API disabled?

The ordinary settings and controls remain usable. Named additions still
produce normal SkyUI option IDs; regular dialogs and typed setters still
work. Explicit highlight help provides the legacy fallback. The sample
disables extension-only navigation and delayed-refresh actions and uses
ordinary page rebuilding where an immediate legacy fallback is appropriate.

The sidebar remains the normal way to change pages. The disabled state is a
supported teaching case, not an instruction to turn the entire host API on
silently from a mod.

## Read the code in this order

In the source checkout, start at `examples/field-guide/OpenMCM_FieldGuide.psc`,
then `plugin` and `BUILDING.md` beside it.

The main 2.0 FOMOD puts the Papyrus file under
`components/field-guide/Data/Source/Scripts/OpenMCM_FieldGuide.psc`, and keeps
the walkthrough, `Source/Plugin` records and `Docs/BUILDING.md` below
`examples/field-guide`. The standalone sample ZIP instead puts the script
under `Data/Source/Scripts`, with `Source/Plugin` and `Docs/BUILDING.md` at its
root. The selected sample installs its readable script to Skyrim's
`Data/Source/Scripts/OpenMCM_FieldGuide.psc` in either case.

| Practical feature / option key | Implementation to examine |
| --- | --- |
| All pages and named controls | `OnPageReset`; `AddNamed*` creates all eight standard control types. |
| `enabled`, dependent checklist/action rows | `OnOptionSelect` → `RefreshEnabledGroup`; `FeatureFlags`/`DelayedFlags` rebuild the same conditions. |
| `load`, `budget_status`, `check_summary` | `ReadLoad`, `PaintSummary`, `LoadText`, `BudgetText`, `ChecklistText`; real actor reads, no actor writes. |
| `trip_name` | `OnOptionInputOpen/Accept`; raw input bounded to 40 characters, escaped by `EscapeLabelText` only when displayed in MCM fields. |
| `travel_style`, `budget`, `accent` | Matching `OnOptionMenu*`, `OnOptionSlider*`, `OnOptionColor*` callbacks and typed setters. |
| `summary_key` | `OnOptionKeyMapChange`, `GetCustomControl`, `RebindSummaryKey`, `OnKeyDown`; default unbound, menu guard, conflict confirmation. |
| `go_overview`, `go_checklist`, `go_preferences` | `OnOptionSelect` → `SetCurrentPage`, using exact raw page names. |
| `delayed` | `QueueRefresh` → self-sent `OnDelayedRefresh`; request generation, captured token, close/reload cancellation. |
| `clear_checks` | `ResetChecklist` state + `BindStateOption`; `ShowMessage` confirmation and ordinary toggle setters. |
| Per-control defaults | `OnOptionDefault`; checklist action also demonstrates `OnDefaultST`. |

`PaintSummary(token, False)` is the delayed worker's guarded path: if its scope
expires it must return, never fall back to resetting another page. Synchronous
button callbacks may use the ordinary page-reset fallback with the API off.

Weights are displayed as whole units (fractional parts are truncated). The
two-second refresh is intentionally an opt-in teaching exercise; the real
weight read itself does not need a delay.

1. **Saved fields and initialization.** Find the trip, budget, checklist,
   appearance, and hotkey settings. Their values live in the savegame. The
   sample's own `GetVersion()` is its settings-migration version, not the
   OpenMCM SDK version.
2. **`OnConfigInit` and `OnPageReset`.** These establish the menu's raw name and
   page names, then recreate the controls from those saved values. Named keys
   are page-local bindings recreated during each build.
3. **Ordinary option callbacks.** Follow selection and dialog callbacks from a
   numeric `a_option` through `GetOptionID(...)` to the relevant setting.
   Keep the standard typed SkyUI setters for toggles, menus, sliders, colours,
   inputs, and keymaps.
4. **Presentation helpers.** Follow the named status rows and live-update
   helpers. The UI is a view of the saved variables, not the source of truth.
5. **Delayed work and lifecycle.** Inspect the one-shot self-sent mod event,
   its captured page token, and its request generation. Then read cancellation
   on close/reload before reusing that pattern.
6. **The reset state.** This shows that normal `Add*OptionST` callbacks and
   `BindStateOption` coexist with named non-ST options.

### API rules illustrated by the sample

- Add or bind names **only during `OnPageReset`**. A key is not a permanent
  handle to a numeric option ID; resolve it on the current page.
- Obtain a page token at the **start** of the operation, before a wait or
  other delayed work. Never obtain a fresh token at the end of old work.
- A live-update return value means the request passed the SDK's checks and
  was submitted. It is not confirmation that the asynchronous UI displayed
  it. The host checks ownership and page publication again.
- Keep your settings in your own variables and rebuild the UI from them.
  `SetOptionLabel`, `SetOptionText`, and `SetOptionsEnabled` change
  presentation; they do not save your mod's configuration.
- `SetOptionText` is for text-option values. A slider still uses
  `SetSliderOptionValue`; other typed controls keep their typed setters too.
- `SetOptionsEnabled` changes only the disabled flag. It is not a condition
  expression engine and does not replace guards in the setting callbacks.
- `SetCurrentPage` targets a published raw `Pages` entry. Call it after the
  page exists, not while `OnPageReset` is building it. Do not call `SetPage`
  directly or replace the host's selection lifecycle.
- Return from the selection callback before waiting so the manager can
  unlock input. The self-sent mod event is one-shot demonstration work, not a
  polling loop supplied by the SDK.
- Page-token guards protect the new presentation calls. They do not cancel
  arbitrary game changes, protect every legacy setter, or undo work already
  performed. The sample additionally checks its own request generation.

## Turn this into your own mod

Copy the sample into a new development project; do not edit the installed host
scripts. Replace the expedition settings with a small, well-defined feature
and keep its game logic separate from presentation helpers where practical.

Rename all of the identities, not just the name shown in the MCM:

| Identity | Why it must be deliberate |
| --- | --- |
| Script file and `Scriptname` | They must match each other and the script attached to your quest. Give your mod its own class. |
| `ModName` | The registry/browser name shown to players; do not publish another menu named Field Guide. |
| Plugin, quest editor ID, and startup SEQ | Your plugin owns its quest and the SEQ entry must refer to that plugin's actual startup quest FormID. Do not reuse the example's records blindly. |
| Custom mod-event name | Use your own namespace so another copy cannot collide with the example. Preserve the sender and request validation. |
| Page names and option keys | Update navigation destinations and every key lookup together. Raw page names/translation keys must match the `Pages` array; do not navigate using translated display text or keys differing only by case. |
| State names and `BindStateOption` | Rename both the ST option's state and its binding. Preserve the standard ST dispatch. |
| Your `GetVersion()` and migration logic | Increment for your own saved-setting migrations. `OpenMCM.GetAPIVersion()` reports the SDK API version and serves a different purpose. |

Compile against the OpenMCM SDK sources plus the matching Skyrim/SKSE script
headers. Attach your class to a start-game-enabled quest. Give that quest a
player reference alias using `SKI_PlayerLoadGameAlias`; it forwards load events
to the owning quest and has no `QuestScript` property to fill. Keep parent
lifecycle calls where the sample uses them, especially `OnGameReload`, so the
base class can invalidate old page contexts and perform normal registration.

Generate an appropriate SEQ for your plugin and verify the player alias,
attached script, quest flags, and plugin masters. The included plugin record
sources and build scripts are the reproducible reference for this sample;
changing only a `.psc` class name does not update those plugin records.

Ship your own plugin, PEX, and source/example documentation. Depend on OpenMCM
for its SDK; do **not** bundle replacement copies of `OpenMCM_ConfigBase`,
`SKI_ConfigBase`, `SKI_ConfigManager`, the Journal SWF, or compilation stubs.
If you need a stock-SkyUI-only edition, design and maintain a separate
`SKI_ConfigBase` implementation or a deliberate adapter; removing the API
checkbox does not remove this sample's base-class dependency.

### Persistence and removal

Settings in this sample are **per savegame**. They are not exported mod-setting
profiles and are not part of OpenMCM's optional shared browser preferences.
Changing one save does not promise to change another. If you add persistence
later, make that a separate, explicit contract rather than treating displayed
UI values as stored settings.

For a clean end to testing, exit Skyrim, disable the sample in the test
profile, and return to the save made before installing it. Do not overwrite a
valuable playthrough to test removing a scripted quest. The sample's normal
close/reload cancellation and hotkey handling are lifecycle behavior, not a
claim that arbitrary mid-playthrough script removal is safe.

## Suggested in-game checks before publishing a derivative

- Open all three pages with mouse and keyboard; use both sidebar navigation
  and API navigation buttons.
- Change every control, close/reopen the MCM, then save/reload. Confirm the
  stored values and help are still correct.
- Test with the API off, then on. Confirm ordinary controls remain usable
  while extension-only actions accurately show their unavailable state.
- Change the checklist enable condition and check the group immediately,
  after changing pages, and after reopening the MCM.
- Start a delayed refresh, then change page, rebuild the same page, close the
  Journal, or reload a save. No old result should paint a replacement page.
- Try hotkey assignment, replacement, conflict cancellation, and unmapping.
  The default unbound configuration must not claim a key or produce unsolicited
  notifications.
- Test reset confirmation both ways. Cancelling must retain the old settings;
  confirming must rebuild from the reset values.
- Test the OpenMCM host modes you intend to claim, using their proper masters
  and load order. Do not infer broad mod-list compatibility from a compiler or
  this example's limited feature set.

For the API contracts and their limitations, see the host's
`docs/OpenMCM-API.md`. Read the comments in `OpenMCM_FieldGuide.psc` alongside
this guide; they are the concrete implementation to adapt, not a promise that
the host stores settings or implements gameplay on an author's behalf.
