# OpenMCM development history through 1.0.1-rc.8

Archived pre-1.1 README, retained for investigation and development history.
Candidate statuses and installation instructions below describe their original
builds; they are not current release instructions. See the root README,
COMPATIBILITY.md, and release/OpenMCM-1.1.0-notes.md for the 1.1 release.

OpenMCM is a standalone Mod Configuration Menu runtime for Skyrim Special
Edition and Anniversary Edition. It implements the SkyUI 6 MCM contract without
shipping or loading SkyUI's scripts, interface classes, artwork, or native code.

Existing MCMs continue to extend `SKI_ConfigBase`. MCM Helper remains an
optional, separate dependency for mods that use it; OpenMCM exposes the plugin,
quest, Papyrus fields, Scaleform path, methods, option types, and `SKICP_*`
events that MCM Helper expects.

## Compatibility

| Consumer | Status |
| --- | --- |
| SkyUI 6 MCM API v4 | Implemented, including input options |
| Classic `SKI_ConfigBase` menus | Implemented |
| State-based option API | Implemented |
| MCM Helper | Integration contract implemented and checked; install MCM Helper separately when a mod requires it. Live integration verification is still needed. |
| Keyboard, mouse, and controller navigation | The owner confirmed the rc.6 mouse fix in-game. That input implementation is retained in rc.8; controller and universal MCM coverage remain unverified. |
| Slider, menu, color, keymap, input, and message dialogs | Implemented |
| Custom-content SWFs | Implemented |
| SkyUI inventory, favorites, HUD, widgets, or item-card features | Out of scope |

SKSE is required. The MCM host itself is implemented in Papyrus and Scaleform
and does not depend on OpenMCM's optional native component. SKSE and native
plugins such as MCM Helper must still match the installed game runtime.

The package also includes `OpenMCMRuntime.dll`, an optional character-creation
precache fix for **Skyrim 1.7.104.0 only**. This is separate from MCM support.
On other game versions, omit the DLL to avoid an SKSE incompatibility warning;
the MCM host remains usable without it. See the rc.3 section below.

OpenMCM deliberately owns the compatibility names `SkyUI_SE.esp` and
`Interface/quest_journal.swf`. **Do not install it alongside SkyUI or SkyUI
Community.** A mod that needs SkyUI features beyond MCM is not a candidate for
this replacement.

### Independently recreated SkyUI-style interface

Version 1.0.0 carries forward the independently drawn interface and the SkyUI 6
layout and interaction work from 0.2.8. Stage geometry, text metrics, list focus,
footer, scroll indicators, and dialog layouts were compared with SkyUI's MCM.
The interface is not a pixel-identical copy: decorative shapes and control
prompts are recreated, and SkyUI's fade animations are not implemented. The
authored 16:9 layout is preserved on ultrawide displays. No SkyUI artwork,
interface classes, SWFs, or other SkyUI assets are bundled.

### Validation scope

Version 1.0.0 was verified working in-game by the project owner in their
installed setup. A whole-game freeze and crash were reported with 1.0.1-rc.1
installed. The 1.0.1-rc.2 input-ownership correction and 1.0.1-rc.3 native
precache correction have automated verification only. The native correction
targets the bulk-loading wait chain found in two captured freezes; it has
**not yet been verified in-game** and is not a confirmed fix for the separately
reported crash. The build
compiles the implementation, checks the
resulting plugin, PEX and SWF contracts, and runs automated regression tests.
This in-game report and the automated checks do not prove
compatibility with every MCM or replace live checks of controller input,
save/load timing, custom content, or MCM Helper. Provider mods retain their own
requirements; OpenMCM does not supply them.

On 2026-09-12 the owner confirmed that rc.6 fixed mouse input, and reported
nearly black/missing-glyph option text in Skyrim Unbound. Version rc.7 corrects
the HTML format readback, but the owner's rc.7 retest still showed the fault.
Version rc.8 additionally supplies explicit HTML defaults and uses the known
plain-text format path for markup-free options. This new text/color correction
still needs an in-game check; the mouse handlers are unchanged.

