# OpenMCM 2.0.1-rc.2 — acknowledged Kicker reset

Supersedes rc.1's unacknowledged stage-1 request. The optional Jaxonz MCM Kicker
adapter now calls a Boolean manager operation and reports success only after
the registry reset completes and reset/readiness signals have been dispatched.
Provider re-registration remains asynchronous and is not certified by this result.

- Busy/menu/storage rejections retain the pending kick and use bounded backoff.
- Six failed attempts terminate without a success notification.
- In-flight and load-generation guards protect against duplicate callbacks and
  stale responses; readiness events do not acknowledge completion.
- The full FOMOD checks that both host modes include the required manager method.
- Existing SkyUI API 4, the void ForceReset entry point, saved manager fields,
  registry size and MCM Helper quest identity remain unchanged.

Keep the original Jaxonz MCM Kicker SE ESPFE plugin and BSA installed. Reinstall
this full FOMOD so the adapted scripts and manager stay matched; copying only
the Kicker scripts onto rc.1 or older OpenMCM is not supported.

This is a local candidate requiring in-game verification, not a public release.
Nothing has been deployed to the game or uploaded to Nexus by this build.
