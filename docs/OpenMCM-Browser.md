# OpenMCM browser — 2.0

This is a first integration of MCM Menu Redone-style browser features, not a
complete replacement for every Redone feature. It is part of the main OpenMCM
FOMOD, in both standalone and With SkyUI modes. Do not install MCM Menu Redone
alongside it: both replace the MCM host. No separate UI addon is required.

## Controls

The mod-list screen has All, Favourites and Hidden tabs, name search, and
A–Z, Z–A or registration-order sorting. Hover or select an MCM, then use
Favourite, Hide, Rename or Priority. R / controller X opens the same browser
actions through the existing list/dialog controls. Tab still goes back.

- Search checks the displayed name, original name and original translation key.
  Clear removes the temporary search. Search is not persisted.
- Hide only removes a menu from All/Favourites. Open Hidden to unhide it; the
  mod remains registered and its settings are not changed.
- An empty rename restores the author's name. Labels are limited to 60 characters.
- Priority 1 is first; 999 is last among pinned menus; 0 means unpinned. Priority
  sorts before the selected alphabetical/registration ordering.
- Each tab remembers its sort and scroll position. Preferences for absent menus
  are retained, so a temporarily unavailable provider does not lose its label.

The original registration index and raw mod name still select the provider.
Renaming and sorting never rewrite its Papyrus ID. Preferences are keyed by raw
mod name, not a FormID: two providers with exactly the same raw name share their
browser preferences. A provider that changes its raw name is a new entry.

## Save-local or optional shared preferences

The recommended installer choice has **no browser DLL**. Browser preferences
are stored by the existing manager with the savegame. Save the game after
customising the browser to retain changes across reloads. Loading an earlier
save restores its preferences. Explicit edits publish state immediately; there
is no background timer or quest-registry polling.

The optional **Shared browser preferences** choice includes OpenMCMBrowser.dll
in the same FOMOD. It saves one shared browser profile under your actual Windows
Documents folder, in `My Games/<Skyrim runtime folder>/SKSE/OpenMCM/Browser/Default.omcmb`.
It requires matching SKSE, Address Library and the Microsoft Visual C++ 2022 x64
runtime. The allowlisted game versions are 1.5.97, 1.6.640, 1.6.1170 and 1.7.104;
other versions, including VR, are not supported by this component. These are
source/build-supported versions, not in-game-tested claims.

A valid shared profile normally takes precedence over the loaded save's
preferences. The manager still keeps a save-local fallback. A missing/invalid
shared profile falls back to the save. If a shared write fails, the fallback is
marked for local recovery and takes precedence over the stale shared profile
when the menu reopens. This also means an older save carrying an unresolved
recovery marker can supersede later shared edits. The browser reports the
failure, retries on the next save/close even without another edit, and clears
the recovery marker only after a successful shared write. The marker is never
written to the shared profile. Save the game to retain recovery across reloads.

An untouched menu cannot publish default preferences while the manager reply
is pending, and a temporary empty mod list cannot erase remembered scrolling.
Browser controls show a loading status and stay disabled until that reply,
including when a shared profile exists, so an early click cannot discard
unknown saved preferences. An invalid reply enables the controls with an error
status but does not overwrite stored state until the user changes something.
This component uses no Papyrus native functions, registry replacement,
serialization hooks, input hooks or character-creation patch. The separate
OpenMCMRuntime chargen component remains its own optional installer choice.

The shared profile is deliberately separate from Redone's profile. Existing
Redone state is not imported automatically. Back it up before switching hosts.
Preferences have a bounded 32,768-character state, including four reserved
characters for local recovery; an oversized state reports an error instead of
truncating saved data. Never remove a profile file while the
game is running.

## Scope and limitations

- The registry remains **128 MCMs**. MCM Helper directly reads SkyUI's original
  `_modConfigs[_configID]` arrays; Redone's expanded/native registry cannot simply
  replace those without breaking that contract.
- A browser profile is **not a mod-settings preset**. It does not export or
  restore provider settings, run callbacks, or change MCM Helper's persistence.
- The new API's page-navigation and conditional-group helpers require author
  adoption and the Runtime API option. Browser features do not require API 1.
- It does not fix or establish the cause of the separately reported exit crash.

Automated checks cover browser ordering/identity, storage validation, compiled
AVM1 behavior and installer branches. A fresh in-game test is still required:
click/keyboard/controller navigation, provider controls and coloured text,
save/reload, shared profile across characters if selected, and quit to desktop.
Use a separate test profile and backed-up saves. The 2.0 package version does
not establish new verified support for the MCMs tested with standalone
OpenMCM 1.1. See the compatibility list for the scope of those historical results.