## Install

1. Build the package as described below, or use the completed zip in `dist`.
2. Install the zip with a mod manager and enable `SkyUI_SE.esp`.
3. Keep SKSE installed and launch Skyrim through SKSE.
4. Open the pause menu, choose **System**, then **Mod Configuration**.

Version rc.8 is a **complete mod package**, not an add-on. When upgrading,
fully exit Skyrim, disable/remove the old OpenMCM mouse diagnostic/update
add-ons, and replace the main OpenMCM package with `OpenMCM-1.0.1-rc.8.zip`.
Deploy the new version and keep `SkyUI_SE.esp` enabled. An old add-on must not
win the Journal or status-script conflicts. No new game is required. Preserve
any intentional local `OpenMCMRuntime.ini` settings during the upgrade.
If you deliberately omitted the optional native DLL, keep it omitted.

If a mod lists MCM Helper as a requirement, install the correct MCM Helper
release for the game runtime as well. Do not remove that dependency merely
because OpenMCM supplies the menu host.

### Version 1.0.1-rc.8 — explicit option-text defaults

The rc.7 text change was insufficient in the owner's game. Option text without
markup or entities now uses the same explicitly formatted plain-text path as
the readable sidebar. HTML text gets explicit inherited font, size, color,
style and paragraph defaults corresponding to SkyUI's authored fields. Inner
mod tags remain intact, including mixed colors and deliberately black text.
Leading translation tokens are resolved before markup is added.

This remains one complete package, with the confirmed mouse implementation
unchanged. No font replacement assets, input changes, provider edits or native
behavior changes are included. In-game text verification remains required.

### Version 1.0.1-rc.7 — insufficient text correction (historical)

Option headers, labels and values now follow SkyUI's HTML format readback:
after assigning HTML, reuse the parsed text format to restore spacing/kerning,
instead of applying a fresh format object that may bring unrelated font,
size or color defaults. Mixed HTML colors/font styles and explicit black text
are retained. Reused fields restore their clean default for the next row.

This package includes the confirmed rc.6 mouse fix, the MCM scripts/plugin,
and the existing optional runtime component. No add-on is required. Mouse
handlers, registration, dialogs, native behavior and native configuration
defaults are unchanged. The separate shutdown crash is not claimed fixed.

### Version 1.0.1-rc.6 — independent list and focus ownership (historical)

The input implementation now follows the audited SkyUI Community 6.11
component model: separate persistent mod/page/options lists, pooled rows with
ordinary transparent hit geometry, list-owned selection and scroll state,
selection/press events, and focus on the active component. Dialogs save and
restore focus and disable underlying lists. The rc.5 blanket Journal hiding
and full-screen modal mouse blocker are removed. Registration and the MCM API
remain unchanged; no SkyUI runtime components or artwork are bundled.

The owner confirmed this version's mouse fix in-game on 2026-09-12. The old
two-file mouse update is superseded by the complete rc.8 package above. This
is not a shutdown-crash fix.

### Version 1.0.1-rc.5 — withdrawn approach (historical)

The in-game mouse probe recorded raw movement/press/release events and one
MCM-row press. It also identified the faded vanilla Journal's
`CreationListPanel.cList_mc.Entry3` as the picked mouse target through blank
MCM content. The screenshots were not taken over an MCM name, so this proves
background click-through, not the cause of every reported failed row click.

While MCM was open, rc.5 made the vanilla Journal fader invisible and
disables its hit testing. Drawing MCM at a higher depth was not sufficient:
noninteractive artwork does not form an AVM1 mouse barrier. The original
flags are captured once and restored on panel close or unload, before focus
returns to the Journal. This is an adaptation for the independent host and
modern vanilla Journal, not an additional SkyUI dependency.

