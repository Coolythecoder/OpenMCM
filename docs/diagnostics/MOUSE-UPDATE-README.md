# OpenMCM mouse update — rc.5 candidate

This two-file update is for the existing OpenMCM rc.4 installation. It
replaces the temporary Mouse Diagnostics add-on; keep the main OpenMCM mod
and its plugin enabled. No new game is required.

## Install

1. Fully exit Skyrim.
2. Disable the temporary `OpenMCM-Mouse-Diagnostics-1` add-on in Vortex.
3. Install `OpenMCM-Mouse-Update-rc5.zip` as an add-on. Let it win the
   `Interface/quest_journal.swf` and `Scripts/OpenMCM_ConfigMenu.pex`
   conflicts against the main OpenMCM mod, then deploy.
4. Launch through SKSE and load an existing save. Test mouse selection of
   MCM names, pages and settings. Close MCM and check that ordinary System,
   Settings and other Journal controls work again. Reopen MCM and repeat.

The optional **OpenMCM > Status > Mouse input diagnostics** toggle remains
available. If a particular name still cannot be clicked, enable it with the
keyboard, return to the MCM list without closing the Journal, click that
name and take a screenshot **with the pointer still on the name**. Include
the diagnostic box. Do not start another new game to perform this test.

## Change and evidence limits

The in-game capture proved a faded vanilla Journal Creations-list entry was
still pickable through blank MCM content. Putting MCM at a higher drawing
depth does not prevent AVM1 picking through noninteractive artwork.

While MCM is active, this update makes the vanilla Journal fader invisible
and disables its hit testing. It restores the exact previous flags before
returning focus to the Journal, and also cleans up on panel unload.
Repeated opens do not overwrite the saved state.

This fixes that confirmed isolation defect. It is not a claim that every
reported MCM-row failure is resolved: the supplied captures were not over
an MCM name, and they recorded one earlier row press. The candidate needs
the in-game test above.

## Scope and rollback

The archive contains two game files, this readme and the license. It contains
no DLL, INI, ESP, registration-manager change or global input hook. The
native precache component and its settings remain unchanged. The separate
exit-to-desktop crash is not claimed fixed.

To roll back, disable this add-on and redeploy; optionally re-enable the
previous diagnostic add-on. Do not remove the main OpenMCM mod. There is
no need to save the game during the mouse test.
