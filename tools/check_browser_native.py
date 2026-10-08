#!/usr/bin/env python3
"""Read-only PE/metadata validation for experimental browser persistence DLL.

Never loads the DLL. This does not establish in-game runtime correctness.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from check_native_runtime import PEImage, METADATA_SIZE, ascii_z, require

SUPPORTED_VERSIONS = ((1, 5, 97), (1, 6, 640), (1, 6, 1170), (1, 7, 104))
RUNTIME_NAMES = tuple(".".join(map(str, version)) for version in SUPPORTED_VERSIONS)
RUNTIMES = tuple((major << 24) | (minor << 16) | (patch << 4) for major, minor, patch in SUPPORTED_VERSIONS)


def validate_dll(data: bytes) -> dict:
    image = PEImage(data)
    exports = image.exports()
    image.require_export(exports, "SKSEPlugin_Load", executable=True)
    image.require_export(exports, "SKSEPlugin_Query", executable=True)
    metadata = image.require_export(exports, "SKSEPlugin_Version", executable=False, size=METADATA_SIZE)
    data_version, plugin_version = struct.unpack_from("<II", metadata)
    require(data_version == 1 and plugin_version > 0, "Invalid SKSE browser version metadata")
    require(ascii_z(metadata[8:0x108], "plugin name") == "OpenMCMBrowser", "Unexpected browser plugin identity")
    author = ascii_z(metadata[0x108:0x208], "author")
    require("SpawneR27" in author, "Missing original profile-code attribution")
    extended, independence = struct.unpack_from("<II", metadata, 0x304)
    require(extended == 2 and independence == 4,
            "Browser must retain CommonLib Address Library v5 metadata/updated structs, not unlimited runtime claims")
    versions = struct.unpack_from("<16I", metadata, 0x30C)
    require(versions == RUNTIMES + (0,) * 12, "Browser runtime allowlist differs from audited versions")
    for function in (b"BeginProfileStateUpdate", b"AppendProfileStateChunk", b"CommitProfileStateUpdate",
                     b"GetProfileStateChunkCount", b"GetProfileStateChunk", b"HasProfileState"):
        require(function + b"\0" in data, f"Missing native profile bridge name {function!r}")
    require(b"OPENMCM_BROWSER_PROFILE_V1" in data, "Missing separate browser profile format")
    require(b"MCMR_PROFILE_V1" not in data, "Foreign Redone profile must not be silently imported")
    return {"plugin": "OpenMCMBrowser", "plugin_version": plugin_version,
            "supported_game_runtimes": RUNTIME_NAMES, "address_library_required": True,
            "game_tested": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_dll(args.dll.read_bytes()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
