OpenMCM — Copyright (C) 2026 TheElderLord1337 and OpenMCM contributors.

Original OpenMCM code is free software: you can redistribute it and/or modify
it under the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.
It is distributed without any warranty, including the implied warranties of
merchantability or fitness for a particular purpose. See `LICENSE.txt` and
`README.txt`. Third-party components retain their own notices and terms; see
`THIRD_PARTY_NOTICES.md`. Earlier MIT notices are preserved in
`licenses/OpenMCM-previous-MIT.txt`, not withdrawn by this release.

# OpenMCM 2.1 — standalone or with SkyUI

**Release package: 2.1 (2.1.0).** Retains the repair for missing dialog parameter storage when
opening MCMs and slider/menu/colour dialogs, so saved initialization flags cannot
leave sliders with an empty range payload. Retains an optional
[Jaxonz MCM Kicker compatibility add-on](docs/Jaxonz-MCM-Kicker.md) to the full
FOMOD; the original Kicker SE mod is still required. The slider repair and Kicker
adapter still need in-game verification. The owner uploaded 2.1 and reported on
7 October 2026 that the Nexus listing was out of review and back online after
their compliance edits. Preserve the published ZIP and existing notices; see
[the recorded release baseline](release/OpenMCM-2.1.0-publication.md).

Package version: **2.1.0**. One full FOMOD installer; no required add-ons.
The main package combines standalone/SkyUI coexistence, a configurable MCM
browser, the opt-in author SDK and an optional practical Field Guide example.
The host version is **2.1.0**, the SkyUI-compatible MCM API remains **4**, and
the experimental OpenMCM extension API remains **1**. These are separate
version contracts: a package version bump does not change existing MCM APIs.

The FOMOD also supplies the full editable OpenMCM project under
`source/OpenMCM-2.1.0-Source.zip`, including ActionScript, Papyrus, both native
components, plugin YAML, examples, tests, build scripts and pinned browser
dependency source. `BUILD-SOURCE.txt` inside explains the build prerequisites.
No crash/hang dumps, personal diagnostics, compiled tool caches or extracted
Skyrim assets are included in that source archive. The separate browser-source
archive is retained for its provenance/hash records. Version 2.1 rebuilds native
version metadata, changes no gameplay logic, and is not a new in-game test result.

On 23 September 2026 the owner reported their current setup working and
approved publication. This is setup-specific confirmation, not exhaustive
verification of the newer API, browser, SkyUI coexistence or optional Field
Guide. The detailed compatibility results below apply to standalone 1.1.0.

The integrated Redone-style browser provides search, favourites, hidden entries,
display names, priorities, sorting and save-local preferences. Optional shared
browser storage adapts Redone's original native persistence code, with GPL
licence and corresponding source included. The 128-menu registry stays intact
for MCM Helper compatibility. Do not install MCM Menu Redone alongside this
package. See [the browser guide](docs/OpenMCM-Browser.md) for controls, storage,
requirements and limitations. This integration does not include every
Redone feature; it does not export mod settings or claim an exit-crash fix.

The opt-in API also gains guarded page navigation and conditional option groups
for mod authors. Existing menus are not automatically converted to use them.

Retains **OpenMCM > Status > Runtime > Enable OpenMCM API**, with version
and explanatory hover text. The option is off by default and saved per savegame.
It enables automatic help and live text/status updates for authors using API 1;
normal MCM controls, SkyUI API 4 and MCM Helper remain available when it is off.
Named controls/IDs remain available as a fallback. It does not convert old MCMs,
require the optional native DLL, or fix the separately reported exit crash.

Retains the installer XML correction for Vortex's invalid-character
error in an earlier preview. Both XML files use double-quoted
encoding declarations, and every FOMOD build checks the final ZIP through the
Nexus installer's encoding conversion.

The installer detects SkyUI using `SkyUI_SE.esp` plus its BSA or the loose
`SKI_Main.pex` and `Interface/skyui/config.txt` markers. It preselects the
recommended mode. The plugin filename alone is insufficient because standalone
OpenMCM deliberately uses it too. Undeployed/hidden files, unusual installations,
or saved installer presets can affect detection: verify the choice and change
it manually if necessary. This detects presence, not an exact SkyUI version.

| Installer mode | MCM host | Other interfaces and plugin ownership |
| --- | --- | --- |
| Standalone — no SkyUI | OpenMCM | Original standalone compatibility plugin; do not enable SkyUI |
| With SkyUI | OpenMCM | Keep real SkyUI installed; its ESP, inventory, favorites, widgets, settings and translations remain untouched |

OpenMCM implements the SkyUI 6 MCM API v4 contract for existing MCMs without
requiring SkyUI. It includes its own compatible Papyrus scripts and interface
implementation. It does not provide SkyUI's inventory, favorites, HUD, widgets,
or other non-MCM features. The interface follows SkyUI's layout and interaction
model, but is not a pixel-identical copy and does not reproduce its animations.

