#!/usr/bin/env python3
"""Package editable OpenMCM sources and a verified browser source bundle offline.

This checks package integrity and scope; it does not certify legal compliance.
Build outputs, local diagnostics, game assets and tool executables are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from package_browser_native_source import COMMONLIB_COMMIT, DEPENDENCIES

SOURCE_TREES = ("src", "scripts", "tools", "tests", "vendor", "examples", "docs", "release", "licenses")
ROOT_FILES = ("README.md", "README.txt", "LICENSE", "LICENSE.txt", "THIRD_PARTY_NOTICES.md",
              "COMPATIBILITY.md", "build.ps1")
REQUIRED_PROJECT_FILES = ROOT_FILES + (
    "src/actionscript/ConfigPanel.as", "src/papyrus/SKI_ConfigBase.psc",
    "src/native/OpenMCMRuntime.cpp", "src/browser-native/Bridge.cpp",
    "src/plugin/SkyUI_SE.esp/RecordData.yaml", "src/plugin-coexist/OpenMCM.esp/RecordData.yaml",
    "src/translations/SkyUI_SE_ENGLISH.tsv", "scripts/Build-OpenMCM.ps1",
    "licenses/OpenMCM-previous-MIT.txt",
)
TEXT_SUFFIXES = frozenset({
    ".as", ".psc", ".flg", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".inl", ".inc", ".lua", ".py", ".ps1", ".psm1", ".psd1", ".cmd", ".bat", ".sh",
    ".yaml", ".yml", ".json", ".tsv", ".csv", ".ini", ".cfg", ".toml", ".xml",
    ".md", ".rst", ".txt", ".cmake", ".in", ".natvis", ".patch", ".props", ".targets",
})
TEXT_NAMES = frozenset({"license", "copying", "notice", "authors", "makefile", "dockerfile", "usage",
                        ".gitignore", ".gitattributes", ".gitmodules", ".clang-format",
                        ".editorconfig", ".aiderignore", ".cursorrules"})
EXCLUDED_DIRS = frozenset({
    ".git", ".svn", ".hg", ".tools", ".xmake", ".vs", ".vscode", ".idea", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
    "build", "dist", "package", "staging", "output", "outputs", "out", "cache", "downloads",
    "diagnostics", "dumps", "logs", "assets", "screenshots", "saves", "profiles",
})
COMMONLIB_PREFIX = ".tools/CommonLibSSE-NG-7.5.1/"
# These are upstream address-library parser test inputs, not compiled programs.
# They are retained from the verified browser source bundle, never from .tools.
COMMONLIB_TEST_DATA = frozenset(COMMONLIB_PREFIX + "tests/REL/" + name for name in (
    "version-1-5-97-0.bin", "version-invalid-format.bin", "versionlib-1-6-1130-0.bin",
    "versionlib-1-6-1170-0.bin", "versionlib-1-6-1179-0.bin", "versionlib-1-6-353-0.bin",
    "versionlib-1-6-629-0.bin", "versionlib-1-7-99-0.bin",
))
BROWSER_ROOT_FILES = frozenset({"DEPENDENCIES.json", "BUILD-SOURCE.txt", "SHA256SUMS.txt"})
BROWSER_SUPPORT_FILES = frozenset({
    "scripts/Build-BrowserNative.ps1", "tools/check_browser_native.py",
    "tools/check_native_runtime.py", "tools/package_browser_native_source.py",
})
MAX_MEMBER_SIZE = 32 * 1024 * 1024
MAX_ARCHIVE_SIZE = 256 * 1024 * 1024
ZIP_DATE = (2026, 9, 19, 0, 0, 0)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> str:
    """Accept only canonical relative paths safe to extract on Windows or Unix."""
    if (not name or any(char in name for char in '\\:*?"<>|')
            or any(ord(char) < 32 or ord(char) == 127 for char in name) or name.startswith("/")):
        raise ValueError(f"Unsafe archive path: {name!r}")
    parts = name.split("/")
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                *(f"lpt{i}" for i in range(1, 10))}
    if any(not part or part in {".", ".."} or part.endswith((".", " "))
           or part.split(".")[0].casefold() in reserved for part in parts):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return name


def is_text_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (path.suffix.casefold() in TEXT_SUFFIXES or path.name.casefold() in TEXT_NAMES
            or (path.parts[0] == "licenses" and path.name.casefold().endswith("_license")))


def check_text(name: str, data: bytes) -> None:
    if len(data) > MAX_MEMBER_SIZE:
        raise ValueError(f"Oversized source file: {name}")
    try:
        encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        decoded = data.decode(encoding)
    except UnicodeError as error:
        raise ValueError(f"Non-text content in source file: {name}") from error
    if "\0" in decoded:
        raise ValueError(f"Non-text content in source file: {name}")


def reject_link(path: Path) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Symlink or reparse point is not a source input: {path}")


def add_file(files: dict[str, bytes], names: dict[str, str], name: str, data: bytes) -> None:
    safe_name(name)
    previous = names.get(name.casefold())
    if previous is not None and (previous != name or files[previous] != data):
        raise ValueError(f"Source collision: {previous} and {name}")
    names[name.casefold()] = name
    files[name] = data


def project_sources(root: Path) -> dict[str, bytes]:
    reject_link(root)
    files: dict[str, bytes] = {}
    names: dict[str, str] = {}

    def walk_error(error: OSError) -> None:
        raise error

    def collect(path: Path) -> None:
        reject_link(path)
        if not path.is_file():
            raise ValueError(f"Source input is not a regular file: {path}")
        name = path.relative_to(root).as_posix()
        if path.stat().st_size > MAX_MEMBER_SIZE:
            raise ValueError(f"Oversized source file: {name}")
        data = path.read_bytes()
        check_text(name, data)
        add_file(files, names, name, data)

    for name in ROOT_FILES:
        path = root / name
        if not path.exists():
            raise ValueError(f"Required project source/documentation missing: {name}")
        collect(path)
    for tree in SOURCE_TREES:
        base = root / tree
        if not base.exists():
            continue
        reject_link(base)
        for directory, subdirs, filenames in os.walk(base, followlinks=False, onerror=walk_error):
            subdirs[:] = sorted(name for name in subdirs if name.casefold() not in EXCLUDED_DIRS)
            for name in subdirs:
                reject_link(Path(directory) / name)
            for name in sorted(filenames):
                if is_text_name((Path(directory) / name).relative_to(root).as_posix()):
                    collect(Path(directory) / name)
    for required in REQUIRED_PROJECT_FILES:
        if required not in files:
            raise ValueError(f"Required editable component missing: {required}")
    return files


def read_archive(archive: Path | io.BytesIO) -> dict[str, bytes]:
    """Read bounded regular members without extracting untrusted paths."""
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    total = 0
    with zipfile.ZipFile(archive) as source:
        if len(source.infolist()) > 10000:
            raise ValueError("Too many source archive members")
        for item in source.infolist():
            name = safe_name(item.filename[:-1] if item.is_dir() else item.filename)
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (kind == stat.S_IFDIR and not item.is_dir()):
                raise ValueError(f"Symlink or special archive member: {name}")
            if item.flag_bits & 1:
                raise ValueError(f"Encrypted archive member: {name}")
            if name.casefold() in seen:
                raise ValueError(f"Duplicate or case-colliding source member: {name}")
            seen.add(name.casefold())
            if item.is_dir():
                continue
            total += item.file_size
            if item.file_size > MAX_MEMBER_SIZE or total > MAX_ARCHIVE_SIZE:
                raise ValueError("Oversized source archive")
            files[name] = source.read(item)
    file_names = {name.casefold() for name in files}
    for name in seen:
        if any(str(parent) in file_names for parent in PurePosixPath(name).parents if str(parent) != "."):
            raise ValueError(f"File/directory collision in source archive: {name}")
    return files


def verify_manifest(files: dict[str, bytes]) -> dict[str, str]:
    if "SHA256SUMS.txt" not in files:
        raise ValueError("Browser source SHA256SUMS.txt manifest is missing")
    manifest: dict[str, str] = {}
    try:
        for line in files["SHA256SUMS.txt"].decode("utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
            if not match:
                raise ValueError("Invalid browser source manifest line")
            digest, name = match.groups()
            safe_name(name)
            if name in manifest:
                raise ValueError(f"Duplicate browser manifest entry: {name}")
            manifest[name] = digest.lower()
    except UnicodeError as error:
        raise ValueError("Invalid browser source manifest encoding") from error
    if set(manifest) != set(files) - {"SHA256SUMS.txt"}:
        raise ValueError("Browser source manifest does not match archive members")
    for name, digest in manifest.items():
        if sha256(files[name]) != digest:
            raise ValueError(f"Browser source manifest checksum mismatch: {name}")
    return manifest


def verify_browser(files: dict[str, bytes]) -> None:
    verify_manifest(files)
    required = BROWSER_ROOT_FILES | BROWSER_SUPPORT_FILES | {
        "src/browser-native/Bridge.cpp", "src/browser-native/xmake.lua",
        "src/browser-native/LICENSE-GPL-3.0.txt", COMMONLIB_PREFIX + "xmake.lua",
        COMMONLIB_PREFIX + "include/SKSE/Version.h", COMMONLIB_PREFIX + "COPYING.txt",
        COMMONLIB_PREFIX + "EXCEPTIONS.md",
    }
    if required - files.keys():
        raise ValueError(f"Incomplete browser source bundle: {sorted(required - files.keys())}")
    try:
        metadata = json.loads(files["DEPENDENCIES.json"])
        expected_archives = [{"file": name, "url": url, "sha256": digest}
                             for name, url, digest in DEPENDENCIES]
        if (metadata.get("commonlib") != {"version": "7.5.1", "commit": COMMONLIB_COMMIT}
                or metadata.get("source_archives") != expected_archives):
            raise ValueError("Browser dependency pins do not match the build")
    except (UnicodeError, json.JSONDecodeError, AttributeError) as error:
        raise ValueError("Invalid browser dependency metadata") from error
    archives = {"dependencies/source/" + name: digest for name, _, digest in DEPENDENCIES}
    for name, digest in archives.items():
        if name not in files or sha256(files[name]) != digest:
            raise ValueError(f"Pinned dependency source checksum mismatch: {name}")
    for name, data in files.items():
        if name in archives or name in COMMONLIB_TEST_DATA:
            continue
        relative = name.removeprefix(COMMONLIB_PREFIX)
        allowed = (name.startswith((COMMONLIB_PREFIX, "src/browser-native/", "licenses/"))
                   or name in BROWSER_ROOT_FILES or name in BROWSER_SUPPORT_FILES)
        if (not allowed or not is_text_name(name)
                or EXCLUDED_DIRS.intersection(part.casefold() for part in PurePosixPath(relative).parts[:-1])):
            raise ValueError(f"Unexpected browser source member: {name}")
        check_text(name, data)


def browser_sources(path: Path) -> dict[str, bytes]:
    reject_link(path)
    if path.stat().st_size > MAX_ARCHIVE_SIZE:
        raise ValueError("Oversized browser source archive")
    files = read_archive(path)
    verify_browser(files)
    return files


def validate_source_archive(raw: bytes, *, version: str | None = None,
                            browser_sha256: str | None = None) -> list[str]:
    """Return verified member names; raise ValueError for invalid scope/integrity.

    This validates declared package content, not legal compliance, reproducible
    compilation or the origin of every source line.
    """
    if len(raw) > MAX_ARCHIVE_SIZE:
        raise ValueError("Oversized full-source archive")
    files = read_archive(io.BytesIO(raw))
    verify_manifest(files)
    generated = {"BUILD-SOURCE.txt", "SHA256SUMS.txt", "OPENMCM-SOURCE.json"}
    provenance = {"source-manifests/browser/BUILD-SOURCE.txt", "source-manifests/browser/SHA256SUMS.txt"}
    required = set(REQUIRED_PROJECT_FILES) | generated | provenance
    if required - files.keys():
        raise ValueError(f"Incomplete full-source archive: {sorted(required - files.keys())}")
    try:
        metadata = json.loads(files["OPENMCM-SOURCE.json"])
        if (metadata.get("format") != 1 or metadata.get("project") != "OpenMCM"
                or not isinstance(metadata.get("version"), str)
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", metadata["version"])
                or not isinstance(metadata.get("browser_source_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", metadata["browser_source_sha256"])):
            raise ValueError("Invalid full-source metadata")
    except (UnicodeError, json.JSONDecodeError, AttributeError) as error:
        raise ValueError("Invalid full-source metadata") from error
    if version is not None and metadata["version"] != version:
        raise ValueError("Full-source version does not match the enclosing release")
    if browser_sha256 is not None and metadata["browser_source_sha256"] != browser_sha256.lower():
        raise ValueError("Full-source browser checksum does not match the enclosing release")
    # Verify the preserved browser manifest against the exact merged source bytes.
    # Reuse browser validation to check dependency pins and narrow binary exceptions.
    browser = {"SHA256SUMS.txt": files["source-manifests/browser/SHA256SUMS.txt"]}
    try:
        for line in browser["SHA256SUMS.txt"].decode("utf-8").splitlines():
            match = re.fullmatch(r"[0-9a-fA-F]{64}  (.+)", line)
            if not match:
                raise ValueError("Invalid preserved browser source manifest")
            name = safe_name(match.group(1))
            merged = "source-manifests/browser/" + name if name == "BUILD-SOURCE.txt" else name
            if merged not in files:
                raise ValueError(f"Missing merged browser source: {name}")
            if name in browser:
                raise ValueError(f"Duplicate preserved browser manifest entry: {name}")
            browser[name] = files[merged]
    except UnicodeError as error:
        raise ValueError("Invalid preserved browser source manifest encoding") from error
    verify_browser(browser)
    for name, data in files.items():
        if name in browser or name in provenance or name in generated:
            continue
        parts = PurePosixPath(name).parts
        if (name not in ROOT_FILES and (parts[0] not in SOURCE_TREES
                or EXCLUDED_DIRS.intersection(part.casefold() for part in parts[:-1]))) or not is_text_name(name):
            raise ValueError(f"Unexpected full-source member: {name}")
        check_text(name, data)
    return sorted(files)


def package(root: Path, browser_source: Path, output: Path, version: str) -> None:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("Invalid release version")
    if output.suffix.casefold() != ".zip":
        raise ValueError("Source output must be a .zip file")
    if output.resolve() == browser_source.resolve():
        raise ValueError("Source output must not overwrite its browser source input")
    files = project_sources(root)
    browser = browser_sources(browser_source)
    names = {name.casefold(): name for name in files}
    for name, data in browser.items():
        # Preserve the original browser instructions and manifest as provenance;
        # the new root manifest covers the complete merged project.
        if name in {"BUILD-SOURCE.txt", "SHA256SUMS.txt"}:
            name = "source-manifests/browser/" + name
        add_file(files, names, name, data)
    files["BUILD-SOURCE.txt"] = (
        f"OpenMCM {version} - complete project source package\n\n"
        "Editable ActionScript 2, Papyrus, both native components, plugin YAML, translations,\n"
        "compatibility scripts, examples, stubs, build scripts, checks and tests are included.\n"
        "The browser source is merged at its original paths, including pinned CommonLib source,\n"
        "third-party source ZIPs under dependencies/source and licenses. CommonLib's eight\n"
        "tests/REL/*.bin files are upstream parser test data, not runtime or tool executables.\n"
        "Original browser instructions/checksums are under source-manifests/browser.\n\n"
        "Read README.md, README.txt, LICENSE, THIRD_PARTY_NOTICES.md and COMPATIBILITY.md.\n"
        "Build on Windows with PowerShell 5.1/7, Python 3.10+, Java 8+, Windows tar, Visual Studio\n"
        "2022 C++ build tools and Windows SDK. Install xmake 3.1.1 at\n"
        ".tools/xmake-3.1.1/xmake/xmake.exe (or supply -Xmake to Build-BrowserNative.ps1).\n"
        "The complete build downloads checksum-pinned BSArch, Caprica 0.3.0, FFDec 26.2.1,\n"
        "MTASC 1.15 and Spriggit 0.41.0; their binaries are not redistributed here. The build\n"
        "and xmake may need network access or preinstalled tool/dependency caches. Included\n"
        "dependency source ZIPs are original sources, not an offline xmake package cache.\n"
        "Supply your own lawful Skyrim Special Edition installation and game interface BSA;\n"
        "game assets, SKSE/Address Library runtime files and external SkyUI are not included.\n"
        "See COMPATIBILITY.md and component READMEs for runtime requirements.\n\n"
        "Install Node.js to run the JavaScript-backed UI unit tests; those tests skip if absent.\n"
        f"From the extracted root: .\\build.ps1 -Version {version} -SkyrimPath '<game directory>'\n"
        "The default output is the FOMOD under dist. Build scripts stage locally; review\n"
        "their prerequisites before running. See scripts/Build-FieldGuide.ps1 for the sample.\n"
        "Source packaging itself needs only Python and the existing browser source ZIP:\n"
        f"python tools/package_openmcm_source.py --project-root . --browser-source <browser-source.zip> --output <new-source.zip> --version {version}\n\n"
        "SHA256SUMS.txt covers every other file in this archive. These integrity checks and\n"
        "the source-selection policy are not a legal compliance certificate or proof of\n"
        "in-game behavior. Do not install this source ZIP as a game mod.\n"
    ).encode("utf-8")
    files["OPENMCM-SOURCE.json"] = (json.dumps({
        "format": 1, "project": "OpenMCM", "version": version,
        "browser_source_sha256": sha256(browser_source.read_bytes()),
        "scope": "Editable project sources, build scripts, tests and browser dependency sources",
        "legal_compliance_certified": False,
    }, indent=2, sort_keys=True) + "\n").encode("utf-8")
    files["SHA256SUMS.txt"] = "".join(f"{sha256(data)}  {name}\n" for name, data in sorted(files.items())).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only after verification, so a failed write cannot replace an archive.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".openmcm-source-", suffix=".zip", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, ZIP_DATE)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, data, compresslevel=9)
        with zipfile.ZipFile(temporary) as target:
            if target.testzip() is not None or set(target.namelist()) != set(files):
                raise ValueError("Full-source ZIP verification failed")
        validate_source_archive(temporary.read_bytes())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"OpenMCM source archive: {len(files)} files, {output.stat().st_size} bytes, {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--browser-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    package(args.project_root.absolute(), args.browser_source.absolute(), args.output.absolute(), args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