The optional mouse probe remains available under **OpenMCM > Status**.
This candidate does not change native patch behavior, registration, or the
separate exit-to-desktop crash investigation. It still requires an in-game
retest of MCM names/pages/settings and normal Journal controls after closing
MCM. The temporary mouse-only update contains no DLL or INI; it can replace
the diagnostic add-on without changing the installed native component.

### Diagnostic build — initial mouse investigation

The owner confirmed that rc.4 still responds only to keyboard input. The
installed Journal hash matches rc.4; this is not an old SWF deployment.
Real pointer movement/clicks in Ruffle successfully activate a mod both in
the compiled standalone panel and the complete compiled Journal. Ruffle is
not Skyrim's Scaleform runtime, so these results do not establish an in-game
fix. The earlier callback-only tests did not cover native target picking.

This diagnostic build adds **OpenMCM > Status > Mouse input diagnostics**.
Enable it with the keyboard, return to the MCM list without closing the
Journal, then move over and click a mod name. The passive overlay shows raw
mouse delivery, the actual row callbacks, pointer coordinates and the target
reported by Scaleform. Send a screenshot with the pointer still over the row.
It is disabled by default, unregisters on menu close/unload, and does not
reroute input, change focus, write logs, or install native hooks.

This is an evidence-gathering build, **not a claimed mouse or crash fix**.
The latest crash report establishes an exit-to-desktop scene-cleanup failure,
not a click-handler crash; its cause is not assigned to a mod. See
[the shutdown analysis and controlled comparison](diagnostics/2026-09-08-exit-to-desktop-crash.md).
The optional native precache implementation is unchanged. No installed files
or Nexus releases are changed by building this package.

### Version 1.0.1-rc.4 (mouse interaction and option font colors)

The dynamic MCM layer now stays above the fading vanilla Journal. Previously,
opening MCM unconditionally swapped it behind the Journal; that animation
reduces alpha without making the Journal invisible, leaving its mouse targets
above MCM. Opening and closing MCM no longer swaps the vanilla layer's depth.

Hover and selection changes now redraw existing mod/page/option rows and menu
dialog rows in place. Slider dragging also updates the existing track and
value field. These actions no longer destroy the MovieClip receiving the
mouse event. Actual list changes and scroll-window changes still rebuild the
appropriate content.

Option headers, labels and displayed values now accept HTML formatting,
including `<font color="#RRGGBB">`, matching SkyUI's option renderer. Mixed
colors are preserved instead of being reset to the default white. Titles,
info/message text, list names and editable input keep their existing plain-text
behavior; this does not introduce HTML support where SkyUI uses plain text.

These changes have automated source/body tests and compiled SWF checks, but
need an in-game mouse/color retest. The Papyrus registration protocol and rc.3
native precache patch are unchanged. The native patch remains optional,
restricted to Skyrim 1.7.104.0 and not yet verified in-game. Building does not
deploy to the game or update Nexus. Fully exit Skyrim, replace the previous
OpenMCM package in the mod manager, deploy, and test MCM selection, settings,
menu choices, slider dragging and colored option text.

### Version 1.0.1-rc.3 (unverified character-creation precache candidate)

Two freeze snapshots showed the main thread waiting for the character menu to
finish preloading many head-part models, including KS Hairdos hairstyles.
Loading was still progressing between snapshots. This was not an MCM
registration loop or evidence of a particular broken hairstyle.

The integrated `Data/SKSE/Plugins/OpenMCMRuntime.dll` disables that bulk
character-creation precache operation on the verified executable layout for
Skyrim **1.7.104.0**. Selected head parts continue to load on demand. This
component adds no input, slider, polling, or render-loop hooks and does not
edit the game executable or hair assets on disk. The MCM Papyrus and
ActionScript implementation is unchanged from rc.2.

The native patch is enabled by default in
`Data/SKSE/Plugins/OpenMCMRuntime.ini`:

