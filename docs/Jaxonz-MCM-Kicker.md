# Jaxonz MCM Kicker compatibility add-on

Available in the full OpenMCM **2.1.0** FOMOD. This is an optional patch
for [Jaxonz MCM Kicker SE 1.1SE](https://www.nexusmods.com/skyrimspecialedition/mods/36801),
not a bundled replacement for the original mod. In-game testing is still needed.

## Install

1. Install the original **Jaxonz MCM Kicker SE - ESPFE** and enable
   `JaxonzMCMKicker.esp`. Keep its original BSA installed.
2. Install the full OpenMCM FOMOD in the correct standalone or With SkyUI mode.
3. Select the Jaxonz MCM Kicker compatibility option. It is recommended when
   the installer sees `JaxonzMCMKicker.esp`; otherwise omission is recommended.
   Review this choice if your manager cannot see undeployed files.
4. Let OpenMCM's loose `JaxonzMCMKicker.pex` and
   `JaxonzSKSEVersionCheckScript.pex` win conflicts with the original scripts.
5. Launch via matching SKSE. Load the game and allow the delayed refresh to
   finish outside menus before inspecting MCM registration.

The add-on installs two PEX files and their PSC sources. It adds no plugin,
DLL or manager quest. It requires the matching OpenMCM manager from this full
installer; do not install these scripts alone over rc.1, 2.0.0 or unmodified
SkyUI. The completion method is independent of the experimental API switch,
which can remain off. Without the original quest/plugin it does nothing.
Never install both original Kicker variants, or duplicate standalone Kicker
patches. Do not mix OpenMCM's two host modes on one profile.

## What changes

The upstream startup checker searches for `SKI_MainInstance`, which belongs to
full SkyUI. Standalone OpenMCM instead supplies the compatible MCM manager.
The adapted checker accepts that manager only on Kicker's own quest instance
(`JaxonzMCMKicker.esp`, local form `0xD62`); it does not pretend other Jaxonz
mods have full SkyUI. Normal SKSE checking and real SkyUI detection remain.

The delayed kick resolves the same `SKI_ConfigManagerInstance`, but calls
`OpenMCM_TryForceReset()` and waits for its Boolean result. Unlike a successful
`SetStage(1)` request, `True` means the manager has validated storage, cleared
the registry and dispatched its reset/readiness signals. It does **not** mean
every provider has finished re-registering. The legacy void `ForceReset()`
entry point remains available to existing callers.

The adapter waits until Journal and character creation close. BUSY, registry
lock and invalid-storage rejections return `False`, retain the pending kick,
and use bounded retries (six failed attempts, with 2/4/8/8/8-second delays).
Exhaustion ends the cycle with a trace, never a success notification. Manager
readiness events cannot bypass retry deadlines or acknowledge a reset. A new
load rearms the cycle; late results from a previous cycle are ignored.
The adapter does not directly edit registry arrays, force manager states,
reset provider quests, or modify provider settings.

A registry reset makes providers register again. A provider can itself react
to re-registration by changing settings; Kicker's original page specifically
warns about Equipment HUD. This add-on cannot repair a broken provider,
missing dependencies, or exceed the host's 128-menu limit. It is optional,
not a general requirement for OpenMCM's normal registration.

## Test before release

Use a backed-up test save/profile. Test both standalone and real-SkyUI host
modes, an existing save and a new game, opening Journal before the delayed
kick, and leaving character creation. Verify that the menu list recovers,
provider settings remain as expected, no repeating kick occurs, and a later
save/load causes one new refresh. Exercise a busy manager followed by recovery,
and sustained rejection: neither should show success before a completed reset.
Also test with the add-on omitted.
Static tests and compilation do not establish these in-game results.

## Reference and permissions

Reviewed the installed 1.1SE ESPFE quest and the sources shipped in its BSA.
The original quest and BSA are **not redistributed**. The adapted scripts
retain their original author attribution and follow the permissions published
on the [original SE page](https://www.nexusmods.com/skyrimspecialedition/mods/36801?tab=description),
checked 1 October 2026: modification and asset use with credit are allowed;
sale of the assets is not allowed. These adapted scripts are not relicensed
under OpenMCM's GPL notice; their upstream permissions remain unchanged.

Credits: **Jaxonz** (original), **insaneplumber** (SE port), **Oisaco1**
(original concept), and **NexusModsCaretaker** (SE upload/permissions).

Build from a prepared checkout with `scripts/Build-KickerCompatibility.ps1`;
the main FOMOD build invokes it automatically. Compile-only native signatures
are provided in `vendor/papyrus-stubs` and are not installed.
