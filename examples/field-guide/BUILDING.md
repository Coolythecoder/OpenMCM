# Building the Field Guide

This is an optional teaching mod, also offered inside the OpenMCM 2.1 FOMOD.
Its own payload installs only its ESP, startup SEQ, compiled script and editable Papyrus source. The
existing OpenMCM SDK, MCM host and player-load alias remain owned by OpenMCM (or
the selected SkyUI coexistence installation).

## Build from the OpenMCM source checkout

Use an OpenMCM 2.1.0 checkout (or compatible 1.2.0-alpha.5 API) and the build toolchain
prepared by its normal build. Requirements are Windows PowerShell, Python 3.11+,
Caprica 0.3.0 and Spriggit CLI 0.41.0 with Spriggit.Yaml.Skyrim 0.41.0. The script
uses the existing `.tools` copies and does not download or install tools.

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-FieldGuide.ps1
python -B .\tools\check_field_guide.py .\dist\OpenMCM-Field-Guide-1.0.0.zip
```

The builder compiles only `examples/field-guide/OpenMCM_FieldGuide.psc`, using
`src/papyrus` as the SDK import directory and `vendor/papyrus-stubs` for
compile-time declarations. Stubs and imported host scripts are never installed.
It builds the new quest from `examples/field-guide/plugin`, emits the local-800
SEQ, checks the real binary records and PEX, and writes a checksummed release ZIP.
Only `build/field-guide` and the named Field Guide archive are replaced; it never
changes the main host package or installed game/mod-manager files.

The main `build.ps1` workflow also integrates this sample into the host FOMOD
as an optional, off-by-default component. The host's package version is 2.1.0;
the example's own release version remains 1.0.0. The main archive keeps the
editable plugin records and this guide under `examples/field-guide/Source/Plugin`
and `examples/field-guide/Docs/BUILDING.md`. Its commented source is in the
optional payload at `components/field-guide/Data/Source/Scripts`. Extract the
bundled `source/OpenMCM-2.1.0-Source.zip` for a complete development checkout;
the outer archive uses the installer layout. The standalone sample archive
uses the layout described below.

`-ProjectRoot`, `-Python`, `-Caprica` and `-Spriggit` can override checkout/tool
locations. The script copy in the example archive's `Source/scripts` directory
is provided for inspection; use `-ProjectRoot` pointing at a complete OpenMCM
checkout. To reproduce from this archive's edits, copy the Papyrus file from
`Data/Source/Scripts` into the checkout's `examples/field-guide`, and the supplied
`Source/Plugin/OpenMCM_FieldGuide.esp` directory into `examples/field-guide/plugin`.
The included validator runs independently using the neighboring helper files:

```powershell
python -B .\Source\tools\check_field_guide.py .\OpenMCM-Field-Guide-1.0.0.zip
```

## Adapting it in Creation Kit

The readable script is `Data/Source/Scripts/OpenMCM_FieldGuide.psc`. Compile a
renamed copy against OpenMCM's current `OpenMCM_ConfigBase.psc`, its imports, and
your normal Skyrim/SKSE script sources. Do not distribute engine source stubs or
your own copy of the OpenMCM SDK runtime scripts with a consuming mod.

Create a new start-game-enabled quest in your own plugin, attach the renamed
script, and set its `ModName` and `Pages`. Give the quest one reference alias
forced to PlayerRef (`Skyrim.esm:000014`) and attach the existing
`SKI_PlayerLoadGameAlias` script to that alias. This lets the host re-register the
menu on save load; do not create a second MCM manager. Generate your plugin's SEQ
using the normal Creation Kit/xEdit process. The supplied YAML is an exact example
of this wiring and does not require Spriggit if you build the equivalent quest in
Creation Kit.

The sample ESP is ESL-flagged, has only one new quest (`000800`), and lists
`Skyrim.esm` then `SkyUI_SE.esp` as masters. OpenMCM's standalone mode provides that
second master; coexistence mode uses the original SkyUI plugin. This is not a
requirement to install full SkyUI in standalone mode. The new SDK still requires
OpenMCM; the sample is not intended to work with SkyUI alone.

The on-disk SEQ entry is `00 08 00 02` (`02000800`, little endian), because the
plugin has two masters. Do not copy this value unchanged into another plugin:
generate its own SEQ from its actual master order and local quest FormID.

## What the checks prove

The package validator checks the exact four-file Data payload, allowed
documentation/source files, checksums, ESP master order, quest and alias owner,
VMAD script/properties, startup SEQ, and the compiled PEX object/parent/API symbols.
Its rejection tests use deliberately broken binary fixtures. These are structural
checks, not a Papyrus VM emulator or an in-game compatibility certification.
Test your adapted menu with the API enabled and disabled, across page rebuilds
and save/reload, in the OpenMCM host modes you intend to support.