```ini
[Patches]
DisableChargenPrecache=1
```

Set `DisableChargenPrecache=0` and restart Skyrim to disable it. Alternatively,
omit `OpenMCMRuntime.dll`; the MCM does not require it. The plugin checks the
runtime and original instruction bytes before changing process memory. An
unrecognized layout or existing hook leaves the patch disabled. It also
defers to a loaded RaceMenu (`skee64.dll`) or Engine Fixes (`EngineFixes.dll`)
instead of combining precache patches, even if that other plugin's fix is
disabled. Do not install an incompatible version of either plugin to address
this stall.

On a supported runtime, the result is logged in
`Documents/My Games/Skyrim Special Edition/SKSE/OpenMCMRuntime.log` (including
redirected Documents folders). For an unsupported runtime, SKSE can reject
the DLL before it starts; consult the SKSE log instead.

Fully exit Skyrim before installing this candidate through the mod manager
in place of the old OpenMCM package. Keep a save backup. No new game, quest
reset, or load-order change is required by the patch. Test new-game character
creation, sex changes, hair and face/body sliders, and normal MCM registration,
page selection, and text dialogs before treating this candidate as verified.
On-demand loading can still take time when choosing a complex hairstyle.
The build does not deploy files to Skyrim or upload a release.

### Version 1.0.1-rc.2 (unverified input-ownership candidate)

OpenMCM now acquires and releases only its own SKSE text-input request. Ordinary
dialogs, unused Journal unloads, and repeated cleanup no longer decrement the
shared input count. Text acceptance/cancellation releases ownership once before
sending callbacks. A missing SKSE bridge does not falsely record acquisition.
Focus and key-remapping protocols are unchanged; no Ctrl-specific workaround
is applied.

This corrects a demonstrable input-lifecycle defect, not a proven cause of the
reported whole-game freeze or crash. Do not treat this candidate as a verified
fix or publish it as one. Crash/hang evidence and in-game regression testing
are still needed. The installed game is not modified by building this package.

### Version 1.0.1-rc.1 (performance candidate; runtime issues reported)

Registry searches now use built-in array lookups instead of scripted loops.
The original registration ABI, exact provider identity checks, sparse IDs,
saved-registry repair, and duplicate-callback suppression remain intact.
Closed Journals no longer receive mod-list updates. Redundant heartbeat
publications, delayed Journal-opening publications, and the extra readiness
broadcast on Journal close are removed. The existing panel request/acknowledgment
handshake still handles dynamic attachment and older saves.

These changes reduce confirmed excess OpenMCM work; they are not yet a verified
fix for sex/slider stalls in character creation. No character-creation assets,
native DLLs, other mods, saved-field layouts, or plugin identities are changed.
Fully exit Skyrim and install this candidate in place of the old OpenMCM
package. Keep a save backup. No console reset is required. Retest the affected
character-creation controls and MCM registration/pages on both a new game and
an existing save before publishing this candidate.

### Version 1.0.0

This release packages the registration, selection, dialog, and interface work
from 0.2.8 as version 1.0.0. The runtime is unchanged from 0.2.8; the version bump
does not change Papyrus API or save-migration versions.

Fully exit Skyrim before upgrading. Install 1.0.0 as a new version in your mod
manager, disable the previous OpenMCM package, enable `SkyUI_SE.esp`, and deploy.
Do not enable SkyUI or SkyUI Community alongside it. No new game or quest reset
is required when upgrading from 0.2.8. Keep a backup of your save before changing
installed mods.

### Updating from 0.1.0

Version 0.1.1 fixed repeated menu registration on the manager heartbeat; that
fix remains included in 1.0.0. After replacing 0.1.0, an affected existing save
may still contain registry entries created before the fix. Open the console
once after loading that save and run:

```text
setstage SKI_ConfigManagerInstance 1
```

