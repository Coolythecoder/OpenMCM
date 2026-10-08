# OpenMCM MCM Bridge Add-on — notices

## OpenMCM

Copyright (C) 2026 TheElderLord1337 and OpenMCM contributors.
Original adapter code is licensed under GPL-3.0-or-later, without warranty.
The full unmodified GPL version 3 is supplied in LICENSE.txt. Corresponding
adapter source, tests, build tools and compile-time inputs are included in the
versioned source ZIP. This package contains no OpenMCM host binaries or assets.
Historical OpenMCM MIT attribution is retained in
`licenses/OpenMCM-previous-MIT.txt` inside that source ZIP.

## MCM Bridge

By Wuerfelhusten / MCM Bridge contributors, GPL-3.0-only.
Project: https://github.com/Wuerfelhusten/MCM-Bridge
Audited version: 1.1.0, commit
`c039e67e9455ab9b21ba3024d8f6b3b157a511e2`.

The source ZIP includes exact Papyrus compile-time imports, upstream LICENSE
and THIRD_PARTY_NOTICES.md under `upstream/mcm-bridge`. Their hashes are pinned
in `src/compat/mcm-bridge/upstream.json`. These files remain under their upstream
terms. They are not replacement runtime scripts: install MCM Bridge separately.
No MCM Bridge DLL, PEX, frontend assets or native dependency code is distributed
by this add-on. This compatibility preview is not an upstream endorsement.

## SkyUI, SKSE, MCM Helper and frontends

The adapter implements OpenMCM's named-option API and delegates ordinary MCM
behavior to the separately installed Bridge base class. SkyUI, SKSE, MCM Helper,
FLICK and SKSE Menu Framework remain separate dependencies with their own
licences. Compile-only Papyrus declaration stubs under `vendor/papyrus-stubs`
are included to reproduce the adapter build, never installed as runtime scripts.
The standalone Field Guide example is not part of this add-on's runtime payload.

No Bethesda game assets, game binaries, compiler executables, private logs or
memory dumps are included. Third-party notices are not overridden by the
OpenMCM licence, and no additional ownership or redistribution rights are claimed.
