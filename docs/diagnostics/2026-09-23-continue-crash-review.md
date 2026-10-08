# Continue/save-load crash review — 2026-09-23

Publication of OpenMCM 2.0.0 remains on hold. The owner clarified that the
reported failure occurs after selecting **Continue**, not while opening or
interacting with an MCM. No corrective runtime change has been justified yet.

## Earlier crash reports

Read all 22 available Trainwreck reports in the game's SKSE/Crashlogs directory
(September 6–22). Two reports, September 17 20:23:31 and September 20 23:40:01,
are empty. There is no September 23 crash report in that directory.

| Reports | Observed signature | What it establishes |
| --- | --- | --- |
| September 6 (three short reports) | SkyrimSE+0AA2776, no stack | Insufficient detail to associate with the current report; predates the example. |
| September 8–16 (repeated +0199FC3 reports) | Same scene-removal/actor-teardown stack as the previously investigated exit crash | A separate known shutdown signature; see the September 8 exit-crash investigation. |
| September 15 23:10:17 | SkyrimSE+02E3DCC; TESObjectREFR-related raw stack | Different signature; no established connection to the example. |
| September 18 08:58:44 | EngineFixes render-pass cache/shadow-map code | Rendering-path failure before the example was built; root cause is not established merely by the module name. |
| September 20 19:59:03 and 19:59:47 | po3_LightPlacer.dll+005F38D, AddEventSink → LightManager::OnDataLoad → MessageHandler | Two matching startup/data-load failures. Light Placer's DLL is no longer deployed in the inspected installation. |
| September 21 10:13:54 | ntdll/_Mtx_unlock through EngineFixes shadow-map render-pass cleanup | A rendering/cleanup failure, not an identified Papyrus or MCM callback failure. |
| September 22 17:06:53 | Null instruction pointer; no probable call stack; rendering objects in raw stack | Insufficient evidence to assign a causal mod or associate it with the reported Continue action. |

The dates are the report filenames. Do not infer the owner's exact triggering
action from a timestamp or assign blame from a DLL merely appearing in a module
inventory. None of the post-example nonempty reports names Field Guide.

## Installed build and save consistency

- Vortex's current deployment identifies `OpenMCM-1.2.0-alpha.5-FOMOD` as the
  source of the host scripts, Journal and standalone compatibility ESP.
- Deployed OpenMCM_ConfigBase, OpenMCM_ConfigMenu, SKI_ConfigBase,
  SKI_ConfigManager PEX files and quest_journal.swf byte-match alpha.5.
- Field Guide's ESP and PEX are absent from the deployed Data tree and the
  active plugin list. This does not establish whether it was installed and
  subsequently removed during an earlier test.
- The most recent Save29 and two autosaves contain 72 full and 94 light
  plugins. Their membership matches the current enabled installation; saved
  plugin files and active plugins' declared masters are present. None of these
  saves lists Field Guide.
- Those saves consistently identify SkyUI_SE.esp as a light plugin, matching
  the deployed 1,046-byte ESL-flagged standalone compatibility plugin. No
  standalone-versus-real-SkyUI identity mismatch was found in this comparison.
- An extended scan of all 47 available saves (September 5–23) found no Field
  Guide entry and no full-versus-light SkyUI identity switch. This does not
  exclude installing the example and crashing before a new save was written.
- The current OpenMCMRuntime log says the optional precache patch was **skipped**
  because RaceMenu/Engine Fixes is present. It is not evidence about whether
  that patch ran during every earlier crash.

The read-only save-table check is `tools/audit_save_plugins.py`. It does not
validate all saved Papyrus state or rule out other forms of save corruption.

## Code review and next evidence

Checked the shipped example's quest, alias, VMAD, SEQ and PEX inheritance plus
the host's reload/API toggle paths. No malformed example plugin or direct
reload recursion was identified. The example's delayed refresh and actor-value
reads are not automatically invoked by its reload callback. These structural
checks are not an in-game reproduction or proof of absence of an indirect bug.

Need the approximate date/time of the Continue failure and whether the example
was removed afterward, to identify the relevant session. If its report is one
of the empty files, a controlled reproduction with a useful trace will be
needed before attributing or patching the failure. Do not clean saves, change
unrelated mods, or publish an alleged crash fix on this evidence.

No game files, saves, Vortex deployment, load order or remote Nexus content were
changed during this investigation. No crash reports or save data were uploaded.

## Owner follow-up

On 23 September 2026 the owner reported that it works and asked to finish the
upload. Release preparation resumed. This report does not establish the cause
of the earlier crash or imply that an OpenMCM crash fix was made.
