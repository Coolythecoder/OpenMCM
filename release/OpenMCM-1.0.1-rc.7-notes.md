# OpenMCM 1.0.1-rc.7 — complete text/color update

This is one complete OpenMCM package. It includes the mouse fix confirmed
working in-game by the owner on 2026-09-12; no mouse add-on is required.

## Changes

- Corrected option HTML formatting to use SkyUI's parsed-format readback
  before restoring letter spacing and kerning. A fresh format object is no
  longer applied over the parsed fonts, sizes, alignment and colors.
- Preserved mixed HTML colors, explicit black, inline font/size/style changes,
  and clean defaults when a pooled field is reused.
- Added regression coverage and compiled-SWF verification for that ordering.
- Mouse handlers, registration, MCM APIs and native behavior are unchanged.

## Upgrade

1. Fully exit Skyrim.
2. Disable/remove old OpenMCM mouse update/diagnostic add-ons in your mod manager.
3. Replace the main OpenMCM installation with `OpenMCM-1.0.1-rc.7.zip`.
4. Preserve intentional local `OpenMCMRuntime.ini` settings; enable
   `SkyUI_SE.esp`, deploy, and launch through SKSE.

If you deliberately omitted the optional native DLL, keep it omitted.

No new game is required. Do not leave an older add-on winning the Journal or
status-script conflicts. Do not install alongside SkyUI or SkyUI Community.
Mods that require MCM Helper still require their matching MCM Helper version.

## Verification limits

The owner confirmed the mouse correction, not this new text correction.
The nearly black/missing-glyph screenshot is confined to HTML option text;
Skyrim Unbound's relevant labels contain no intentional color markup.
The helper now follows SkyUI's text handling, but automated text-format tests
and emulator rendering cannot establish Skyrim's localized font appearance.
Check Skyrim Unbound's Main page and an MCM with colored text in-game.

The existing optional native precache component is for Skyrim 1.7.104.0 only.
Its behavior/configuration defaults are not changed by this update. The
separate exit-to-desktop crash is not claimed fixed.
