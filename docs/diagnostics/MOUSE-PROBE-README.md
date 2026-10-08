# OpenMCM temporary mouse diagnostic

This add-on requires the existing OpenMCM 1.0.1-rc.4 installation. It gathers
evidence about the reported keyboard-only MCM interface. **It is not a
claimed mouse fix or crash fix, and is not a Nexus release.**

## Install and capture

1. Fully exit Skyrim. Install `OpenMCM-Mouse-Diagnostics-1.zip` as a separate
   temporary mod in Vortex. Let it win conflicts against OpenMCM for
   `Interface/quest_journal.swf` and `Scripts/OpenMCM_ConfigMenu.pex`, then
   deploy. Leave the main OpenMCM mod and its plugin enabled.
2. Launch through SKSE and load an existing save. No new game is required.
   Open Mod Configuration using the keyboard.
3. Open **OpenMCM > Status**, highlight **Mouse input diagnostics**, and
   press Enter to enable it.
4. Use Back/Tab to return to the MCM names without closing the Journal.
   Move over a mod name, click once, and leave the pointer over that name.
5. Send a screenshot including the small black diagnostic box below the main
   panel and the mouse pointer. The movement/down/up counts, `over`/`press`
   counts, coordinates, and `top` target are the important evidence.

If the diagnostic box does not appear after enabling it, report that rather
than starting a new game. The probe turns off when the Journal unloads; it
does not save a permanent setting, write a log, or change input routing.

Remove/disable this temporary add-on and redeploy to restore the main mod's
two files. Do not delete the main OpenMCM installation. There is no need to
save the game during this capture.

## Scope

The add-on contains exactly two game files plus this readme and the license.
It contains no DLL, INI, ESP, input hook, or registration-manager change. The
native precache setting and its installed binary remain untouched.

The rc.4 standalone panel and complete Journal both respond to real browser
mouse clicks in a Ruffle AVM1 test, including exactly one mod-selection
event. That does not reproduce Skyrim's Scaleform implementation. This
probe observes Scaleform's actual picked target and row callbacks in-game,
instead of assuming that a callback test proves click delivery.

The exit-to-desktop report separately shows actor 3D cleanup after a scene
pointer is already null. It does not prove which mod caused that lifetime
failure. This add-on does not attempt a shutdown patch.
