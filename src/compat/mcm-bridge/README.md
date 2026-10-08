# OpenMCM MCM Bridge Add-on — basic compatibility preview

Copyright (C) 2026 TheElderLord1337 and OpenMCM contributors.
Original OpenMCM adapter code is free software under GPL-3.0-or-later.
It is distributed WITHOUT ANY WARRANTY, including the implied warranties of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See LICENSE.txt for the
complete licence and THIRD_PARTY_NOTICES.md for component boundaries.

This optional SDK-only add-on lets menus written against OpenMCM API 1 use
their ordinary controls under **MCM Bridge 1.1.0**. MCM Bridge is the sole host:
it owns registration, callbacks, dialogs and the FLICK/Menu Framework interface.
This does not make the two full MCM hosts run together.

Preview version: **0.1.0**. Source and package checks are not an in-game result.
This add-on has not been verified in Skyrim or uploaded to Nexus.

## Requirements and installation

1. Use a separate mod-manager test profile and back up your saves. Switching an
   existing OpenMCM-host save to Bridge is not a verified migration; begin with a
   new test game rather than uninstalling a manager from your only save.
2. Install the real SkyUI, matching SKSE and Address Library, a supported MCM
   Helper build, and either FLICK API 5+ or SKSE Menu Framework 3.18+ as required
   by [MCM Bridge](https://www.nexusmods.com/skyrimspecialedition/mods/193476).
   Install MCM Bridge 1.1.0 and let its original host scripts win conflicts.
3. Disable the **full OpenMCM host** in this profile, including its Journal,
   manager/base scripts, compatibility/companion plugins and optional native
   components. Do not use the standalone OpenMCM SkyUI_SE.esp shim instead of
   the real SkyUI plugin. Keep Bridge's other documented incompatible mods off.
4. Install this add-on as a separate mod. The only installed files are
   `Scripts/OpenMCM.pex`, `Scripts/OpenMCM_ConfigBase.pex` and their two matching
   `Source/Scripts/*.psc` files. It provides no ESP, DLL, SWF or SKI_* replacement.
   Do not install the nested source ZIP as a mod.
5. Enable the OpenMCM-authored MCM providers you want to use. Restart Skyrim.
   Their existing callbacks and settings remain owned by those mods.

Use your mod manager's conflict view to confirm that MCM Bridge still supplies
its SKI_* and MCMBridgeNative scripts, and this add-on supplies only the two
OpenMCM SDK scripts. Installing this over an active full OpenMCM host is not a
supported shortcut. Do not manually overwrite files in the game folder.

## Supported and deliberately unavailable

- Supported: named headers/text/toggles/sliders/menus/colours/keymaps/inputs,
  `BindOption`, state-option binding, and `GetOptionID`.
- Standard callbacks, ordinary typed value setters, dialogs, explicit
  `SetInfoText`, resets and sidebar page navigation are handled by Bridge.
- Unavailable: automatic bound help, guarded asynchronous/live updates,
  page tokens, API-driven page navigation and atomic conditional groups.
  These return false/zero or safely do nothing; they do not claim completion.

`OpenMCM.GetAPIVersion()` remains 1 for signature compatibility.
`HasCapability("named_options")` is true; all other capability names are false.
`IsAPIEnabled()` is false and `GetHostAPIVersion()` is zero. There is no
OpenMCM Runtime enable switch in this setup. This is intentional, not a missing
installation step. Menus must have normal-control fallbacks for advanced calls.

Providers with a hard dependency on OpenMCM.esp, OpenMCM's manager internals or
its Journal movie need separate changes; this add-on does not satisfy those
dependencies. Not every OpenMCM-authored menu can be guaranteed compatible.
Custom SWF/DDS content remains subject to Bridge's own limitations. VR is not
supported by the audited Bridge release.

One construction limit is rejected explicitly: rewinding a page cursor and
replacing a state-based row with an ordinary row. Bridge 1.1.0 retains the old
state callback in that case. The adapter rejects the addition before changing
the row, rather than letting clicks call the wrong handler. Rebuild the page
with the intended row instead. Ordinary and state-based rows can otherwise be
constructed and named normally, within the host's 128-option page buffers.

## Field Guide and testing

The separate OpenMCM Field Guide 1.0.0 example can be used as a test provider;
install its standalone package, not the full OpenMCM host FOMOD. The example's
normal controls already contain fallback paths. Its API-only navigation and
delayed/live demonstrations remain disabled. Any example text asking you to
enable OpenMCM's Runtime switch applies to the original host, not this add-on.

Before a public compatibility claim, test both FLICK and Menu Framework:

- Registration, opening/closing, reopening and sidebar page changes.
- Sliders outside 0–1, menu/input/colour dialogs, toggles and key mappings.
- Named ordinary and state-based controls, including provider help callbacks.
- Field Guide settings, saving/loading, and unavailable API demonstrations.
- Normal game interfaces and exiting to desktop, with MCMBridge.log/Papyrus.log
  checked for missing methods or overwritten host scripts.

Record the exact Skyrim, SKSE, SkyUI, Bridge, MCM Helper and frontend versions
with any result. Compilation alone does not verify those runtime combinations.

## Source and reproducible build

Complete adapter source, build/validation scripts, tests and pinned compile-time
imports are in `source/OpenMCM-MCM-Bridge-Addon-0.1.0-Source.zip`. Extract it to a
new directory. The upstream source pin and checksums are in
`src/compat/mcm-bridge/upstream.json`. No upstream compiled host files are bundled.

Requirements: Windows PowerShell, Python 3.11+, and Caprica 0.3.0 supplied by the
builder. From the extracted source root:

```powershell
.\scripts\Build-MCMBridgeAddon.ps1 -Caprica 'C:\Tools\Caprica\Caprica.exe'
python -B tools/check_mcm_bridge_addon.py dist/OpenMCM-MCM-Bridge-Addon-0.1.0.zip
python -B -m unittest discover -s tests -p 'test_bridge_*.py'
```

The builder uses bundled `upstream/mcm-bridge` imports or the main checkout's
`.tools/mcm-bridge-reference`, checks their pinned bytes and refuses existing
output archives. It does not download tools, deploy into the game or modify
OpenMCM 2.1. The two original API source files under `src/papyrus` are ABI
references for tests, not files to install or compile into this add-on.