Wait for the menus to register once, save, and continue normally. New saves and
saves that never showed the repeated notification do not need this reset.

### Updating from 0.2.0

Version 0.2.1 fixes the Journal startup race where registration could succeed
but the MCM list remained on the waiting message. It also corrects ultrawide
stretching and two overlapping welcome-screen decorations. No console reset is
needed when updating from 0.2.0.

### Updating from 0.2.1

Version 0.2.2 makes list refreshes work with existing saves whose SKSE co-save
did not acquire 0.2.1's newly introduced event subscription. It reuses the
long-established SkyUI selection channel for a non-selection refresh sentinel,
retries briefly until the panel acknowledges the list, and republishes after
registration and during Journal startup. It also fixes the remaining title,
welcome-mark, and empty-message alignment issues. No console reset is needed.

### Updating from 0.2.2

Version 0.2.3 repairs an older save whose manager retained a menu name and
numeric count after losing the corresponding Papyrus object registry. Each MCM
can recover a cached manager/slot pair after that registry is rebuilt. Valid
registries are preserved, and a missing name cache is reconstructed from their
menu objects.

### Updating from 0.2.3

Version 0.2.4 follows SkyUI's original registration protocol more closely:
every manager-ready heartbeat calls the established `RegisterMod` function,
and the manager deduplicates the exact menu object. No new manager method is
required in the client registration path, successful repeats do not rerun
`OnConfigRegister`, and failed `BUSY` attempts retry on a later heartbeat.

The package also includes `Seq/SkyUI_SE.seq` so the manager and a small built-in
OpenMCM status menu start reliably when the plugin is introduced to an existing
save. Seeing **OpenMCM** in the list confirms that the manager, Papyrus bridge,
and Journal list are all connected.

### Updating from 0.2.4

Version 0.2.5 fixes the registration failure in 0.2.4. Caprica 0.3 emitted the
manager's referenced custom type as `sKI_ConfigBase[]`; Skyrim therefore left
the authoritative `_modConfigs` object array uninitialized even on a brand-new
game. The parallel name array still existed, which allowed a provider to appear
to receive slot 0 and produced a registration notification even though no menu
object was retained.

The build now canonicalizes and verifies every compiled `SKI_*` custom-type
reference, restores SkyUI's direct registry allocation in `OnInit`, and refuses
to return a successful registration unless the object array exists and retains
the provider. Fully exit Skyrim before replacing 0.2.4 so the corrected PEX
files are loaded. The manager repairs the absent registry on the next load and
asks providers to register again; no quest-reset console commands are needed.

### Updating from 0.2.5

Version 0.2.6 corrects the populated MCM list against SkyUI 6's authored
geometry. Right-aligned mod and page names now end before the center divider,
and the selection fade remains inside the left pane.

It also restores SkyUI's mouse interaction model. Every mod, page, option, and
menu-dialog row has a full-width invisible trigger area and activates on mouse
press. Hovering no longer destroys the pending click target, so clicking a mod
name opens that MCM instead of only changing its highlight.

### Updating from 0.2.6

Version 0.2.7 fixes the active-MCM reset that could happen on every manager-ready
heartbeat. Re-registering an existing menu is now idempotent, as it is in SkyUI,
and a genuinely new registry snapshot updates the backing mod list without
replacing the selected MCM's page list, options, or custom content. Opening the
Journal still starts from a freshly rendered top-level mod list, while page
rows remain unselected until the player explicitly chooses one.

Fully exit Skyrim before replacing 0.2.6 so the new PEX and SWF are loaded. No
quest reset or new save is required.

### Updating from 0.2.7

Version 0.2.8 updates the SkyUI-compatible registration and selection path.
The built-in OpenMCM provider now occupies its own persistent quest at FormID
`0x830`; FormID `0x820` remains as an inactive compatibility tombstone so a
save made with an earlier OpenMCM build cannot restore the provider onto
SkyUI's historical quest identity. The manager repairs stale registry indices,
publishes list refreshes without unlocking an unrelated active request, and
preserves the selected MCM while duplicate ready events are deduplicated.

