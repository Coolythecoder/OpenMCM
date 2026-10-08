# Standalone MCM compatibility contracts

These tests freeze the compatibility boundary that existing SkyUI 6 MCMs and
MCM Helper observe. They do not launch Skyrim and need no third-party Python
packages.

The contract covers:

- the exact `SKI_ConfigBase`, `SKI_ConfigManager`, and lifecycle Papyrus API;
- all `SKICP_*` event names and the Journal Menu bridge entry points;
- `_root.ConfigPanelFader.configPanel` and the two runtime SWF paths;
- the `SkyUI_SE.esp` compatibility identity;
- the manager quest at local FormID `0x00000802`, with EditorID
  `SKI_ConfigManagerInstance` and attached `SKI_ConfigManager` script;
- the private Papyrus fields that MCM Helper reads directly;
- standalone packaging: only official game masters are allowed;
- the light-plugin flag plus the start-enabled manager quest, stage fragment,
  forced player alias, and alias script wiring;
- safe, case-unique zip paths and an exact SHA-256 package inventory when the
  OpenMCM checksum manifest is present.

`test_visual_contract.py` separately freezes the clean-room SkyUI 6 visual
contract: pinned panel geometry and custom-SWF origin, vanilla font aliases,
focus and dialog states, ultrawide scaling, the 2-by-14 color palette, and the
absence of bundled or linked SkyUI visual assets. It also pins the mod-list
text bounds and full-row mouse press targets so names cannot cross the divider
and rollover cannot destroy a pending click.
`test_registration_handshake.py` protects the post-bootstrap list refresh that
prevents a registered menu from remaining stuck behind the waiting message.
`test_registry_recovery.py` protects save upgrades where a menu retains its
cached manager/slot while the manager's typed object registry is missing, and
also covers stale `BUSY` state recovery and name-cache reconstruction.
These tests also require native registry lookups, no list publication for a
closed Journal, and one initial Journal publication backed by the panel's
request/acknowledgment handshake. They do not measure game-thread stall times.
`test_text_input_ownership.py` uses Node.js, when available, to execute the small
AS2 ownership/teardown method bodies with a mocked SKSE shared counter. It
covers another menu holding input, repeated cleanup, callbacks opening another
input consumer, unavailable bridges, and two independent panel owners. Only
AS2 local type annotations are removed. This is not an in-game/Scaleform test.

`test_mouse_interaction.py` executes actual renderer and event-handler bodies
against a display-list mock. It protects live row/field/hit-area identity on
hover and click, original event IDs, modal gating, and slider track/button
identity during dragging. `test_journal_lifecycle.py` also checks that the
dynamic MCM remains above the fading Journal across repeated open/close.
`test_formatted_text.py` tests actual text-assignment bodies with a narrow
formatting model: HTML option colors/styles survive, plain text stays literal,
and reused fields retain authored defaults. These mocks are not Scaleform's
hit tester, HTML parser or font renderer; the full build also compiles the SWF.
The text model includes mixed-run null attributes and a deliberately
default-bearing constructor to catch unsafe partial-format writes. That
constructor scenario is a regression model, not a claimed Skyrim capture.
`avm1/AVM1TextFormatHost.as` separately exercises the actual embedded utility
and native TextField formatting in an instrumented copy of the final Journal.
For rc.8 the unit model also covers HTML document defaults differing from the
field's insertion format. Native cases cover entities, nested markup and
paragraph/newline semantics as well as formatting; they remain distinct from
the owner's in-game screenshot and cannot replace its verification.

The values are in
[`contracts/skyui6_mcm_contract.json`](contracts/skyui6_mcm_contract.json).
Its provenance section pins the upstream revisions used to derive the
contract: [SkyUI Community](https://github.com/doodlum/SkyUI-Community) and
[MCM Helper](https://github.com/Exit-9B/MCM-Helper).

## Run the unit tests

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Check a source checkout

```powershell
python tools/check_mcm_contract.py . --profile source
```

## Check an unpacked release or zip

The checker accepts a mod root containing `Data`, a directory representing the
contents of `Data`, or a zip containing either layout.

```powershell
python tools/check_mcm_contract.py build/staging --profile release
python tools/check_mcm_contract.py dist/OpenMCM-1.0.1-rc.4.zip --profile release
python tools/check_native_runtime.py dist/OpenMCM-1.0.1-rc.4.zip
```

Add `--json` for CI output. Add `--require-source` to a release check when the
SDK/source `.psc` files are intentionally shipped alongside the `.pex` files.

To exercise the opt-in integration unittest against a real target:

```powershell
$env:MCM_CONTRACT_TARGET = "build/staging"
$env:MCM_CONTRACT_PROFILE = "release"
python -m unittest tests.test_contract_checker.WorkspaceContractTest -v
```

Source checks verify exact parameter types/defaults. Release checks validate
the PEX symbol table, SWF bridge tokens, runtime paths, and TES4/QUST plugin
identity. In-game smoke testing remains necessary for timing, focus, save/load,
and SKSE event delivery behavior.

## Optional native precache component

`scripts/Build-NativeRuntime.ps1 -Version 1.0.1-rc.4` compiles the x64 DLL
and executes `native/test_precache_patch.cpp`. The same patch transaction is
tested with simulated executable memory: both signatures, every mismatched
byte, unsupported runtime/distribution, disabled settings, competing providers,
duplicate application, protection failure, cache flush failure, and rollback.
Only the two precache entry bytes may change; the selected-head loader remains
untouched. These tests do not patch or launch Skyrim.

`test_native_runtime_package.py` exercises the independent PE/INI artifact
checker. It follows real export-table indirection and validates AMD64 code/data
exports, SKSE metadata layout, exact runtime compatibility and package defaults.
It never loads the DLL. Neither test suite replaces an in-game test of SKSE
startup delivery, character creation, race/sex/hair changes and normal menus.
