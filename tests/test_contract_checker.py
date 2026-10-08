from __future__ import annotations

import json
import hashlib
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPOSITORY_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_mcm_contract import PEX_MAGIC, validate  # noqa: E402


MANIFEST_PATH = Path(__file__).parent / "contracts" / "skyui6_mcm_contract.json"


def _subrecord(signature: bytes, payload: bytes) -> bytes:
    return signature + struct.pack("<H", len(payload)) + payload


def _record(signature: bytes, form_id: int, payload: bytes, flags: int = 0) -> bytes:
    return (
        signature
        + struct.pack("<I", len(payload))
        + struct.pack("<I", flags)
        + struct.pack("<I", form_id)
        + b"\0" * 8
        + payload
    )


def _minimal_plugin(form_local_id: int = 0x802, extra_master: str | None = None) -> bytes:
    header_payload = _subrecord(b"HEDR", struct.pack("<fII", 1.7, 1, 0x801))
    header_payload += _subrecord(b"MAST", b"Skyrim.esm\0") + _subrecord(b"DATA", b"\0" * 8)
    if extra_master:
        header_payload += _subrecord(b"MAST", extra_master.encode("ascii") + b"\0")
        header_payload += _subrecord(b"DATA", b"\0" * 8)
    header = _record(b"TES4", 0, header_payload, flags=0x200)

    quest_payload = _subrecord(b"EDID", b"SKI_ConfigManagerInstance\0")
    quest_payload += _subrecord(
        b"VMAD",
        b"\x11\0SKI_ConfigManager\0"
        b"SKI_QF_ConfigManagerInstance\0Fragment_0\0"
        b"Alias_PlayerRef\0SKI_PlayerLoadGameAlias\0",
    )
    quest_payload += _subrecord(b"DNAM", struct.pack("<H", 0x119) + b"\0" * 10)
    quest_payload += _subrecord(b"INDX", b"\x01\x00\x00\x13")
    quest_payload += _subrecord(b"ALST", struct.pack("<I", 0))
    quest_payload += _subrecord(b"ALID", b"PlayerRef\0")
    quest_payload += _subrecord(b"ALFR", struct.pack("<I", 0x14))
    quest_payload += _subrecord(b"ALED", b"")
    quest = _record(b"QUST", 0x01000000 | form_local_id, quest_payload)
    group = b"GRUP" + struct.pack("<I", 24 + len(quest)) + b"QUST" + b"\0" * 12 + quest
    return header + group


def _write_checksum_manifest(root: Path) -> None:
    manifest = root / "OpenMCM_SHA256SUMS.txt"
    lines = []
    for path in sorted((item for item in root.rglob("*") if item.is_file())):
        if path == manifest:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _minimal_pex(symbols: set[str], script: str, parent: str) -> bytes:
    values = [script, parent, ""]
    values.extend(sorted(symbols - set(values), key=str.casefold))
    indices = {value: index for index, value in enumerate(values)}

    def pex_string(value: str) -> bytes:
        encoded = value.encode("utf-8")
        return struct.pack(">H", len(encoded)) + encoded

    header = PEX_MAGIC + bytes((3, 2)) + struct.pack(">H", 1) + struct.pack(">Q", 0)
    header += pex_string(f"{script}.psc") + pex_string("fixture") + pex_string("fixture")
    table = struct.pack(">H", len(values)) + b"".join(pex_string(value) for value in values)
    metadata = b"\0" + struct.pack(">H", 0) + struct.pack(">H", 1)
    object_payload = (
        struct.pack(">H", indices[parent])
        + struct.pack(">H", indices[""])
        + struct.pack(">I", 0)
        + struct.pack(">H", indices[""])
        + struct.pack(">H", 0)  # variables
        + struct.pack(">H", 0)  # properties
        + struct.pack(">H", 0)  # states
    )
    script_object = (
        struct.pack(">H", indices[script])
        + struct.pack("<I", len(object_payload))
        + object_payload
    )
    return header + table + metadata + script_object