The Journal lifecycle, mod/page mouse selection, option buffering, cursor
restoration, custom-content placement, footer prompts, and slider, menu, color,
input, keymap, and message dialogs were aligned with the SkyUI 6 MCM contract and
authored stage measurements. Fully exit Skyrim before replacing 0.2.7 so the
new plugin, PEX files, and SWF are loaded. A new game or quest reset is not
required.

XPMSE intentionally creates no Styles options when its own requirements check
fails. Its installed script checks the XPMSE skeleton/library, SKEE or
NiOverride, `FNIS.esp`, and the FNIS version. The XPMSE Info page is the useful
control: if Info renders but Styles is blank, the host page pipeline is working
and XPMSE is reporting a provider prerequisite problem rather than a failed MCM
selection.

## Build

The build requires Windows PowerShell 5.1 or PowerShell 7, Visual Studio 2022
or newer (or Build Tools) with **Desktop development with C++** and a Windows
SDK, 64-bit Java 8 or newer on `PATH`, Python 3.10 or newer, internet access on
its first run, and a legal local Skyrim installation. It locates the installed
x64 C++ toolchain using Visual Studio Installer, compiles and tests the optional
native runtime with the static C++ runtime, and downloads checksum-pinned tools
for the MCM build. It
compiles the Papyrus layer, generates the minimal compatibility plugin,
extracts the vanilla Journal menu from the local game BSA, applies the host
hooks, embeds the independent ActionScript classes, round-trips the result
through a decompiler, and runs the contract tests.

```powershell
.\build.ps1 -SkyrimPath "E:\SteamLibrary\steamapps\common\Skyrim Special Edition"
```

If Skyrim is in a discoverable Steam library, `-SkyrimPath` may be omitted.
`SKYRIM_SE_PATH` is also accepted. The result is
`dist/OpenMCM-1.0.1-rc.4.zip` by default. Native compiler outputs, test executable,
symbols, and build logs remain in `build/native`; only the DLL and configuration
are included under `Data/SKSE/Plugins` in the package.

Pass `-SkipTests` only when Python is intentionally unavailable. The built-in
compiler, native regression tests, export checks, and SWF checks still run,
but the Python compatibility contract and unit suite do not.

The repository does not contain Bethesda's vanilla `quest_journal.swf`; it is
derived during the build from the user's installed game. Downloaded tools live
under the ignored `.tools` directory and are not placed in the release package.
Every other packaged file is covered by `OpenMCM_SHA256SUMS.txt`; the final zip
is reopened by the release checker to reject missing, added, or changed files.

## Verify

```powershell
python -B tools/check_mcm_contract.py . --profile source
python -B -m unittest discover -s tests -p "test_*.py" -v
python -B tools/check_mcm_contract.py dist/OpenMCM-1.0.1-rc.4.zip --profile release
```

The checks validate the source contract and inspect compiled PEX, SWF, native
DLL, and plugin identities in a release. The native build also runs executable
regression tests for the guarded patch logic. They are not a substitute for
an in-game smoke test of character creation, focus, timing, save/load, and
SKSE event delivery.

## Layout

- `src/papyrus` contains the compatible `SKI_*` implementation.
- `src/actionscript` contains the code-drawn AVM1 panel and its ABI manifest.
- `src/plugin` contains the text-serialized minimal `SkyUI_SE.esp`.
- `src/native` contains the optional runtime-specific precache fix and its INI.
- `scripts` contains the reproducible Journal patch and package build.
- `tests/native` contains executable native patch regression tests.
- `tools/check_mcm_contract.py` is the source/release compatibility checker.
- `examples/OpenMCMExample.psc` is a conventional SkyUI-style menu example.

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for upstream references,
tooling licenses, and Bethesda asset notes.
