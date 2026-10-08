# OpenMCM 1.0.1-rc.8 — explicit text defaults, complete package

The owner's rc.7 retest still showed nearly black/missing-glyph option text.
The confirmed rc.6 mouse fix remains unchanged.

## Changes

- Ordinary option text uses the same explicitly formatted plain-text path
  as the readable sidebar, instead of dynamic HTML defaults.
- Formatted/entity-containing text inherits explicit font, size, white color,
  paragraph alignment and baseline styles corresponding to SkyUI's authored
  option fields. Inner MCM color/font tags are preserved, not flattened.
- Translation occurs before generated markup so leading tokens still resolve.
- Clean defaults are retained when a field switches between plain and HTML.

The change is confined to text handling. No provider data, mouse handlers,
registration or native behavior was changed. This is a full mod, not an add-on.

## Installation

Fully exit Skyrim. Replace the main OpenMCM package with
`OpenMCM-1.0.1-rc.8.zip`, disable/remove old mouse diagnostic/update add-ons,
enable `SkyUI_SE.esp`, and deploy through the mod manager. Do not install
alongside SkyUI or SkyUI Community. Keep MCM Helper when another mod needs it.

Preserve any intentional `OpenMCMRuntime.ini` setting or omission of the
optional native DLL. That component is still for Skyrim 1.7.104.0 only; its
behavior is unchanged and it is not a claimed shutdown-crash fix.

No new game is required. Retest Skyrim Unbound Main and an MCM using colored
text. The screenshot's runtime failure cannot be reproduced by the emulator,
so this new correction still requires in-game confirmation.
