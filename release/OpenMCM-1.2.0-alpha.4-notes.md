# OpenMCM 1.2.0-alpha.4 — Runtime API control

One full FOMOD replacement, no add-ons. Includes both standalone and SkyUI
coexistence modes with OpenMCM as the MCM host, and the Vortex XML fix.

## Runtime section

- Open **OpenMCM > Status > Runtime > Enable OpenMCM API** to enable the
  optional API 1 features. An adjacent row shows the installed API version;
  highlight the checkbox for explanatory text.
- Off by default, including saves upgraded from earlier previews. The setting
  is stored with the savegame; save after changing it to retain it on reload.
- Enabling allows automatic help and guarded live label/value/help/status
  updates in MCMs authored for OpenMCM. It does not upgrade existing MCM mods.
- Disabling leaves SkyUI API 4, MCM Helper, normal controls/callbacks, explicit
  highlight help, and named option construction/IDs available. Optional live
  updates are rejected and public page tokens return zero. Authors can query
  `OpenMCM.IsAPIEnabled()` and provide a normal synchronous fallback.
- The preference is reapplied when the Journal is recreated. Changing it
  invalidates outstanding optional work; re-enabling cannot revive stale tokens.
- No OpenMCMRuntime.dll dependency. The FOMOD's native component choice is
  separate and remains omitted by default, restricted to Skyrim 1.7.104.0.

## Exit-crash status

The supplied September 12 Trainwreck report reproduces the earlier
SkyrimSE+0199FC3 actor/scene teardown signature after quitting. It contains no
OpenMCM call frame but does show OpenMCMRuntime loaded; the stack alone cannot
prove or rule out a contributing mod. This update does not claim to fix that
crash and does not change native patch behavior. No speculative engine teardown
patch or forced process-exit workaround is included.

## Verification boundary

This remains an API/coexistence preview. Automated compilation, ABI, API toggle,
UI lifetime, installer and package tests do not replace testing in Skyrim.
Prior owner compatibility testing applies to standalone 1.1.0 only.
Building does not deploy files, edit saves/settings or upload a release.

See README.md for installation guidance and docs/OpenMCM-API.md for author use.
