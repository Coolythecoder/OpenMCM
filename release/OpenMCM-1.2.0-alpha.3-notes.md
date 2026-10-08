# OpenMCM 1.2.0-alpha.3 — Vortex installer correction

One complete replacement FOMOD, no add-ons. Use this archive instead of alpha.2;
do not bypass Vortex's validation warning on the older installer.

## Installer fix

- Corrected both XML declarations to double-quoted UTF-8 encoding. The previous
  declarations were valid XML, but incompatible with Nexus's quote-sensitive
  conversion to UTF-16, causing the reported invalid-character error at 1:39.
- Every FOMOD build now checks the actual ZIP through that conversion and .NET's
  XML reader, even when optional tests are skipped. The regression self-check
  reproduces the old failure before accepting the corrected files.
- Archive checks reject a reintroduced single-quoted declaration even if its
  XML structure and checksum are otherwise valid.

SkyUI detection, mode choices, installed-file mappings and runtime behavior
are unchanged from alpha.2. Standalone and SkyUI coexistence modes remain in
one installer, with OpenMCM hosting MCM in either mode.

## Included API preview

Retains opt-in OpenMCM API 1: named options, automatic help, guarded live
label/text/help updates, capability discovery, documentation and example.
The legacy SkyUI API remains version 4. Existing MCMs need no migration.
MCM Helper keeps its own base, JSON schema, persistence and requirements.

## Testing status

This remains an experimental API/coexistence build. Automated installer and
runtime checks do not establish in-game verification of the new API or live
SkyUI coexistence. Earlier owner testing applies to standalone 1.1.0 only.

The native component remains optional, omitted by default, and restricted to
Skyrim 1.7.104.0. Its behavior is unchanged; this installer fix makes no new
claim about character-creation stalls or exit-to-desktop crashes.

Building does not deploy to a game, alter saves, or upload to Nexus. See README.md
for installation cautions and docs/OpenMCM-API.md for the API guide.
