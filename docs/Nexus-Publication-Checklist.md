# Nexus moderation response checklist

This checklist addresses the requirements in the owner's supplied moderation
notice. Packaging checks are not a legal compliance certificate or an assurance
that Nexus will approve the page.

## Released baseline and preservation

On 7 October 2026 the owner reported that their compliance edits were complete
and the Nexus listing was out of review and back online. This is an owner report,
not an independent inspection of the live page or a new in-game test.

Keep the published `dist/OpenMCM-2.1-FOMOD.zip` unchanged. Its recorded hash and
local comparison are in `release/OpenMCM-2.1.0-publication.md`. The local archive
has no additional archive-only edits to import; its licensing and source files
already match the build inputs. Keep the following materials in future builds:

- The complete unmodified GPL text in `LICENSE.txt` and `LICENSE`.
- Copyright, GPL grant, warranty disclaimer and third-party boundaries in
  `README.txt`, with matching attribution in `README.md` and
  `THIRD_PARTY_NOTICES.md`.
- Prior licence notices under `licenses/` and each component's own notices.
- Complete corresponding source with build instructions, pinned dependency
  sources and matching release/checksum metadata; not browser-only source.

Nexus description and permission edits are separate from the ZIP. Preserve the
owner's live edits. Do not replace them with the older 2.0 description or the
template below without inspecting and incorporating the current page text.
Those page-specific edits have not been copied into this workspace.

## In the revised download

- `LICENSE.txt`: full GPL version 3 text; conventional `LICENSE` retained too.
- `README.txt`: copyright notice, GPL grant and warranty disclaimer, source
  location, and explicit third-party boundaries.
- `source/OpenMCM-2.1.0-Source.zip`: complete editable OpenMCM code, examples,
  plugin YAML, build scripts, tests, pinned CommonLibSSE-NG and dependency source.
- Browser GPL licence, original browser-source archive, upstream notices and
  historical MIT attribution are retained, not silently removed or overwritten.
- No working-folder dump, crash/hang memory dumps, local diagnostics, compiler
  executables, build caches, Git histories or extracted game assets in source.

## Checklist for future uploads

1. Upload the intended newly validated source-inclusive FOMOD without
   overwriting the local published baseline. Do not upload the earlier oversized working-folder archive or the
   first clean archive that contained only the browser's source.
2. Retain the owner's current source/licensing information in the description
   and update versioned source paths when needed. The template below is a
   reference, not a replacement for the owner's edits. State
   where users can find the source; a private or nonexistent repository is not
   a substitute for source access.
3. Set page permissions to permit modification and redistribution of original
   OpenMCM code under GPL terms. Preserve attribution and source/licence duties.
   Do not claim blanket ownership or additional rights over third-party content.
4. Reply through the moderator's existing review channel after the updated
   file, description and permission settings are actually saved. Do not claim
   these external changes were completed merely because this package was built.

Suggested description text:

> Original OpenMCM code is available under GPL-3.0-or-later. The download includes
> LICENSE.txt and the copyright/warranty notice in README.txt. Complete editable
> project source, build scripts, plugin YAML, examples and pinned dependency
> sources are supplied in source/OpenMCM-2.1.0-Source.zip. See BUILD-SOURCE.txt
> inside for build prerequisites. Third-party components retain their own notices
> and terms, detailed in THIRD_PARTY_NOTICES.md. The browser component retains its
> GPL-3.0-only notice; the optional Jaxonz adapter retains its upstream permissions.

Suggested reply, **only after making the page changes**:

> Thank you for explaining the requirements. I have updated the download with
> LICENSE.txt containing the full GPL v3 text, README.txt containing the copyright
> and GPL/warranty notice, and a clean full-project source archive with build
> instructions and dependency sources. I have added the source location to the
> description and enabled modification/redistribution permissions for OpenMCM's
> original code, with third-party attributions and terms preserved. Please review
> the revised package and let me know if you need any further changes.
