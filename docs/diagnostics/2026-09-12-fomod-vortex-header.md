# Vortex XML declaration failure / alpha.3 correction

## Root cause

The alpha.2 archive was well-formed UTF-8 XML and passed direct XML parsing and
schema validation. That was insufficient to reproduce the reported failure.

[Nexus XmlScriptType.StringStream](https://github.com/Nexus-Mods/fomod-installer/blob/5f0baede15f9e6d38065b05698a358975b1f5eb9/src/InstallScripting/XmlScript/XmlScriptType.cs#L94)
removes a double-quoted encoding attribute, then encodes the string as UTF-16BE
with a BOM. Python ElementTree's single-quoted `encoding='utf-8'` survives that
conversion. The reader subsequently treats UTF-16 bytes as UTF-8 and encounters
a NUL immediately after the declaration: line 1, position 39.

The generator now writes a canonical double-quoted UTF-8 declaration explicitly
for both ModuleConfig.xml and info.xml. Apostrophes, Unicode and XML escaping
inside the document body are preserved. The ZIP checker validates declaration
bytes before parsing, and the build always applies the new .NET preprocessing
regression to the final archive, including builds using `-SkipTests`.

## Validation against the actual installed Vortex library

In a separate PowerShell process, loaded these local libraries read-only:

`E:/Vortex/resources/app.asar.unpacked/node_modules/@nexusmods/fomod-installer-ipc/dist/FomodInstaller.Interface.dll`

`E:/Vortex/resources/app.asar.unpacked/node_modules/@nexusmods/fomod-installer-ipc/dist/XmlScript.dll`

Instantiated `FomodInstaller.Scripting.XmlScript.XmlScriptType` and called
`Validate(string)` with ModuleConfig.xml read directly from each ZIP:

- Alpha.2: exact `System.Xml.XmlException`, invalid hexadecimal 0x00 at 1:39.
- Alpha.3: PASS, including the library's schema validation.

Independent validation against the same library's embedded official
`FomodInstaller.Scripting.XmlScript.Schemas.XmlScript5.0.xsd` also passed.

XmlScript.dll SHA256:
`41ECE950D93E34FD357A849AA2193F61C0AD73CC4F2F4F3F9284ADA02AEB0867`

Embedded schema SHA256:
`A29DC8E83DA69F7C72A14784AAFFB488FE2CFBB632DEDB4714F9369DAEAF6F69`

This did not launch an installer, change its settings, or install any files.
The validation result is not a claim that all interactive installer steps or
the new API/coexistence behavior have been tested in a running game.

## Built artifact and regressions

`dist/OpenMCM-1.2.0-alpha.3-FOMOD.zip`: 56 files (plus 7 directory entries),
1,198,223 bytes. SHA256:

`E330EB83B30503973D460666949A2B6FD7808280646D782E42762EB8E2FA44CD`

- Full build: `build/fomod-alpha3-build.log`, successful Papyrus/example/native
  compilation, 82 native cases and 2,545 final archive/selected-install checks.
- Final expanded suite: `build/fomod-alpha3-tests.log`, 350 tests, 349 passed
  and one existing opt-in test skipped. Nine new tests cover serialization,
  final-archive rejection, and actual .NET preprocessing through PowerShell.
- Both LF and CRLF XML pass. Unicode and apostrophes survive serialization.
- The old header fails independently in either XML file at the exact position.
- Missing/duplicate XML entries and malformed XML are rejected.
- All four standalone/SkyUI and native-omitted/included projections pass.

The installed scripts' source payloads are unchanged from alpha.2. Recompiled
PEX files differ only in the eight-byte compilation timestamp. The production
Journal SWF is byte-identical:

`012A2E16029318367A085597DCFCCCF9EEE50C1F21CC61C3729C059FECDEB8B7`

The XML bodies are unchanged after normalizing the package version and line
endings; SkyUI detection and file-selection semantics are identical. The
optional native DLL was rebuilt with the alpha.3 version string; no native
behavior changed.

Published 1.1.0 and the failed alpha.2 archive were preserved unchanged. No
game files, saves, mod-manager configuration or Nexus uploads were modified.

## Repeatable local checks

```powershell
.\scripts\Test-FomodXml.ps1 -ArchivePath .\dist\OpenMCM-1.2.0-alpha.3-FOMOD.zip
python -B tools/check_fomod_package.py dist/OpenMCM-1.2.0-alpha.3-FOMOD.zip
python -B -m unittest discover -s tests -p "test_fomod*.py"
```

The .NET script does not require Vortex to be installed: it reproduces the
pinned consumer's encoding conversion and checks its own failure fixture first.
