# API 1 runtime preference / alpha.4

## Delivered

Full replacement FOMOD: `dist/OpenMCM-1.2.0-alpha.4-FOMOD.zip`

56 files, 1,203,363 bytes. SHA256:
`CBD58127926E85B16C1A5EE7C8C56E15BEBCFCCA291746AE4D61F19AA92492F9`

OpenMCM's Status page now has an API 1 version row and an **Enable OpenMCM API**
checkbox in Runtime, with explanatory highlight text. It defaults off and is
saved on the existing manager quest. Save after changing the preference to
retain it on reload. No new plugin, dependency or native registration is added.

Both installation modes resolve the same SkyUI manager form at local 0x802.
The new saved Bool is appended, not substituted for existing ABI fields.
The setting is not reset by registry repair or game reload. Publication through
the existing mod-list handshake restores the preference after movie recreation,
including when initial OnMenuOpen races dynamic panel attachment.

The setting enables automatic help and optional live text/status operations.
Off still permits standard controls, numeric/ST callbacks, named construction/
bindings, synchronous legacy value setters and explicit highlight help. Public
page tokens return zero when off; internal guarded help scope remains separate.
Preference changes invalidate queued work; repeated synchronization with the
same value is harmless and re-enabling cannot resurrect stale tokens.

`OpenMCM.IsAPIEnabled()` exposes the saved choice independently of whether
the Journal is open. `GetAPIVersion()`/`HasCapability()` describe the installed
SDK; `GetHostAPIVersion()` reports zero when the movie is disabled/unavailable.
The guide documents fallback behavior and the SDK example disables its
extension-only actions with an instruction to enable the feature first.

## Verification

- Successful full build: `build/api-toggle-alpha4-final-build.log`.
- Papyrus scripts and both examples compiled; source legacy ABI 354 checks,
  staged standalone ABI 312, SDK 63, coexistence payload 686.
- 383 discovered Python tests: 382 pass, one existing opt-in skip. Source
  contracts and explicitly labelled lifecycle models do not execute Papyrus.
- Compiled AVM1 fixture: 48 assertions pass, including default off, opt-in,
  live-operation rejection, explicit legacy help while off, idempotent sync,
  off/on stale-token rejection, recreation, navigation and native text colours.
  Evidence: `build/diagnostics/avm1-mouse/openmcm-api-toggle-results.json`.
- 82 native patch tests pass. Native behavior is unchanged; version metadata
  is alpha.4. The API preference does not require or configure this DLL.
- 2,553 final ZIP/selected-install checks pass across all four combinations.
- Both XML files pass the Nexus preprocessing/.NET regression. The final
  ModuleConfig also passes the actual installed Vortex `XmlScriptType.Validate`
  method and its embedded official 5.0 schema, without installing anything.
- Both modes' final script sources and packaged API guide match the workspace.

Production Journal SWF SHA256:
`D244F8F7678FBE8FE618BAD0F9D8875B8EA8755BB641D329356C619AB80586D0`

The first integrated build caught an unnecessary status-provider migration
version bump. That was removed: the provider's pages rebuild on every open and
no provider migration is required. The final build retains its version 1 and
all coexistence tests pass without weakening their assertions.

## Unresolved exit crash

See `2026-09-19-alpha3-exit-crash.md` for the supplied report's fingerprint and
shutdown/scene-lifetime evidence. It is not explained or fixed by the API
preference. No speculative native crash patch or forced-termination workaround
was added. A controlled comparison and fresh per-run evidence remain necessary.

No in-game test of the new toggle was performed. No game files, saves, mod-manager
configuration or Nexus uploads were changed. Published 1.1.0 and alpha.3 ZIPs
retain their previous hashes.
