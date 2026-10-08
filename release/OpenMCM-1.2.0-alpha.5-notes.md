# OpenMCM 1.2.0-alpha.5 — browser integration preview

One full FOMOD; no addon packages. Not a verified stable release.

- Integrated name search, All/Favourites/Hidden tabs, reversible hiding, custom
  display names, priorities and per-tab sorting/scroll preferences.
- Save-local browser preferences work without a native plugin. Optional shared
  preferences adapt MCM Menu Redone 2.3.0's original GPL native persistence code
  into a separate, persistence-only OpenMCMBrowser component.
- Added opt-in API 1 page-navigation and conditional-option-group helpers, with
  stale-page protection. These require mod-author use; normal SkyUI API 4 and
  MCM Helper interfaces remain available without enabling the extension.
- Retained real SkyUI coexistence/standalone choices and the Vortex-safe XML
  encoding checks. Shared storage and the older chargen patch are independent,
  optional choices inside the same installer.

The registry remains 128 menus to preserve MCM Helper's array/index ABI.
This is not the entire Redone registry/SWF implementation and does not import
its old profile. Browser profiles do not save mod settings. No exit-crash fix
is claimed. See docs/OpenMCM-Browser.md and docs/OpenMCM-API.md.

Replace the previous preview main package through your mod manager; do not
install MCM Menu Redone alongside it. Keep save/profile backups and review all
installer choices. New features need in-game testing before public release.
