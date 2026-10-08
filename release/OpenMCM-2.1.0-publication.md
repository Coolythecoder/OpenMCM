# OpenMCM 2.1 — preserved publication baseline

On 7 October 2026 the owner reported that they had made compliance edits and
that the Nexus listing was out of review and back online. They asked to retain
those edits. This records the owner's report; the live Nexus description,
permissions and uploaded bytes were not independently inspected in this task.
Moderation status does not establish new gameplay testing.

## Local archive identity

- Archive: `dist/OpenMCM-2.1-FOMOD.zip`
- Internal version: `2.1.0`
- Size: 13,523,534 bytes
- SHA-256: `0C2227709E5317C1C244D5C649B0A5539B57DF3ECD13FEDE815754EA1FA5B17F`
- Complete source: `source/OpenMCM-2.1.0-Source.zip`
- Complete-source SHA-256: `B54B863AE8471D0DEDC505BFB4718C3C470C34AF3F9FFE2C8F1504EFF6B69A88`

The supplied local ZIP matches the 3 October build byte-for-byte. There are no
additional archive-only changes to import. Its GPL, README notice, third-party
notices and licence files are already the project's build inputs, and its
complete source is already included by the main builder. Any additional
Nexus-page-only edits remain on Nexus; their exact text is not recorded here.

## Preserve on subsequent releases

Do not rebuild over, repack or rename this published archive. Use a new output
version for a new release. Do not strip its source bundle or restore the older
browser-source-only packaging. Keep the full unmodified GPL text, copyright
and warranty notice, original attribution and third-party licence boundaries.
Update source paths and metadata consistently when making a new release.

The main builder refuses an existing output archive so a same-version build
cannot silently replace a released or manually edited ZIP. Packaging regression
tests also check the GPL text, notice content and source-copy wiring.

Keep the owner's live Nexus description and permissions. Do not publish the
historical `OpenMCM-2.0.0-nexus-description.txt` or generic moderation-response
template over their edits. Consult `docs/Nexus-Publication-Checklist.md` when
preparing later releases. This preservation update changes no gameplay logic
and does not modify the published ZIP or the Nexus page.
