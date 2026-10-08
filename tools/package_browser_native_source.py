#!/usr/bin/env python3
"""Package complete browser-native corresponding source, including dependencies.

Downloads only pinned source archives if absent. No downloaded script is executed.
The compiler, Windows SDK and build-tool executables are not redistributed.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

COMMONLIB_COMMIT = "bedcb1e05418baba7b316a650b6180c2dd6007a8"
DEPENDENCIES = (
    ("DirectXMath-feb2024.zip", "https://github.com/microsoft/DirectXMath/archive/refs/tags/feb2024.zip",
     "214d71420107249dfb4bbc37a573f288b0951cc9ffe323dbf662101f3df4d766"),
    ("DirectXTK-feb2024.zip", "https://github.com/microsoft/DirectXTK/archive/feb2024.zip",
     "edb643b2444ff24925339cfb1bc9f76c671d5404a5549d32ecaa0d61bbab28c9"),
    ("spdlog-v1.16.0.zip", "https://github.com/gabime/spdlog/archive/refs/tags/v1.16.0.zip",
     "3d25808d2fc4db86621a46855800c99ab5734999b61c4cbf9470edf631555397"),
)


def dependency_source(root: Path, name: str, url: str, digest: str) -> bytes:
    """Prefer sources shipped in an extracted bundle; verify every origin."""
    bundled = root / "dependencies/source" / name
    cached = root / ".tools/downloads/browser-native-sources" / name
    selected = bundled if bundled.exists() else cached
    downloaded = not selected.exists()
    if not downloaded:
        data = selected.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError(f"Oversized dependency source: {name}")
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Source checksum mismatch: {name}")
    if downloaded:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


def package(root: Path, commonlib: Path, output: Path) -> None:
    files: dict[str, bytes] = {}
    for path in (root / "src/browser-native").rglob("*"):
        if path.is_file() and not {"build", ".xmake", "__pycache__"}.intersection(path.relative_to(root / "src/browser-native").parts):
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("scripts/Build-BrowserNative.ps1", "tools/check_browser_native.py",
                 "tools/check_native_runtime.py", "tools/package_browser_native_source.py"):
        files[name] = (root / name).read_bytes()
    if (commonlib / ".git").exists():
        commit = subprocess.check_output(["git", "-C", str(commonlib), "rev-parse", "HEAD"], text=True).strip()
        if commit != COMMONLIB_COMMIT:
            raise ValueError("Unpinned CommonLib checkout")
        paths = subprocess.check_output(["git", "-C", str(commonlib), "ls-files", "-z"]).decode().split("\0")
    else:
        paths = [path.relative_to(commonlib).as_posix() for path in commonlib.rglob("*") if path.is_file()]
    for name in sorted(filter(None, paths)):
        path = commonlib / name
        if path.is_file() and not {".git", "build", ".xmake"}.intersection(PurePosixPath(name).parts):
            files[f".tools/CommonLibSSE-NG-7.5.1/{name}"] = path.read_bytes()
    for name in ("COPYING.txt", "EXCEPTIONS.md"):
        files[f"licenses/CommonLibSSE-NG-{name}"] = (commonlib / name).read_bytes()
    for name, url, digest in DEPENDENCIES:
        data = dependency_source(root, name, url, digest)
        files[f"dependencies/source/{name}"] = data
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            license_members = [item for item in source.namelist() if PurePosixPath(item).name.lower() in {"license", "license.txt"}]
            if not license_members:
                raise ValueError(f"Dependency has no license: {name}")
            for member in license_members:
                files[f"licenses/{name.removesuffix('.zip')}-{member.replace('/', '_')}"] = source.read(member)
    files["DEPENDENCIES.json"] = (json.dumps({
        "commonlib": {"version": "7.5.1", "commit": COMMONLIB_COMMIT},
        "source_archives": [{"file": name, "url": url, "sha256": digest} for name, url, digest in DEPENDENCIES],
        "build_tool": "xmake 3.1.1; MSVC Visual Studio 2022; Windows SDK",
        "redistributable_runtime": "Microsoft Visual C++ 2022 x64",
    }, indent=2) + "\n").encode()
    files["BUILD-SOURCE.txt"] = (
        "OpenMCMBrowser corresponding source\n"
        "GPL-3.0 browser code derives from MCM Menu Redone 2.3.0 by SpawneR27.\n"
        "Full CommonLib source and third-party source archives/licenses are included.\n"
        "Build on Windows with Visual Studio 2022 C++, Windows SDK, Python 3 and xmake 3.1.1.\n"
        "Run scripts/Build-BrowserNative.ps1 -Version <release-version> -Xmake <path-to-xmake.exe>.\n"
        "Use the release version from OpenMCM_BUILD.json in the enclosing OpenMCM package.\n"
        "The script verifies CommonLib fingerprints and invokes xmake for pinned library versions.\n"
        "xmake can download matching dependency packages automatically; original sources are also\n"
        "included under dependencies/source for inspection, rebuilding and modified builds.\n"
        "Do not install this source ZIP as a game mod. No game deployment is performed.\n"
    ).encode()
    forbidden = {".exe", ".dll", ".pdb", ".obj", ".lib", ".exp"}
    if any(PurePosixPath(name).suffix.lower() in forbidden for name in files):
        raise ValueError("Compiled output must not enter corresponding-source archive")
    files["SHA256SUMS.txt"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 9, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, data)
    with zipfile.ZipFile(output) as target:
        if target.testzip() is not None or set(target.namelist()) != set(files):
            raise ValueError("Corresponding-source ZIP verification failed")
    print(f"Browser source archive: {len(files)} files, {output.stat().st_size} bytes, {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--commonlib", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.project_root.resolve(), args.commonlib.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
