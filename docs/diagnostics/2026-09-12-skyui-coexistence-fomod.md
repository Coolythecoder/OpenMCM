# OpenMCM 1.2.0-alpha.1 — SkyUI coexistence / FOMOD

The owner requested SkyUI coexistence with OpenMCM remaining the MCM host,
then requested one FOMOD with SkyUI autodetection. No game/mod-manager files
were modified and nothing was uploaded. Published OpenMCM 1.1.0 is unchanged.

## Ownership decision

SkyUI mode ships only the Journal, SKI_ConfigBase/Manager PEX and matching PSC,
the OpenMCM status provider PEX/PSC, OpenMCM.esp and its SEQ (nine files).
The optional native pair is a separate selection within the same installer.

Real SkyUI retains SkyUI_SE.esp/BSA, its settings/favorites/widget/main quests,
shared quest lifecycle and reload/reset scripts, settings MCM, non-MCM UI,
and complete translations. The old nine-key standalone language tables cannot
override its full dictionaries. Existing MCMCompatUtil fallback translations
cover OpenMCM's generic labels without adding another language-table override.

There is one manager, at SkyUI_SE.esp local 0x802, with OpenMCM's compatible
manager/base scripts. MCM Helper continues to use that identity. Leaving the
original manager with the dynamic OpenMCM panel would lose OpenMCM's refresh
sentinel/protocol and risk the old empty-menu failure.

New light plugin OpenMCM.esp has masters Skyrim.esm and SkyUI_SE.esp, one status
quest local 0x800 (on-disk 0x02000800), and no manager or SkyUI record overrides.
Its player reload alias uses SkyUI's existing compatible implementation.
The provider prefers the companion when installed, rejects malformed/stale
identities, otherwise retains standalone's 0x830; migration/API versions stay put.

Reference audit: installed SkyUI Community 6.8 (real ESP SHA256
`61EB77164ED3632344AC2CCAC4C8A4E69C62397999E7D8D558C162FD205616CF`)
and [6.11 source at the pinned commit](https://github.com/doodlum/SkyUI-Community/tree/b7a24a936647e815269e34f4899e4b09768eff29).
Its SKI_Main has no live Journal SWF version check; SettingsManager bridges
item menus, favorites targets FavoritesMenu and widgets target HUD. No error
suppression or version spoofing was added. SkyUI-specific Journal changes are
not preserved: OpenMCM supplies its own vanilla-derived Journal.

## Installer

One SelectExactlyOne host choice with complementary recommendations:

- SkyUI_SE.esp present (Active or Inactive), AND either SkyUI_SE.bsa present
  OR both Scripts/SKI_Main.pex and Interface/skyui/config.txt present:
  recommend With SkyUI.
- Otherwise recommend Standalone. SkyUI_SE.esp alone cannot trigger coexistence.
- Users may override when deployment visibility or saved installer presets
  make detection incomplete. Detection does not verify the SkyUI version.
- A second SelectExactlyOne choice omits the optional native component by
  default; inclusion is explicitly restricted to Skyrim 1.7.104.0.
- Mode folders map directly to Data, never Data/Data. No required or conditional
  file installation can silently merge branches.

Generated XML was checked against the official Nexus installer's
[XmlScript5.0.xsd reference repository](https://github.com/Nexus-Mods/fomod-installer/tree/5f0baede15f9e6d38065b05698a358975b1f5eb9).
Its preselection code confirms Recommended is enabled for a fresh selection;
saved presets may override it. No live Vortex wizard session was run.

## Verification and artifact

- Full build: 263 Python tests, 262 passed, one opt-in workspace check skipped.
- 82 native regression cases and ABI assertions passed.
- 354 source / 312 standalone staged / 611 coexistence staged checks passed.
- Final archive: 2,201 checks including exact checksums, strict installer XML,
  four separately projected installs and their binary contracts.
- New tests cover 81 detection states, mode isolation, source/destination
  tampering, checksum corruption, wrong masters/SEQ/VMAD, native pairing, and
  wrong-mode payloads. Native leaks and plugin-content-based contract dispatch
  were caught and corrected during review.
- Standalone 25 files, or 27 with native. SkyUI 9 files, or 11 with native.
- Both Journal SWFs are byte-identical to working 1.1.0:
  `24B69DDC956ED3543607384BFC4F356CF05D5625A4853CFC75BEE33FBAD5B8A8`.
- MCM manager/base PSC and PEX are unchanged except compile timestamps.
  The status provider identity guard is the only Papyrus behavior change.
- The native INI and patch behavior are unchanged; version metadata is 1.2.0-alpha.1.

Archive: `dist/OpenMCM-1.2.0-alpha.1-FOMOD.zip`, 1,171,608 bytes.
SHA256: `63AD03F4D32935908215356415241BE9224C925C594622409F2909D4A8A5E656`.

## Remaining live validation

This is an experimental integration build, not a newly verified compatibility
release. Test the actual FOMOD choice in Vortex/MO2, deploy in a separate profile,
and test a new game or existing real-SkyUI save with backups. Check SkyUI's own
settings MCM, other MCMs, inventory/favorites/HUD, Journal closure, and save/reload.
Do not promise seamless conversion of standalone OpenMCM saves to real SkyUI:
their same-named plugins contain different persistent quests. No save cleaning
or uninstall/save/reinstall migration is prescribed. The optional native fix
and separate shutdown crash retain their existing verification limitations.
