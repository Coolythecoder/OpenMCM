# OpenMCMBrowser (experimental native profile persistence)

The profile codec and file-store design derive from **MCM Menu Redone 2.3.0**,
by **SpawneR27**, under GPL-3.0. See `LICENSE-GPL-3.0.txt`.
Original source: https://www.nexusmods.com/skyrimspecialedition/mods/186166

OpenMCM modifications (2026-09-19): separate runtime/namespace/profile identity,
transactional in-memory rollback, per-movie transfers, immutable read snapshots,
bounds/NaN checks, movie-owned return strings and corruption-backup failure checks.
The original registry, serialization, Papyrus bindings, translations and
SkyUI-derived interface assets are **not** compiled or copied into this component.

This DLL is independent of OpenMCMRuntime's optional character-creation patch.
It registers only `skse.plugins.OpenMCMBrowser` for browser profile persistence.
It never holds quest, actor, game-form or movie pointers and installs no input,
gameplay, VM, save/load, quit or background-thread hooks. All I/O happens only
at initialization or on an explicit browser preference change. It does not
increase the 128-menu registry limit, preserving the MCM Helper array contract.

Profile path: the matching game's SKSE log directory, then
`OpenMCM/Browser/Default.omcmb`. There is no automatic migration from Redone.
Only browser presentation preferences are stored; this is not mod-setting import.
The UI retains per-save preferences if the DLL is absent or has no valid profile.

Build dependency: CommonLibSSE-NG 7.5.1, commit
`bedcb1e05418baba7b316a650b6180c2dd6007a8` from
https://github.com/alandtse/CommonLibSSE-NG . Build with xmake 3.1.1 and MSVC.
CommonLib is GPL-3.0-or-later WITH Modding Exception and GPL-3.0 Linking Exception;
its exact `COPYING.txt` and `EXCEPTIONS.md` must accompany a distributed DLL.

Explicit runtime allowlist: 1.5.97, 1.6.640, 1.6.1170 and 1.7.104. The pinned
CommonLib source defines these versions, including 1.7.104. Matching SKSE and
Address Library and Microsoft Visual C++ 2022 x64 Redistributable are required.
This is source-supported, **not in-game verified**.
All other versions/VR fail closed before SKSE initialization.

Bridge: `BeginProfileStateUpdate()`, `AppendProfileStateChunk(string)`,
`CommitProfileStateUpdate()` return booleans. Chunks are at most 1024 ASCII bytes,
total at most 32768 bytes. Only valid `OPENMCMB1` envelopes are accepted; empty,
malformed, non-ASCII or oversized updates cannot overwrite a profile. Names and
aliases use ActionScript `escape()` percent encoding. Invalid writes abort the
pending transaction. Read with
`GetProfileStateChunkCount()` then `GetProfileStateChunk(index)`; the count call
captures an immutable snapshot. `HasProfileState()` distinguishes a valid
persisted profile from an absent/invalid one. No automatic Redone data import.
