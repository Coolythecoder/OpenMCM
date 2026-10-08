# Enabled MCM inventory for OpenMCM 1.1.0

Inspected 2026-09-12. Read-only inventory of the owner's current Skyrim Special Edition deployment. No game files, Vortex state, plugins, or archives were modified.

The owner explicitly confirmed **“Every MCM tested”** when asked whether all MCMs in this modlist had been tested. The release compatibility list may therefore describe the providers below as **owner-reported in-game compatible**, for the installed versions and modlist. This is not independent automated verification of their complete functionality, all optional features, other versions, or other modlists.

## Compatible third-party MCMs in the current modlist

| Mod | Installed version | MCM display name | Enabled plugin | Compiled provider |
| --- | --- | --- | --- | --- |
| Skyrim Unbound Reborn | 3.0.17 | Skyrim Unbound | `Skyrim Unbound.esp` | `SkyrimUnboundMCMScript` |
| Stats Editor MCM Menu | 1.0 | * Stats Editor MCM Menu | `Stats Editor MCM Menu.esp` | `TestMCMmenu` |
| Atlas Map Markers | 3.0.4 | Atlas Map Markers | `atlas map markers.esp` | `atlasmcmscript` |
| LOD Unloading Bug Fix | 0.2 | LOD Reload Bug Fix | `fixLOD.esp` | `fixLODMCMQuest` |
| Nether's Follower Framework | 2.8.6b | NFF | `nwsFollowerFramework.esp` | `nwsFollowerMCMScript` |
| The New Gentleman | 4.2.6 | T.N.G. | `TheNewGentleman.esp` | `TNG_MCM` |
| XP32 Maximum Skeleton Special Extended | 5.06 | XPMSE | `XPMSE.esp` | `XPMSEMCM` |

All seven provider scripts directly inherit `SKI_ConfigBase`, as checked in the compiled PEX object header. Atlas's provider is inside `atlas map markers.bsa`; the other six are deployed loose scripts. Mod versions above come from the winning Vortex deployment source directory names, not guessed script API version constants. The MCM names are also visible in the owner's September 8 screenshot; Skyrim Unbound's compiled script sets `ModName` to `" Skyrim Unbound"` with a leading sorting space, omitted in the display-name column.

OpenMCM's own **OpenMCM** configuration page also appeared in that screenshot, but it is not a third-party compatibility entry.

## Supporting framework

**MCM Helper 1.6.3** is the deployed version; `MCMHelper.esp` is enabled and its DLL and BSA are in the deployment manifest. Its archive contains `MCM_ConfigBase extends SKI_ConfigBase` and `SKI_ConfigMenu extends MCM_ConfigBase`, plus the `MCM` support script. The sole deployed `MCM/Config/*/config.json` belongs to `SkyUI_SE` and comes from MCM Helper itself. It must not be counted as another independent third-party MCM or as proof that every JSON-driven MCM has been tested. All seven identified external providers above use the original `SKI_ConfigBase` path.

Compatibility with a mod's MCM does not remove that mod's own non-MCM dependencies or prove optional native/animation features. In particular, do not infer that OpenMCM supplies XPMSE's skeleton/animation dependencies, another mod's SKSE plugin, or unrelated SkyUI inventory interfaces.

## Evidence and scope

- Deployment: `E:/SteamLibrary/steamapps/common/Skyrim Special Edition/Data/vortex.deployment.json`, deployment time `1789224695254`, staging root `E:/Vortex Mods/skyrimse`.
- Enabled plugin list: `C:/Users/josep/AppData/Local/Skyrim Special Edition/plugins.txt`. Each of the seven plugins in the table and `MCMHelper.esp` is prefixed with `*` (enabled), not merely installed in staging.
- Inspected all 354 loose PEX files in the deployed `Data/Scripts` directory and 13,243 PEX entries across 19 deployed, enabled-plugin-associated non-texture/non-audio BSA archives. Binary reads parsed PEX object names/parent types; archive reads handled both raw and framed LZ4 payloads without extracting or executing scripts. Loose provider files were matched back to the deployment manifest's winning source.
- No additional third-party `SKI_ConfigBase`/`MCM_ConfigBase` provider was identified. A `nwsFollower_PlayerAlias` reference to `SKI_ConfigBase` is not itself a provider; inheritance, not a string match alone, was used for identification.
- Installed-but-not-enabled staging directories and disabled plugins are not added to the compatibility list. Examples include older duplicate MCM Helper installations and the staged SkyUI package; their existence does not establish they are active.
- Runtime confirmation comes from the owner's explicit testing report and supplied screenshots. This agent did not launch Skyrim or execute an MCM.

### Current-deployment caveat

At this inventory snapshot the deployment manifest does not contain an OpenMCM source, the loose `Data/Scripts` and `Data/SKSE/Plugins` listings do not contain OpenMCM-named files, and `plugins.txt` does not list `SkyUI_SE.esp`. This does not negate the owner's runtime testing report, but means these filesystem checks should not be described as proof that the just-built OpenMCM 1.1.0 release is already installed or active. No deployment was performed for this inventory.

## Winning Vortex source directories

- `Skyrim Unbound Reborn 27962 3.0.17 2026-07-09T06-52Z uhRBKsrCN`
- `Stats Editor MCM Menu-70011-1-0-1655762736`
- `Atlas Map Markers-24104-3-0-4-1742779005`
- `LOD Unloading Bug Fix-61251-0-2-1728699151`
- `Nether's Follower Framework - Universal Installer-55653-2-8-6b-1712793520`
- `The New Gentleman 104215 4.2.6 2026-08-26T18-20Z IoFlhf4M8`
- `XP32 Maximum Skeleton Special Extended-1988-5-06-1707663131`
- Framework: `MCM Helper 53000 1.6.3 2026-08-26T18-07Z kATsMWjPO`