def _minimal_swf(tokens: list[str]) -> bytes:
    metadata = "\0".join(tokens).encode("utf-8")
    rect = b"\x08\x00"  # one-bit zero-valued frame rectangle
    frame_header = rect + b"\x00\x0c\x01\x00"
    tag_header = struct.pack("<H", (77 << 6) | 0x3F) + struct.pack("<I", len(metadata))
    body = frame_header + tag_header + metadata + b"\0\0"
    return b"FWS" + b"\x08" + struct.pack("<I", 8 + len(body)) + body


def _symbols_for(contract: dict[str, object]) -> set[str]:
    import re

    symbols = set(contract.get("required_identifiers", []))
    symbols.update(contract.get("required_exact_identifiers", []))
    symbols.add(str(contract["script"]))
    symbols.add(str(contract.get("extends", "")))
    for declaration in contract.get("required_declarations", []):
        match = re.search(r"(?i)\b(?:event|function|property)\s+(\w+)", declaration)
        if match:
            symbols.add(match.group(1))
    return {symbol for symbol in symbols if symbol}


class FixturePackage:
    """Build small, deterministic source/release fixtures from the public manifest."""

    def __init__(self, root: Path, manifest: dict[str, object]):
        self.root = root
        self.manifest = manifest

    def write_source(self) -> None:
        papyrus_root = self.root / "src" / "papyrus"
        papyrus_root.mkdir(parents=True)
        variable_lines = {
            "SKI_ConfigBase": [
                "int _configID",
                "int _currentPageNum",
                "int _state",
                "int _cursorPosition",
                "int _cursorFillMode",
                "int[] _optionFlagsBuf",
                "string[] _textBuf",
                "string[] _strValueBuf",
                "float[] _numValueBuf",
                "float[] _sliderParams",
                "int[] _menuParams",
                "int[] _colorParams",
                "string _infoText",
                "string _inputStartText",
                "bool _messageResult",
                "bool _waitForMessage",
            ],
            "SKI_ConfigManager": [
                "SKI_ConfigBase[] _modConfigs",
                "string[] _modNames",
                "SKI_ConfigBase _activeConfig",
            ],
        }
        for contract in self.manifest["papyrus"]:
            script = contract["script"]
            lines = [f"Scriptname {script} extends {contract['extends']}"]
            lines.extend(variable_lines.get(script, []))
            lines.extend(contract.get("required_declarations", []))
            if script == "SKI_ConfigBase":
                lines.extend(
                    (
                        "If candidate == None",
                        "    Return",
                        "EndIf",
                        "previousManager = _configManager",
                        "previousID = _configID",
                        "assignedID = candidate.RegisterMod(Self, ModName)",
                        "If assignedID >= 0",
                        "    _configManager = candidate",
                        "    _configID = assignedID",
                        "    If previousManager != candidate || previousID != assignedID",
                        "        OnConfigRegister()",
                        "    EndIf",
                        "EndIf",
                    )
                )
            # Identifiers and event names need to survive as PEX/source symbols.  The
            # declarations above provide most; these strings model registration calls.
            lines.extend(f'string _fixture_{index} = "{value}"' for index, value in enumerate(contract.get("required_literals", [])))
            lines.extend(f"; symbol {value}" for value in contract.get("required_identifiers", []))
            lines.extend(
                f'RegisterForModEvent("{binding["event"]}", "{binding["handler"]}")'
                for binding in contract.get("required_event_bindings", [])
            )
            lines.extend(
                f'SendModEvent("{event_name}")'
                for event_name in contract.get("required_sent_events", [])
            )
            (papyrus_root / f"{script}.psc").write_text("\n".join(lines) + "\n", encoding="utf-8")

        plugin_root = self.root / "src" / "plugin" / "SkyUI_SE.esp"
        quest_root = plugin_root / "Quests"
        quest_root.mkdir(parents=True)
        (plugin_root / "RecordData.yaml").write_text(
            "ModKey: SkyUI_SE.esp\n"
            "GameRelease: SkyrimSE\n"
            "ModHeader:\n"
            "  Flags:\n"
            "  - Small\n"
            "  MasterReferences:\n"
            "  - Master: Skyrim.esm\n",
            encoding="utf-8",
        )
        (quest_root / "SKI_ConfigManagerInstance.yaml").write_text(
            "FormKey: 000802:SkyUI_SE.esp\n"
            "EditorID: SKI_ConfigManagerInstance\n"
            "VirtualMachineAdapter:\n"
            "  Scripts:\n"
            "  - Name: SKI_ConfigManager\n"
            "  - Name: SKI_QF_ConfigManagerInstance\n"
            "    Properties:\n"
            "    - Name: Alias_PlayerRef\n"
            "  Fragments:\n"
            "  - Stage: 1\n"
            "    ScriptName: SKI_QF_ConfigManagerInstance\n"
            "    FragmentName: Fragment_0\n"
            "  Aliases:\n"
            "  - Scripts:\n"
            "    - Name: SKI_PlayerLoadGameAlias\n"
            "Flags:\n"
            "- StartGameEnabled\n"
            "- AllowRepeatedStages\n"
            "- RunOnce\n"
            "Stages:\n"
            "- Index: 1\n"
            "Aliases:\n"
            "- Name: PlayerRef\n"
            "  ForcedReference: 000014:Skyrim.esm\n",
            encoding="utf-8",
        )

        for asset in self.manifest["ui_assets"]:
            if asset["name"] == "MCM ConfigPanel bridge":
                path = self.root / "src" / "actionscript" / "ModConfigPanel" / "ConfigPanel.as"
            else:
                path = self.root / "src" / "actionscript" / "PauseMenu" / "Quest_Journal.as"
            path.parent.mkdir(parents=True, exist_ok=True)
            tokens = asset.get("required_source_tokens", asset.get("required_tokens", []))
            text = "\n".join(tokens) + "\n"
            text += "\n".join(
                f'MCMCompatUtil.sendModEvent("{event_name}", null, 0);'
                for event_name in asset.get("required_dispatched_events", [])
            )
            if asset["name"] == "Journal Menu MCM host":
                text += "function ConfigPanelOpen() {}\nfunction ConfigPanelClose() {}\n"
            path.write_text(text, encoding="utf-8")

    def write_release(self, form_local_id: int = 0x802, extra_master: str | None = None) -> None:
        data = self.root / "Data"
        scripts = data / "Scripts"
        interface = data / "Interface"
        scripts.mkdir(parents=True)
        (interface / "skyui").mkdir(parents=True)
        (data / "SkyUI_SE.esp").write_bytes(_minimal_plugin(form_local_id, extra_master))

        for contract in self.manifest["papyrus"]:
            symbols = "\0".join(sorted(_symbols_for(contract), key=str.casefold)).encode("ascii")
            symbol_set = _symbols_for(contract)
            (scripts / f"{contract['script']}.pex").write_bytes(
                _minimal_pex(symbol_set, str(contract["script"]), str(contract.get("extends", "")))
            )

        swf_tokens: dict[str, list[str]] = {}
        for asset in self.manifest["ui_assets"]:
            tokens = asset.get("required_release_tokens", asset.get("required_tokens", []))
            swf_tokens.setdefault(asset["runtime_path"], []).extend(tokens)

        for runtime_path, tokens in swf_tokens.items():
            swf = _minimal_swf(list(dict.fromkeys(tokens)))
            target = data / runtime_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(swf)

        sequence = data / "Seq" / "SkyUI_SE.seq"
        sequence.parent.mkdir(parents=True, exist_ok=True)
        sequence.write_bytes(struct.pack("<II", 0x01000802, 0x01000820))


class ContractCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_reference_source_satisfies_contract(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertTrue(report.ok, "\n".join(report.errors))
        self.assertGreater(report.checks, 100)

    def test_cached_skyui_reference_cannot_shadow_implementation_source(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        source = self.root / "src" / "papyrus" / "SKI_ConfigBase.psc"
        cached_text = source.read_text(encoding="utf-8").replace(
            "assignedID = candidate.RegisterMod(Self, ModName)", "assignedID = -1"
        )
        for folder in (".tools", "build", "dist", "vendor"):
            cache = self.root / folder / "skyui-reference" / "source" / "scripts"
            cache.mkdir(parents=True)
            (cache / source.name).write_text(cached_text, encoding="utf-8")
        # Explicit source traversal prunes caches; auto source checks filter
        # candidates without weakening the inventory used for release checks.
        for profile in ("source", "auto"):
            with self.subTest(profile=profile):
                report = validate(self.root, MANIFEST_PATH, profile)
                self.assertTrue(report.ok, "\n".join(report.errors))

    def test_cached_valid_source_cannot_mask_broken_real_source(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        source = self.root / "src" / "papyrus" / "SKI_ConfigBase.psc"
        valid_source = source.read_text(encoding="utf-8")
        for folder in (".tools", "build", "dist", "vendor"):
            cache = self.root / folder / "reference"
            cache.mkdir(parents=True)
            (cache / source.name).write_text(valid_source, encoding="utf-8")
        source.write_text(
            valid_source.replace("function ForcePageReset()", "function ResetCurrentPage()"),
            encoding="utf-8",
        )
        for profile in ("source", "auto"):
            with self.subTest(profile=profile):
                report = validate(self.root, MANIFEST_PATH, profile)
                self.assertFalse(report.ok)
                self.assertTrue(any("PAPYRUS_SIGNATURE_MISSING: src/papyrus/SKI_ConfigBase.psc"
                                    in error and "ForcePageReset" in error
                                    for error in report.errors))

    def test_source_cache_filter_cannot_supply_missing_ui_tokens(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        source = self.root / "src/actionscript/ModConfigPanel/ConfigPanel.as"
        valid_source = source.read_text(encoding="utf-8")
        cached = self.root / ".tools/skyui-reference/source/actionscript/ModConfigPanel/ConfigPanel.as"
        cached.parent.mkdir(parents=True)
        cached.write_text(valid_source, encoding="utf-8")
        source.write_text(valid_source.replace("SKICP_optionSelected", "BROKEN_optionSelected"),
                          encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(any("UI_TOKEN_MISSING" in error and "SKICP_optionSelected" in error
                            for error in report.errors))

    def test_release_checksum_inventory_still_includes_cache_named_paths(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        _write_checksum_manifest(self.root)
        for folder in (".tools", "build", "dist", "vendor"):
            cache = self.root / folder
            cache.mkdir()
            (cache / "unexpected.psc").write_text("not checksummed", encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        for folder in (".tools", "build", "dist", "vendor"):
            self.assertTrue(any("CHECKSUM_FILE_UNLISTED" in error
                                and f"{folder}/unexpected.psc" in error
                                for error in report.errors))

    def test_reference_release_satisfies_contract(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertTrue(report.ok, "\n".join(report.errors))
        self.assertGreater(report.checks, 100)

    def test_missing_api_signature_is_reported(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        path = self.root / "src" / "papyrus" / "SKI_ConfigBase.psc"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("function ForcePageReset()", "function ResetCurrentPage()"), encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(any("PAPYRUS_SIGNATURE_MISSING" in error and "ForcePageReset" in error for error in report.errors))

    def test_ready_heartbeat_requires_original_register_mod_handshake(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        path = self.root / "src" / "papyrus" / "SKI_ConfigBase.psc"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                "assignedID = candidate.RegisterMod(Self, ModName)",
                "assignedID = -1",
            ),
            encoding="utf-8",
        )
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(any("original RegisterMod ABI" in error for error in report.errors))

    def test_fake_pex_with_only_magic_and_symbols_is_rejected(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        path = self.root / "Data" / "Scripts" / "SKI_ConfigBase.pex"
        path.write_bytes(PEX_MAGIC + b"SKI_ConfigBase\0ForcePageReset")
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("PEX_PARSE_ERROR" in error for error in report.errors))

    def test_manager_pex_rejects_lowercase_custom_reference_type(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        path = self.root / "Data" / "Scripts" / "SKI_ConfigManager.pex"
        payload = path.read_bytes()
        canonical = b"SKI_ConfigBase[]"
        caprica_casing = b"sKI_ConfigBase[]"
        self.assertEqual(payload.count(canonical), 1)
        path.write_bytes(payload.replace(canonical, caprica_casing))

        report = validate(self.root, MANIFEST_PATH, "release")

        self.assertFalse(report.ok)
        self.assertTrue(
            any(
                "PEX_EXACT_IDENTIFIER_MISSING" in error
                and "SKI_ConfigBase[]" in error
                for error in report.errors
            )
        )
        self.assertTrue(
            any(
                "PEX_FORBIDDEN_IDENTIFIER" in error
                and "sKI_ConfigBase[]" in error
                for error in report.errors
            )
        )

    def test_fake_swf_with_only_magic_and_tokens_is_rejected(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        path = self.root / "Data" / "Interface" / "quest_journal.swf"
        payload = b"SKICP_modSelected\0ConfigPanelOpen"
        path.write_bytes(b"FWS\x08" + struct.pack("<I", 8 + len(payload)) + payload)
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("SWF_INVALID" in error for error in report.errors))

    def test_mcm_helper_private_layout_is_enforced(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        path = self.root / "src" / "papyrus" / "SKI_ConfigManager.psc"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("SKI_ConfigBase[] _modConfigs", "Form[] _modConfigs"), encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(any("MCM Helper requires SKI_ConfigBase[] _modConfigs" in error for error in report.errors))

    def test_bridge_event_rename_is_reported(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        path = self.root / "src" / "actionscript" / "ModConfigPanel" / "ConfigPanel.as"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("SKICP_optionSelected", "OPENMCM_optionSelected"), encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(any("UI_TOKEN_MISSING" in error and "SKICP_optionSelected" in error for error in report.errors))

    def test_manager_event_cannot_be_bound_to_the_wrong_handler(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        path = self.root / "src" / "papyrus" / "SKI_ConfigManager.psc"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            'RegisterForModEvent("SKICP_pageSelected", "OnPageSelect")',
            'RegisterForModEvent("SKICP_pageSelected", "OnModSelect")',
        )
        path.write_text(text, encoding="utf-8")
        report = validate(self.root, MANIFEST_PATH, "source")
        self.assertFalse(report.ok)
        self.assertTrue(
            any(
                "PAPYRUS_EVENT_BINDING_MISSING" in error
                and "SKICP_pageSelected -> OnPageSelect" in error
                for error in report.errors
            )
        )

    def test_wrong_manager_form_id_is_reported(self) -> None:
        FixturePackage(self.root, self.manifest).write_release(form_local_id=0x803)
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("MANAGER_FORM_MISSING" in error for error in report.errors))

    def test_external_skyui_master_is_rejected(self) -> None:
        FixturePackage(self.root, self.manifest).write_release(extra_master="SomeOtherMCM.esp")
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("EXTERNAL_MASTER_FORBIDDEN" in error for error in report.errors))

    def test_plugin_must_keep_the_light_flag(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        plugin = self.root / "Data" / "SkyUI_SE.esp"
        payload = bytearray(plugin.read_bytes())
        struct.pack_into("<I", payload, 8, 0)
        plugin.write_bytes(payload)
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("PLUGIN_FLAGS_MISMATCH" in error for error in report.errors))

    def test_manager_quest_startup_flags_are_required(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        plugin = self.root / "Data" / "SkyUI_SE.esp"
        payload = bytearray(plugin.read_bytes())
        dnam = payload.index(b"DNAM")
        payload[dnam + 6 : dnam + 8] = b"\0\0"
        plugin.write_bytes(payload)
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("MANAGER_QUEST_FLAGS_MISMATCH" in error for error in report.errors))

    def test_manager_player_alias_script_is_required(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        plugin = self.root / "Data" / "SkyUI_SE.esp"
        payload = plugin.read_bytes()
        self.assertEqual(payload.count(b"SKI_PlayerLoadGameAlias"), 1)
        plugin.write_bytes(payload.replace(b"SKI_PlayerLoadGameAlias", b"XKI_PlayerLoadGameAlias"))
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("player alias script" in error for error in report.errors))

    def test_embedded_ui_runtime_path_is_enforced_case_insensitively(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        source = self.root / "Data" / "Interface" / "quest_journal.swf"
        source.rename(self.root / "Data" / "quest_journal.swf")
        report = validate(self.root, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("Data/Interface/quest_journal.swf" in error for error in report.errors))

    def test_release_zip_is_supported(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        _write_checksum_manifest(self.root)
        archive = self.root / "OpenMCM.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            for path in self.root.rglob("*"):
                if path.is_file() and path != archive:
                    package.write(path, path.relative_to(self.root))
        report = validate(archive, MANIFEST_PATH, "release")
        self.assertTrue(report.ok, "\n".join(report.errors))

    def test_packaged_checksum_manifest_covers_exact_inventory(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        _write_checksum_manifest(self.root)
        archive = self.root / "checksummed.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            for path in self.root.rglob("*"):
                if path.is_file() and path != archive:
                    package.write(path, path.relative_to(self.root))
        report = validate(archive, MANIFEST_PATH, "release")
        self.assertTrue(report.ok, "\n".join(report.errors))

        with zipfile.ZipFile(archive, "a", zipfile.ZIP_DEFLATED) as package:
            package.writestr("unexpected.txt", "not listed")
        report = validate(archive, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("CHECKSUM_FILE_UNLISTED" in error for error in report.errors))

    def test_release_zip_requires_checksum_manifest(self) -> None:
        FixturePackage(self.root, self.manifest).write_release()
        archive = self.root / "missing-manifest.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            for path in (self.root / "Data").rglob("*"):
                if path.is_file():
                    package.write(path, path.relative_to(self.root))
        report = validate(archive, MANIFEST_PATH, "release")
        self.assertFalse(report.ok)
        self.assertTrue(any("CHECKSUM_MANIFEST_MISSING" in error for error in report.errors))

    def test_unsafe_zip_entry_is_rejected(self) -> None:
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("../outside.txt", "unsafe")
        with self.assertRaisesRegex(ValueError, "unsafe zip entry path"):
            validate(archive, MANIFEST_PATH, "release")

    def test_unsafe_zip_directory_entry_is_rejected(self) -> None:
        archive = self.root / "unsafe-directory.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("../outside/", b"")
        with self.assertRaisesRegex(ValueError, "unsafe zip entry path"):
            validate(archive, MANIFEST_PATH, "release")

    def test_case_duplicate_zip_entry_is_rejected(self) -> None:
        archive = self.root / "duplicate.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("Data/example.txt", "one")
            package.writestr("data/EXAMPLE.txt", "two")
        with self.assertRaisesRegex(ValueError, "duplicate zip entry path"):
            validate(archive, MANIFEST_PATH, "release")

    def test_auto_uses_source_for_an_unbuilt_checkout(self) -> None:
        FixturePackage(self.root, self.manifest).write_source()
        report = validate(self.root, MANIFEST_PATH, "auto")
        self.assertEqual(report.profile, "source")
        self.assertTrue(report.ok, "\n".join(report.errors))


class WorkspaceContractTest(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("MCM_CONTRACT_TARGET"),
        "set MCM_CONTRACT_TARGET to validate a real checkout/package",
    )
    def test_requested_workspace_or_package(self) -> None:
        target = os.environ["MCM_CONTRACT_TARGET"]
        profile = os.environ.get("MCM_CONTRACT_PROFILE", "auto")
        report = validate(target, MANIFEST_PATH, profile)
        self.assertTrue(report.ok, "\n".join(report.errors))


if __name__ == "__main__":
    unittest.main()
