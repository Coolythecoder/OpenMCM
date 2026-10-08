# In-game Journal click-through and rc.5 correction

## Captured evidence

The owner supplied `SkyrimSE 2026-09-08 16-29-43_1.png` and
`SkyrimSE 2026-09-08 16-29-50_2.png`. The installed Journal matched the
diagnostic build SHA-256
`42489019D658D6709180A5D88A914F5AEABBF565CB13B4F275EA5408356A6EC1`.

Both captures show the main MCM list and a ready, active panel with its
mouse listener installed. They record nine raw mouse downs and ups, two
side-row rollovers and one side-row press. The last row event is
`sideOut #5`. These are cumulative counts, not nine proven failed row clicks.

The first pointer is outside the main panel, at panel-local `(15,403)`,
and the picked target is `none`. In the second it is over blank welcome
content at `(506,288)`, with this target:

```text
_level0.QuestJournalFader.Menu_mc.SystemFader.Page_mc.CreationListPanel.cList_mc.Entry3
```

The dynamic MCM fader is at depth 0; the vanilla Journal fader is at -16383.
Thus the existing depth correction is present. A vanilla descendant is
nevertheless pickable through noninteractive MCM content. Neither capture
has the pointer over an MCM name, so these images do not identify the cause
of every reported failed row click. One row press reached its callback.

## Correction

`MCMCompatBootstrap.suspendJournalInput` captures the exact vanilla fader
reference and its visibility/hit-test flags once, then sets `_visible=false`
and `hitTestDisable=true`. Patched and fallback host opening paths call it
before returning focus to the MCM; `startPage` calls it defensively too.

`restoreJournalInput` clears ownership and restores only that captured clip,
including its native hit-test flag. `endPage` restores after hiding MCM and
before the host focuses the Journal. Unload also restores; repeated calls
are inert. No global mouse routing, native input hook, pause counter, or
registration-manager behavior changed.

This is a modern vanilla-host adaptation. SkyUI's authored lifecycle uses
fade/depth transitions and its own list input management. A fade is not
equivalent to making a clip invisible, and a higher noninteractive graphic
does not itself block underlying AVM1 button picks. Scaleform documents the
visibility distinction and the native
[hit-test-disabling extension](https://help.autodesk.com/cloudhelp/ENU/Scaleform-Help/scaleform_help/as2_reference/movieclip_extensions.html).

## Red/green verification

The real-input fixture injects a transparent clickable sentinel into the
actual Journal fader at the second screenshot's coordinates. Playwright
sends browser clicks to Ruffle running the compiled Journal; the runner does
not manually invoke mouse handlers.

| Phase | Old diagnostic host | rc.5 |
| --- | ---: | ---: |
| Before opening MCM | 1 background press | 1 background press |
| MCM open | 1 (defect) | 0 |
| Repeated open | 1 (defect) | 0 |
| Closed | 1 | 1 |
| Direct panel end | Not part of baseline run | 1 |
| Actual MovieClip unload | Not part of baseline run | 1 |

The rc.5 host also emits exactly one XPMSE selection from a real row click.
Probe-on/off runs pass, including probe removal and four-line display bounds.
Ownership regression tests cover pre-existing flags, native property setters,
host replacement, repeated close/unload, and missing clips.

The full build ran 167 tests: 166 passed, one skipped. Native regression
checks also passed (82 cases); native patch behavior was not changed. Source,
staging and final-package contract checks passed. The final tested SWF is
`7FC72B9685CD3CF3B243B9FE6CBC93AC13787C970D1117F6E0E00F01500C76E7`.

Ruffle is not Skyrim's Scaleform runtime. This establishes a regression for
the observed isolation defect, not universal in-game mouse compatibility.
An in-game test over actual MCM names/pages/settings remains necessary.

## Delivery

`dist/OpenMCM-Mouse-Update-rc5.zip` contains only the Journal SWF, the
OpenMCM Status-page script retaining the optional probe, instructions and
license. SHA-256:
`F3D8971EE2F06D8052DDD3FB0E88F6EDE1A11BAFD788CC8B9B6A1C8A2442ECCC`.

It replaces the temporary diagnostic add-on while leaving the main OpenMCM
installation enabled. It contains no DLL, INI or ESP. No game installation,
mod-manager state or Nexus upload was changed during this correction. The
separate exit-to-desktop crash is not claimed fixed.
