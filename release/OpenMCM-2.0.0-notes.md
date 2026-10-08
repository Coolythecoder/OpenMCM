# OpenMCM 2.0.0

One full FOMOD installer with standalone and SkyUI coexistence modes. No
required add-on archives; optional components are choices within the installer.

## New since the published 1.1 release

- **Use OpenMCM with SkyUI installed.** SkyUI continues to provide inventory,
  favourites, widgets and other non-MCM features; OpenMCM remains the MCM host.
  The FOMOD recommends a mode using SkyUI's plugin plus BSA/loose-file markers.
  Review that choice before installing; a plugin filename alone does not prove
  that full SkyUI is present.
- **An integrated Redone-style MCM browser.** Name search, All/Favourites/Hidden
  tabs, reversible hiding, custom display names, priorities and per-tab sorting
  and scrolling. Save-local preferences need no DLL. This is not every Redone
  feature, and MCM Menu Redone must not be installed alongside OpenMCM.
- **Optional shared browser preferences.** A separate storage-only native
  component can share browser customisations between saves. It does not export
  the individual mods' settings or replace the MCM registry. GPL notices and
  corresponding native source are included.
- **Experimental OpenMCM API 1 for authors.** Named standard controls,
  automatic help, page-scoped live labels/text/help, guarded page navigation,
  conditional groups and stale-page tokens. Existing SkyUI API 4 and MCM Helper
  menus retain their normal workflows; they do not need rewriting.
- **A player-controlled API switch.** OpenMCM > Status > Runtime > Enable
  OpenMCM API is off by default and saved per savegame. It enables extension
  behavior only for menus whose authors use it; it does not convert old MCMs.
- **Optional Field Guide 1.0.0 teaching MCM.** A practical expedition planner
  demonstrates all standard controls, real carry-weight reads, checklists,
  a planning budget, colour/input controls, optional keyboard summary hotkey,
  live updates and safely scoped delayed work. Commented source, editable quest
  records and an author walkthrough are included. The sample is off by default,
  has no DLL requirement and does not change gameplay values.
- **Consolidated installer.** Retains the Vortex XML encoding correction and
  independent optional choices for shared browser storage, the existing
  runtime-specific chargen adjustment, and the Field Guide.

## Three different version numbers

OpenMCM's **package version is 2.0.0**. Its legacy SkyUI-compatible **MCM API
remains 4**, and its opt-in **extension API remains 1**. Field Guide retains its
own **1.0.0** example version. Do not use a package version as an API version or
increase a provider's save-migration version just to match the host.

## Installation and upgrade

Exit Skyrim and back up saves/profile settings. Replace the previous main
OpenMCM package with `OpenMCM-2.0.0-FOMOD.zip`; review every installer choice.
Remove obsolete OpenMCM mouse/diagnostic add-ons from the active profile. Do not
install MCM Menu Redone alongside this host.

- **Standalone:** keep the supplied `SkyUI_SE.esp` enabled; do not enable actual
  SkyUI. This branch supplies only the compatibility identity, not SkyUI's other
  interfaces.
- **With SkyUI:** retain actual SkyUI's ESP/BSA, enable `OpenMCM.esp` after it,
  and let OpenMCM win Journal, `SKI_ConfigBase` and `SKI_ConfigManager` conflicts.
  Keep MCM Helper and each provider mod's requirements where needed. The old
  standalone plugin or translation overrides must not mask the real SkyUI.
- **Field Guide:** if selected, enable `OpenMCM_FieldGuide.esp` after its
  `SkyUI_SE.esp` master. Do not also keep the separate Field Guide sample
  package active; they contain the same example.

Launch through matching SKSE. Switching standalone/coexistence modes on an
existing save is not a verified migration: use a separate profile/new game or
a save already using actual SkyUI. Do not uninstall/save/reinstall or clean a
save as a migration workaround.

## Requirements and honest limits

On 23 September 2026 the owner reported their current setup working and
approved publication. This is setup-specific confirmation, not exhaustive
verification of every optional component or supported runtime.

- The normal MCM host, save-local browser and author SDK do not require an
  OpenMCM native plugin. MCM Helper remains a separate dependency for mods
  requiring it.
- Shared browser storage requires matching SKSE, Address Library and Visual
  C++ 2022 x64 runtime. Its allowlisted game versions are 1.5.97, 1.6.640,
  1.6.1170 and 1.7.104; these are source/build-supported targets, not new
  in-game certifications. It does not support VR.
- The optional chargen component supports **1.7.104.0 only** and remains
  unverified as a fix for the reported freezes. Omit it on other game versions.
- The MCM registry stays at **128 menus** to preserve MCM Helper's existing
  array/index contract. Browser customisations are not mod-settings presets.
- The reported exit-to-desktop crash is **not claimed fixed** by this release.
- The owner verified the listed standalone 1.1 MCM setup in September 2026.
  Those historical results are preserved in `COMPATIBILITY.md`; they do not
  certify the new 2.0 browser, coexistence, extension API or Field Guide.
  Automated validation does not replace in-game/mod-manager regression tests.

Read `README.md`, `docs/OpenMCM-Browser.md`, `docs/OpenMCM-API.md` and
`examples/field-guide/README.md` for detailed controls, author contracts and
safe testing instructions.
