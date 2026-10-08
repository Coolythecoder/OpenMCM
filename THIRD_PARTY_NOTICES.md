# Third-party notices

## OpenMCM distribution notice (3 October 2026)

Original OpenMCM code in this distribution is offered under GPL-3.0-or-later;
the full GPL version 3 text is in `LICENSE.txt` (also `LICENSE`), with the
copyright and warranty notice in `README.txt`. Earlier MIT grants and copyright
notices remain in `licenses/OpenMCM-previous-MIT.txt`. The full editable project,
build scripts, and pinned browser dependency sources are included under
`source/OpenMCM-<version>-Source.zip`, recorded in `OpenMCM_BUILD.json`.

This notice does not replace the licences or permissions of independently
licensed third-party materials below. In particular it does not claim ownership
of Bethesda assets or relicense the Jaxonz adaptations. The optional browser
component retains its GPL-3.0-only notice; the teaching Field Guide retains its
permissive example licence. Retain those notices when redistributing their code.

## Optional Jaxonz MCM Kicker adapter (2.0.1-rc.1)

The optional `JaxonzMCMKicker` and `JaxonzSKSEVersionCheckScript` adapters
derive from [Jaxonz MCM Kicker SE 1.1SE](https://www.nexusmods.com/skyrimspecialedition/mods/36801).
Credit Jaxonz (original author), insaneplumber (SE port), Oisaco1 (concept),
and NexusModsCaretaker (SE uploader). The page's permissions checked on
1 October 2026 allow modification and asset use with credit, prohibit sale
of the assets, and permit Donation Points. These adapted scripts are not
relicensed by OpenMCM's GPL notice. Their source is supplied beside the compiled
scripts. The original ESP/BSA is not bundled and is required separately.
See `docs/Jaxonz-MCM-Kicker.md` for the exact compatibility scope.

## MCM Menu Redone browser integration (OpenMCM 2.0.0)

[MCM Menu Redone 2.3.0](https://www.nexusmods.com/skyrimspecialedition/mods/186166)
is the browser behavior reference. The official Source And Build Tools archive
downloaded by the owner has SHA-256
`0583CC8659873106FE4C746A6D9D09F0EE601D59C8D92053FE1B78FB30AB2CD6`.
OpenMCM's browser ActionScript is independently implemented; no Redone/SkyUI
ConfigPanel class, timeline artwork or prebuilt PEX/SWF is imported.

The optional **OpenMCMBrowser.dll** does adapt Redone's **original** native
profile codec/store and Scaleform persistence bridge under GPL-3.0-only.
It excludes Redone's registry, Papyrus and serialization layers, has its own
plugin identity/profile path, and uses bounded, transactional persistence.
Its existing GPL-3.0-only licence is included as
`LICENSE-OpenMCMBrowser-GPL-3.0.txt`; complete corresponding module source,
build instructions and pinned dependency sources/licences are in the package's
`source/` archive, identified by OpenMCM_BUILD.json. This also covers the
CommonLibSSE-NG and other dependencies used by this component. See the module's
notices for their individual licences. SKSE and Address Library binaries are
not bundled. The previous chargen DLL remains independently implemented.

## Compatibility references

OpenMCM is an independently implemented compatibility layer. Compatibility was
checked against the public interfaces of the following projects; their names,
APIs, and code remain the property of their respective authors:

- [SkyUI](https://github.com/schlangster/skyui) and
  [SkyUI Community](https://github.com/doodlum/SkyUI-Community), used as the
  behavioral and MCM API compatibility references. No SkyUI artwork, exported
  timeline symbols, packaged scripts, or ActionScript classes are distributed
  from this source tree.
- [MCM Helper](https://github.com/Exit-9B/MCM-Helper), MIT License, used to
  verify its documented and source-visible integration contract. MCM Helper is
  not bundled.

The optional native character-creation fix is independently implemented and
does not contain copied RaceMenu or Engine Fixes code. Its engine behavior was
reviewed against primary upstream references and the locally installed Skyrim
executable:

- [RaceMenu / SKSE64Plugins](https://github.com/expired6978/SKSE64Plugins),
  used as a research reference for disabling character-creation precaching,
  including gender changes. RaceMenu is not bundled.
- [SSE Engine Fixes](https://github.com/aers/EngineFixesSkyrim64), MIT License,
  used as a research reference for `DisableChargenPrecache`. Engine Fixes is
  not bundled.
- [SKSE](https://skse.silverlock.org/), used to verify the public native plugin
  ABI against the SKSE 2.3.1 SDK. OpenMCM declares only the minimal ABI needed
  by this component; it does not bundle the SKSE SDK or SKSE runtime binaries.

These engine-patch references do not change the MCM implementation's SkyUI
and MCM Helper reference scope. The native component requires a compatible
SKSE installation supplied separately by the user.

The build downloads and executes these tools. They are checksum-pinned and are
not included in the OpenMCM release zip:

- [BSArch / xEdit](https://github.com/TES5Edit/TES5Edit), Mozilla Public
  License 2.0.
- [Caprica](https://github.com/Orvid/Caprica), MIT License.
- [JPEXS Free Flash Decompiler](https://github.com/jindrapetrik/jpexs-decompiler),
  GNU General Public License v3 or later.
- [MTASC 1.15](https://sourceforge.net/projects/mtasc/), GNU General Public
  License v2.
- [Spriggit](https://github.com/Mutagen-Modding/Spriggit), GNU General Public
  License v3.

The generated `Interface/quest_journal.swf` is a modified form of the vanilla
Journal interface extracted from the builder's local copy of The Elder Scrolls
V: Skyrim Special Edition. Bethesda Softworks/Bethesda Game Studios owns that
base game asset. It is not relicensed by OpenMCM's GPL notice and is not stored
in this repository.

The Elder Scrolls, Skyrim, Bethesda, SkyUI, and MCM Helper are trademarks or
names of their respective owners. OpenMCM is not endorsed by or affiliated
with them.
