# OpenMCM mouse update — rc.6 candidate

This interface update implements the independent list/input model derived
from the SkyUI Community 6.11 source audit. It replaces the temporary mouse
diagnostics/rc.5 add-on. Keep the main OpenMCM mod and its plugin enabled.

## Install and test

1. Fully exit Skyrim.
2. Disable any previous OpenMCM mouse diagnostics or mouse update add-on in
   Vortex. Do not disable the main OpenMCM mod.
3. Install `OpenMCM-Mouse-Update-rc6.zip` as an add-on. Let it win the
   `Interface/quest_journal.swf` and `Scripts/OpenMCM_ConfigMenu.pex`
   conflicts against the main OpenMCM mod, then deploy.
4. Launch through SKSE and load an existing save. No new game is required.
5. Test mouse selection of mod names, pages (including XPMSE Styles),
   settings, sliders, menu choices, colors and text-input dialogs. Check
   scrolling and keyboard navigation too. Close MCM, check ordinary Journal
   controls, and reopen MCM to repeat.

The optional **OpenMCM > Status > Mouse input diagnostics** toggle remains.
If a name fails to open, leave the pointer on that name and capture the
diagnostic box. The code change still needs confirmation in Skyrim's own
Scaleform runtime; source comparison and automated tests are not a substitute.

## Changes

- Independent persistent mod/page/options list controls, with pooled row
  clips and list-owned selection/scroll positions.
- Ordinary transparent row geometry instead of hidden replacement hit areas.
- Row hover -> list selection -> item-press event -> MCM API dispatch.
- Per-list input gates and stationary-pointer reselection after scrolling.
- Active-component focus; dialog focus is saved/restored, and underlying
  lists are disabled without adding a full-screen mouse-blocking button.
- The rejected rc.5 whole-Journal visibility/hit-testing workaround is removed.
- A failed key-remapping capture now restores list input instead of leaving
  the lists disabled.

This remains independent of SkyUI at runtime. No SkyUI components, SWFs or
visual assets are bundled. Existing registration and Papyrus APIs are kept.

## Verification limits

The final build passes 180 unit tests (one separate environment-dependent
test is skipped) and source/package compatibility checks. A 30-stage real
mouse-input test covers mod/page/options IDs, dialogs, scrolling, text entry
and reopening in the compiled Journal. That downstream test uses an explicitly
labelled pointer-reentry mode because the emulator still generates a rollout
when focus changes despite the host's Scaleform suppression flag. The ordinary
first-hover flow does not pass there. Skyrim first-hover behavior therefore
remains unverified; this is a test candidate, not a claim of universal success.

## Scope and rollback

The archive contains two game files, this readme and the license. It contains
no DLL, INI, ESP, registration-manager change or global input hook. The
separate shutdown crash is not claimed fixed.

To roll back, disable this add-on and redeploy the main OpenMCM installation.
Do not remove the main mod. No save is needed during this interface test.
