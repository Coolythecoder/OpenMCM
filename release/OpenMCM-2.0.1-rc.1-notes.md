# OpenMCM 2.0.1-rc.1 — Kicker compatibility candidate

Adds an optional **Jaxonz MCM Kicker SE** compatibility add-on to the full
FOMOD. The installer recommends it when the original plugin is detected and
otherwise recommends omission. The original mod remains a separate requirement.

- Recognises the compatible MCM manager on Kicker's own checker instance
  without claiming full SkyUI support for other Jaxonz mods.
- Defers the one-shot load refresh while Journal/character creation is open.
- Retains upstream script/quest identities and the existing stage-1 command.
- Installs only two adapted scripts and their source; no new ESP or DLL.
- Preserves the 2.0 host, API 4 compatibility, experimental extension API 1,
  and all previous independent FOMOD choices.

This is a local release candidate, not a new in-game compatibility claim.
See `docs/Jaxonz-MCM-Kicker.md` for requirements, credits and the test checklist.
Nothing has been deployed to the game or uploaded to Nexus by this build.
