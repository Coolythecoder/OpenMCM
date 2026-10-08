# OpenMCM 1.1

Package version: **1.1.0**. One complete replacement package; no add-ons required.

OpenMCM provides a standalone, SkyUI-style Mod Configuration Menu with SkyUI
MCM API v4 compatibility. It does not require SkyUI and does not replace
SkyUI's inventory, favorites, HUD, or other non-MCM features.

What's changed

- Improved mouse selection for MCMs, pages, settings, and dialogs using
  persistent lists and component-owned focus.
- Corrected option-text font and colour defaults while preserving formatting
  supplied by individual mods, including mixed colours and styles.
- Includes the registration, menu-state, and text-input ownership corrections
  developed since 1.0.

The project owner reports that every MCM in their current installed list
works, including mouse input and text/colours. See `COMPATIBILITY.md` for
tested mods and versions; MCM Helper 1.6.3 was installed. This is not a
guarantee for other mods, versions, runtimes, or untested controller behavior.

## Requirements and installation

SKSE is required. Install MCM Helper separately if a mod requires it, using a
version compatible with your game. Each MCM retains its own mod requirements.

1. Fully exit Skyrim and keep a save backup.
2. Replace the previous OpenMCM package with `OpenMCM-1.1.0.zip` through your
   mod manager. Disable old OpenMCM mouse/diagnostic add-ons so they cannot
   override this release.
3. Keep `SkyUI_SE.esp` enabled, deploy, and launch through SKSE.

The plugin name is intentional compatibility identity. **Do not enable SkyUI
or SkyUI Community alongside OpenMCM.** Upgrading from recent OpenMCM
builds requires no new game or quest reset; do not load and save with
OpenMCM temporarily absent.

## Optional native component

The included `OpenMCMRuntime.dll` retains the existing character-creation
precache adjustment for **Skyrim 1.7.104.0 only**. It is not required for MCM
and has automated verification only. Omit it on other runtimes; preserve any
intentional omission or custom `OpenMCMRuntime.ini` settings when upgrading.
The separately reported exit-to-desktop crash is **not claimed fixed**.
