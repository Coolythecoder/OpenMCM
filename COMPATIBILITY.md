# OpenMCM compatibility — recorded test results

**2.0 release note:** the list below records the owner's verified **standalone
1.1** setup. It is retained as historical test evidence, not a claim that all
2.0 features or SkyUI coexistence have been tested in-game. The 2.0 FOMOD can install
With SkyUI mode while keeping OpenMCM as host; its new compatibility target
is SkyUI Community 6 (installed 6.8 / source audit 6.11).

On **23 September 2026**, the owner reported their current setup working and
approved publication. The exact optional-component and runtime matrix was not
specified; this does not extend the detailed 1.1 results to every 2.0 feature.

On **12 September 2026**, the project owner confirmed that **every MCM in
their current mod list was tested and working**, including the corrected mouse
input, text, and colours. The seven third-party providers below were identified
from the enabled plugins, deployed files, and compiled MCM scripts in that list.
These are **owner-reported in-game compatible** with the interface carried
forward unchanged from 1.0.1-rc.8 into OpenMCM 1.1.0.

| Mod | Installed version | MCM name | Status |
| --- | --- | --- | --- |
| Skyrim Unbound Reborn | 3.0.17 | Skyrim Unbound | Compatible — owner tested |
| Stats Editor MCM Menu | 1.0 | * Stats Editor MCM Menu | Compatible — owner tested |
| Atlas Map Markers | 3.0.4 | Atlas Map Markers | Compatible — owner tested |
| LOD Unloading Bug Fix | 0.2 | LOD Reload Bug Fix | Compatible — owner tested |
| Nether's Follower Framework | 2.8.6b | NFF | Compatible — owner tested |
| The New Gentleman | 4.2.6 | T.N.G. | Compatible — owner tested |
| XP32 Maximum Skeleton Special Extended | 5.06 | XPMSE | Compatible — owner tested |

OpenMCM's built-in Status menu was also present in the reported working setup.
**MCM Helper 1.6.3** is the installed supporting framework, not an eighth
third-party MCM. Install MCM Helper separately whenever a mod requires it.

## Scope

- These results cover the listed installed versions in the owner's setup;
  they are not an independent test of every setting or a guarantee for all
  game runtimes, controller inputs, combinations, or future mod versions.
- The local game executable is Skyrim **1.7.104.0**. The in-game report is the
  evidence of successful use; filesystem inventory alone is not a runtime test.
- Each mod retains its own dependencies. OpenMCM supplies the MCM host, not
  skeletons, animation frameworks, native plugins, or SkyUI's non-MCM features.
- MCM API v4, classic/state-based options, dialogs, and custom content are
  implemented. Unlisted MCMs may work through those APIs but are not added to
  this tested list without evidence.
- SkyUI must not be enabled with the **standalone** mode. The experimental
  **With SkyUI** mode preserves the real SkyUI plugin and its non-MCM features;
  use that FOMOD selection, not the old 1.1 standalone package, for coexistence.
- This list does not verify the optional native precache adjustment or resolve
  the separate exit-to-desktop crash report. See the README for those limits.
- OpenMCM's host version 2.1.0 is separate from the unchanged SkyUI API 4 and
  experimental OpenMCM API 1. The extension is off by default; existing MCMs do
  not require it to be enabled.
- Field Guide 1.0.0 is an optional OpenMCM-dependent teaching MCM in the main
  installer. Compilation and package checks are not an in-game compatibility
  result; it is not added to the owner-tested list above.
