# OpenMCM 1.2.0-alpha.2 — API preview

One full FOMOD installer, no add-on installation. Retains alpha.1's standalone
and SkyUI-detected coexistence choices, with OpenMCM as MCM host in both.

## New opt-in API 1

- `OpenMCM_ConfigBase` extends the existing SkyUI-compatible base.
- Named option creation/binding without changing numeric or ST callbacks.
- Automatic help, with explicit callback overrides including empty text.
- Live labels, text-option values and help/status without page resets.
- Provider/page guards and persistent SDK generations reject obsolete updates.
- Validation traces, capability discovery, a full API guide, and a compiled
  example covering both ordinary and state-based callbacks.

The legacy SkyUI API remains version 4. Existing providers do not need migration.
MCM Helper keeps its own JSON schema, base class, persistence and requirements.
New API providers require OpenMCM; they do not run on vanilla SkyUI alone.

## Testing status

This is an experimental SDK/coexistence build, not an owner-verified release.
Build tests cover scripts, examples, UI behavior and installer projections.
In-game testing of the new API and live SkyUI coexistence is still required.
The owner's earlier successful MCM tests apply to standalone 1.1.0 only.

The native component remains optional, omitted by default, and limited to
Skyrim 1.7.104.0. Its behavior is unchanged. No installed files, existing saves,
published 1.1 archive, or Nexus uploads are changed by building this preview.

See README.md for install/migration cautions and docs/OpenMCM-API.md for the SDK.
