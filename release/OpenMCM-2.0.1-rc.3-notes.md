# OpenMCM 2.0.1-rc.3 — repair dialog storage on use

Full replacement FOMOD, not a separate hotfix. Retains both host modes, the
optional Field Guide and the acknowledged Jaxonz MCM Kicker reset from rc.2.

## Fix

- Allocate the SkyUI-compatible dialog parameter arrays when an MCM opens,
  before its page and open callbacks.
- Allocate each slider, menu and colour request's scratch array before writing
  defaults and dispatching the provider callback. Do not depend on an earlier
  initialization/reload event or a saved `_initialized` flag.
- Preserve the author's start/default/minimum/maximum/step values, callback IDs,
  state-based callbacks and MCM Helper field layout. Legitimate 0–1 sliders
  remain supported; no replacement range is imposed on mods.

## Evidence and limits

A read-only inspection of the affected save found `_initialized = true` but
null `_sliderParams`, `_menuParams` and `_colorParams` on the Field Guide, and
null slider storage on XPMSE. The installed compiled Field Guide callback
correctly supplies 25–500 with step 5. Missing storage prevents those setters
from recording their values. The UI then receives no usable range and falls
back to 0–1. Why the earlier lifecycle left these arrays null has not been
established; this repair makes dialog use independent of that lifecycle.

Automated source/behavior checks and package validation do not replace gameplay
verification. After reinstalling the full archive and fully restarting Skyrim,
load the existing save and check Field Guide > Preferences > Planned carry
budget: range 25–500, step 5, default 200. Check a third-party slider, a menu
selection and a colour dialog too. No new game or save cleaning is required by
the repair. No saves, mod settings or installed game files were edited to build
this candidate. It has not been published or verified in game.