A separate [basic MCM Bridge SDK add-on](src/compat/mcm-bridge/README.md) is available
as a 0.1.0 preview for OpenMCM-authored menus in Bridge-only profiles. It is not included
in the published 2.1 FOMOD and must not be used to run both full hosts together.
Its advanced API operations are deliberately unavailable; named controls use
Bridge's original callbacks. Compilation, 54 focused tests, package validation
and an extracted-source rebuild passed; in-game verification is still required.
See its own installation and testing limits.

## Changes retained from 1.1

- Working mouse selection for MCMs, pages, settings, and dialogs, using
  persistent lists and component-owned focus.
- Corrected option-text font and colour defaults, retaining individual mods'
  HTML colours and styles, including mixed colours and intentionally black text.
- Registration, menu-state, and text-input ownership corrections since 1.0,
  consolidated into one full package.

The owner confirmed mouse input, text, colours, and every MCM in their current
mod list working in-game in standalone 1.1.0. Version 2.0 retains those
rendering/input corrections while adding opt-in features; broad regression
testing remains important. See [COMPATIBILITY.md](COMPATIBILITY.md) for the seven
third-party MCMs and their installed versions. These are owner-reported results
for that setup, not a guarantee for every mod, version, or controller workflow.

## Opt-in OpenMCM API 1 (experimental)

Existing `SKI_ConfigBase` and MCM Helper menus do not need to be rewritten.
Authors can instead extend `OpenMCM_ConfigBase` for named options, automatic
help on ordinary and state-based options, and page-scoped live label, text-value
and footer updates. These repaint without resetting selection or scroll.
The SkyUI API remains version 4; OpenMCM's extension version is separate.

See [the API guide](docs/OpenMCM-API.md) and
[the compiled-as-a-test example](examples/OpenMCMApiExample.psc).
Both installer modes include the SDK scripts and sources. The small examples
are source documentation, not automatically registered gameplay quests. The API is still
experimental; it does not add presets, new widgets or automatic layout reflow.

## Optional Field Guide teaching MCM

The same FOMOD includes **OpenMCM Field Guide 1.0.0**, omitted by default.
Choose **Practical API example > Install Field Guide - practical API example**
to install a working example quest, compiled script, startup SEQ
and readable Papyrus source. It is a small expedition planner with live
carry-weight readouts, a manual checklist, a planning budget, colour/input
controls and an optional unbound-by-default keyboard summary shortcut. It does
not change inventory, actor values or another mod's settings.

The [author walkthrough](examples/field-guide/README.md), annotated script,
editable plugin records and build instructions demonstrate named controls,
automatic help, conditional groups, page navigation and stale-page-safe delayed
updates. The sample depends on OpenMCM, not MCM Helper, and requires no native
component. Enable the Runtime API option to try its extension-only actions;
ordinary controls still work with it off. Do not install the separate Field
Guide archive as well as selecting the same sample in the main installer.

## Requirements

- SKSE matching your game runtime; launch the game through SKSE.
- MCM Helper separately, if a provider mod requires it, in a version matching
  your game. OpenMCM does not replace MCM Helper.
- Each provider mod's own requirements, including skeletons and other native
  plugins where applicable.

In **standalone mode**, do not enable SkyUI or SkyUI Community. In **With SkyUI
mode**, the actual SkyUI package is required: keep its `SkyUI_SE.esp` and BSA.
OpenMCM overrides only the MCM base/manager scripts and Journal, and adds its
own `OpenMCM.esp` status quest. There is still exactly one MCM manager, at
SkyUI's original identity used by MCM Helper. The coexistence plugin does not
contain copies or overrides of SkyUI quests and does not bundle SkyUI assets.

Coexistence was audited against installed SkyUI Community 6.8 and pinned 6.11
source. Other SkyUI versions are not verified. The OpenMCM Journal replaces
SkyUI's Journal, not merely its MCM panel: SkyUI-specific Journal changes or
third-party Journal replacements are not preserved. Other interfaces remain
SkyUI's responsibility. No SkyUI error checks are disabled or versions spoofed.

## Install or upgrade

1. Fully exit Skyrim and keep a save backup.
2. Install `OpenMCM-2.1-FOMOD.zip` (build output: `OpenMCM-2.1.0-FOMOD.zip`) with a FOMOD-capable mod manager.
   Review its detected mode. Do not manually install the entire archive's
   `modes` folder; the installer maps exactly one selected branch to Data.
3. Replace the previous OpenMCM main package; disable old OpenMCM mouse/diagnostic
   add-ons. The old standalone `SkyUI_SE.esp`, shared scripts and translation
   overrides must not remain if choosing With SkyUI mode.
