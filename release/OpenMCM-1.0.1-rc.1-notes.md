# OpenMCM 1.0.1-rc.1 — local performance candidate

Status, 2026-09-06: the user reported a crash and a whole-game freeze that clears
after pressing Ctrl with this candidate installed (deployed PEX/SWF hashes
verified). No crash stack was available. It is not a verified stall fix.

This candidate addresses confirmed excess work in OpenMCM. It is not yet an
in-game-verified fix for the reported stalls when changing character sex or
moving character-creation sliders. The published 1.0.0 package is unchanged.

## Changes

- Replace scripted registry searches with built-in array lookups, including
  duplicate detection, removal, and circular free-slot allocation.
- Preserve exact provider identity, sparse slot IDs, saved-registry repair,
  duplicate-callback suppression, and the original SkyUI registration ABI.
- Do not publish mod names or initialize display storage for a closed Journal.
- Remove redundant heartbeat publications, delayed Journal-opening
  publications, and the extra readiness broadcast on Journal close.
- Keep one initial Journal publication plus the existing panel request/ack
  handshake so dynamic panel attachment and older saves still receive names.

No character-creation interface, native DLL, game setting, third-party mod,
provider requirement, plugin identity, or saved-field layout is changed.

## In-game verification still required

Fully exit Skyrim, install this candidate in place of the previous OpenMCM
version through the mod manager, and deploy. Keep the previous package and a
save backup. Do not enable SkyUI alongside OpenMCM. No console reset is part
of this test.

1. In a disposable new game, change sex and move the same sliders that stalled.
   Record whether the freeze remains and which control triggers it.
2. Open Journal normally, then MCM: check OpenMCM, XPMSE, and their pages.
3. Close/reopen Journal and MCM; verify selection, dialogs, and the mod list.
4. Load an existing save; verify registered menus return without repeated
   registration notifications. A newly initialized provider blocked while
   Journal is open retries on the normal SkyUI readiness heartbeat.

Do not advertise the character-creation freeze as fixed until step 1 is
verified in game. A remaining stall requires runtime isolation; the source
audit found no OpenMCM handler for character-creation sex or slider changes.
