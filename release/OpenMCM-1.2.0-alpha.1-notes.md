# OpenMCM 1.2.0-alpha.1 — SkyUI coexistence preview

One complete FOMOD installer, no add-ons. OpenMCM remains the MCM host in
both modes. The published 1.1.0 archive is unchanged.

- Detects actual SkyUI using its plugin plus archive/loose-file markers and
  preselects Standalone or With SkyUI. Review the choice; manual override is
  available for undeployed installations or saved installer presets.
- With SkyUI mode preserves the real SkyUI plugin, full translations, inventory,
  favorites, widgets and settings infrastructure. OpenMCM supplies its MCM
  scripts and Journal plus a separate status plugin, not a second manager.
- Keeps the working mouse, text and colour interface from 1.1.
- Native precache component is optional within the installer and omitted by
  default. Include only for Skyrim 1.7.104.0; custom INI settings are not merged.

Keep real SkyUI installed and enable `SkyUI_SE.esp` and `OpenMCM.esp` for With
SkyUI mode. Let OpenMCM win Journal and MCM base/manager script conflicts.
Remove stale standalone OpenMCM overrides through your mod manager. MCM Helper
remains a separate requirement for mods using it.

Coexistence is a preview, audited against SkyUI Community 6.8/6.11, not yet
verified in-game. The Journal is OpenMCM's vanilla-derived replacement, so
SkyUI-specific Journal features are not preserved. Do not treat this as support
for every SkyUI version or third-party Journal replacer.

Test on a separate profile/new game or an existing real-SkyUI save, with backups.
Switching an old standalone OpenMCM save to full SkyUI is not a verified migration;
do not use save cleaning or uninstall/save/reinstall as a workaround.

Check MCM registration, SkyUI's own settings MCM, mouse/dialog/text behaviour,
inventory sorting/search, favorites, HUD widgets, and save/reload before release.
The seven owner-tested MCMs in COMPATIBILITY.md were verified in standalone 1.1,
not this new coexistence mode. The separate shutdown crash remains unresolved.