4. Keep `SkyUI_SE.esp` enabled. With SkyUI also enable `OpenMCM.esp` after it.
   Let OpenMCM win Journal, `SKI_ConfigBase.pex` and `SKI_ConfigManager.pex`
   conflicts, but keep the real SkyUI plugin, translations and other scripts.
   MCM Helper's `SKI_ConfigMenu.pex` must remain available when it supplies that
   provider. Deploy and launch through SKSE.
5. Open the pause menu, then **System > Mod Configuration**.

If you selected the optional Field Guide, also enable `OpenMCM_FieldGuide.esp`
after `SkyUI_SE.esp`. Existing users of its separate sample package should
choose one provider of those files, not keep both copies active. Its own
version remains 1.0.0; selecting it does not enable the experimental API.

The optional chargen component is a separate choice in the same installer,
**omitted by default**. If intentionally including it, preserve custom INI
settings; the installer cannot merge an existing INI. See its runtime limits below.
Shared browser preferences and the Field Guide are independent optional choices,
also omitted by default. Save-local preferences require neither native component.

Standalone's identities/save-migration versions are retained. However,
**switching modes on an existing save is not a verified migration**: the
minimal standalone plugin and full SkyUI plugin have different quests despite
sharing a filename. Test coexistence in a separate profile/new game or a save
already using actual SkyUI. Do not clean a save or uninstall/save/reinstall as
a migration workaround. Keep a backup and do not overwrite your only save.

## Optional native component

The optional `SKSE/Plugins/OpenMCMRuntime.dll` retains the existing
character-creation precache adjustment for **Skyrim 1.7.104.0 only**.
It is not required for MCM. Omit it on other runtimes to avoid SKSE rejecting
an incompatible plugin; the Papyrus/Scaleform MCM host does not depend on it.

Its INI default remains `DisableChargenPrecache=1` under `[Patches]`.
Set it to `0` and restart Skyrim to disable the adjustment, or omit the DLL.
The component checks original instruction bytes and defers to a loaded
RaceMenu or Engine Fixes instead of combining precache patches. Selected
head parts still load on demand, which can take time.

The native adjustment has automated checks but **no confirmed in-game fix
verification**. The separately reported exit-to-desktop crash is **not claimed
fixed**. The 2.0 version bump does not add a new native patch or establish the
cause of that crash.

## Troubleshooting

- For missing menus or stale UI, check that this package wins Journal/script
  conflicts and that `SkyUI_SE.esp` is enabled. Fully restart Skyrim after
  replacing scripts or interface files.
- Mouse diagnostics are available under **OpenMCM > Status**, disabled by
  default. They are not required for normal operation.
- Provider-specific missing pages can reflect that mod's prerequisites.
  For example, check XPMSE's Info page if its Styles page has no options.
- The optional native plugin logs to the Skyrim SKSE folder under your
  Documents directory. If SKSE rejects it before loading, consult SKSE's log.

## Build and verify (source checkout)

Requires Windows PowerShell 5.1 or 7, Visual Studio 2022+ / Build Tools with
Desktop development with C++ and a Windows SDK, x64 Java 8+ on `PATH`,
Python 3.10+, and a legal local Skyrim installation. The first build downloads
checksum-pinned tools. The release ZIP is for installation, not a source checkout.

```powershell
.\build.ps1 -SkyrimPath "E:\SteamLibrary\steamapps\common\Skyrim Special Edition"
python -B tools/check_mcm_contract.py . --profile source
python -B -m unittest discover -s tests -p "test_*.py"
python -B tools/check_fomod_package.py dist/OpenMCM-2.1.0-FOMOD.zip
.\scripts\Test-FomodXml.ps1 -ArchivePath .\dist\OpenMCM-2.1.0-FOMOD.zip
```

The default output is `dist/OpenMCM-2.1.0-FOMOD.zip`. `SKYRIM_SE_PATH` or Steam
library discovery can supply the game path. Build outputs, diagnostic fixtures,
tools, symbols, and test executables are not shipped. The build does not deploy
to Skyrim or upload to Nexus. `-PackageFormat Standalone` builds the legacy
single-mode layout for development; never use that layout with real SkyUI.

The build compiles Papyrus and native code, generates the compatibility plugin,
derives the Journal from the locally installed game, and compiles the independent
interface. It checks compiled contracts, runs regressions, and reopens the ZIP
to verify `OpenMCM_SHA256SUMS.txt` and the supported host/native/browser/sample/Kicker
installer combinations separately.
Automated tests do not replace in-game testing.
`-SkipTests` skips the Python checks; do not use it for release validation.

See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
for original-source licensing, upstream references, tool licenses, and the
separate status of Bethesda-derived Journal assets.
