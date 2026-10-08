# Independent MCM ConfigPanel UI

`MCMCompatBootstrap.install(journal)` creates the exact object path used by
SkyUI's Papyrus MCM scripts:

```text
_root.ConfigPanelFader.configPanel
```

The panel is drawn at runtime using AVM1 primitives and text fields. It has no
imports from `skyui.*`, no CLIK component dependency, and no copied SkyUI
timeline symbols or artwork. `ConfigPanel.as` is a conventional facade and ABI
index; `MCMCompatPanel.as` contains the panel/API adapter. `MCMCompatList.as`
owns each list's selection, scrolling, native row callbacks and renderer pool.
Mod, page, option and menu-dialog lists are separate persistent controls.

Mouse rollover selects within the originating list. A press consumes that
list's selected entry and sends an item event to the panel, which checks its
READY state before invoking the existing MCM/Papyrus event. Rows contain
ordinary transparent geometry, not hidden replacement hit areas. Input gates
belong to the lists; dialogs save and restore component focus without a
full-screen mouse blocker or hiding the Journal subtree.

Option headers, labels and values support HTML. Their typography helper uses
SkyUI's parsed-format readback before restoring spacing/kerning; do not replace
it with a fresh partial `TextFormat` or a blanket white-color assignment.
Mixed-run font/color attributes must survive, and pooled fields must retain
clean defaults for their next entry. Plain-text surfaces remain plain text.
Markup-free/entity-free options also take that plain-text path. For formatted
options, the helper supplies explicit inherited HTML font/color/paragraph
defaults because dynamic fields lack SkyUI's authored DefineEditText state.
Translate before wrapping and leave provider markup intact inside the wrapper.

## Journal integration

Call this during the Quest Journal's extension initialization, before any code
reads `ConfigPanelFader.configPanel`:

```actionscript
this.ConfigPanel = MCMCompatBootstrap.install(this);
```

The journal must route input to `this.ConfigPanel.handleInput(...)`, show the
fader in `ConfigPanelOpen`, and hide it in `ConfigPanelClose`. The bootstrap
does not require an imported `ConfigPanelFader` linkage asset.

## Build caveats

- Compile for AVM1 / ActionScript 2 and inject all required `.as` classes into the
  same `quest_journal.swf` class pool (for FFDec, under `__Packages`).
- An independent `configpanel.swf` may be shipped as a compatibility marker,
  but the dynamic bootstrap does not load or import it.
- `MCMCompatEntry.main()` is only an optional standalone entry point. The
  journal call to `MCMCompatBootstrap.install(this)` is the reliable path.
- Text translation relies on Skyrim's native `$TOKEN` resolution in a hidden
  text field. Mod events, input enablement, and key remapping require SKSE's
  injected `skse` object, exactly as Papyrus MCMs do.
- Raw `Key` events are disabled by default to prevent double navigation when
  the Journal routes `handleInput`. Set `_global.MCM_COMPAT_RAW_KEYS = true`
  before installation only for a host that does not route Scaleform input.
- The real Journal's FocusHandler initializes Scaleform's
  `Selection.disableFocusRolloverEvent` extension, as SkyUI's does. Plain AVM1
  emulators may still synthesize rollouts on a focus change; do not treat an
  emulator's focus behavior as an in-game verification.

See `MCM_COMPAT_ABI.json` for the auditable method/event contract.
