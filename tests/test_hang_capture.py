"""Exercise the read-only dump validator; never execute the capture script."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/MinidumpValidation.ps1"
CAPTURE = ROOT / "scripts/Capture-SkyrimHang.ps1"


def dump_fixture(*, full=False):
    """Small structural fixture, not intended to be a debuggable process dump."""
    # Four directories, then metadata placeholders and one memory descriptor.
    data = bytearray(164 if full else 152)
    struct.pack_into("<IIIIIIQ", data, 0, 0x504D444D, 42899, 4, 32, 0, 0, 2 if full else 0)
    entries = [(3, 4, 80), (4, 4, 84), (7, 40, 88), (9 if full else 5, 32 if full else 20, 128)]
    for index, entry in enumerate(entries):
        struct.pack_into("<III", data, 32 + index * 12, *entry)
    if full:
        struct.pack_into("<QQQQ", data, 128, 1, 160, 0x10000, 4)
    else:
        struct.pack_into("<IQII", data, 128, 1, 0x10000, 4, 148)
    data[-4:] = b"DATA"
    return data


class HangCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not cls.powershell:
            raise unittest.SkipTest("PowerShell is required for the dump-validator tests")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openmcm-dump-validator-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def invoke(self, command, **variables):
        # The only dot-sourced script is the read-only validation helper.
        program = "$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest; . $env:VALIDATOR; " + command
        encoded = base64.b64encode(program.encode("utf-16-le")).decode("ascii")
        env = os.environ | {"VALIDATOR": str(VALIDATOR)} | {key: str(value) for key, value in variables.items()}
        process = subprocess.run(
            [self.powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, env=env, timeout=20,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def validate(self, data, *, full=False):
        path = self.folder / "fixture.dmp"
        path.write_bytes(data)
        return self.invoke(
            "Get-MinidumpValidation -LiteralPath $env:DUMP -RequireFullMemory:([bool]::Parse($env:FULL)) | ConvertTo-Json",
            DUMP=path, FULL=str(full),
        )

    def test_mini_and_full_payloads(self):
        for full in (False, True):
            with self.subTest(full=full):
                result = self.validate(dump_fixture(full=full), full=full)
                self.assertTrue(result["StructurallyValid"], result)
                self.assertEqual(result["FullMemory"], full)

    def test_rejects_invalid_headers(self):
        variants = [bytearray(b"MDMP"), dump_fixture(), dump_fixture(), dump_fixture(), dump_fixture()]
        variants[1][0:4] = b"NOPE"
        struct.pack_into("<I", variants[2], 4, 0)
        struct.pack_into("<I", variants[3], 8, 0)
        struct.pack_into("<I", variants[4], 8, 0xFFFFFFFF)
        for data in variants:
            with self.subTest(size=len(data)):
                self.assertFalse(self.validate(data)["StructurallyValid"])

    def test_rejects_directory_and_stream_out_of_bounds(self):
        for position, value in [(12, 0), (12, 1000), (36, 1000), (40, 1000)]:
            data = dump_fixture()
            struct.pack_into("<I", data, position, value)
            with self.subTest(position=position, value=value):
                self.assertFalse(self.validate(data)["StructurallyValid"])

    def test_rejects_truncated_external_memory_payloads(self):
        for full in (False, True):
            result = self.validate(dump_fixture(full=full)[:-1])
            self.assertFalse(result["StructurallyValid"])
            self.assertIn("Memory", result["Error"])

    def test_rejects_memory_descriptor_overflow(self):
        for full in (False, True):
            data = dump_fixture(full=full)
            struct.pack_into("<Q" if full else "<I", data, 128, 0xFFFFFFFFFFFFFFFF if full else 0xFFFFFFFF)
            self.assertFalse(self.validate(data)["StructurallyValid"])

    def test_full_memory_request_cannot_silently_accept_mini_dump(self):
        result = self.validate(dump_fixture(), full=True)
        self.assertFalse(result["StructurallyValid"])
        self.assertIn("flag", result["Error"])

    def test_requires_process_streams(self):
        data = dump_fixture()
        struct.pack_into("<I", data, 32, 0)
        self.assertFalse(self.validate(data)["StructurallyValid"])

    def test_requires_exactly_two_valid_artifacts(self):
        for count in range(4):
            folder = self.folder / str(count)
            folder.mkdir()
            for index in range(count):
                (folder / f"{index}.dmp").write_bytes(dump_fixture())
            result = self.invoke("Get-HangCaptureValidation -LiteralPath $env:DUMPS | ConvertTo-Json -Depth 4", DUMPS=folder)
            self.assertEqual(result["Complete"], count == 2)
            self.assertEqual(result["ValidCount"], count)
        # A present but unfinished second file does not make the set complete.
        (self.folder / "2/1.dmp").write_bytes(b"MDMP")
        result = self.invoke("Get-HangCaptureValidation -LiteralPath $env:DUMPS | ConvertTo-Json -Depth 4", DUMPS=self.folder / "2")
        self.assertFalse(result["Complete"])
        self.assertEqual(result["ValidCount"], 1)

    def test_capture_keeps_existing_safety_guards_and_no_automatic_retry(self):
        script = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("$expectedHash = 'D1FC99AE304BD1D2BF28ABEB62531DA959E2431916194981B88C958FD713A8E6'", script)
        self.assertIn("Get-AuthenticodeSignature", script)
        self.assertIn("[IO.Path]::GetFullPath($_.Path) -eq $expectedGame", script)
        self.assertIn("if (-not $NoClone) { $captureArgs += @('-r', '1', '-a') }", script)
        self.assertIn("if ($FullMemory) { '-ma' } else { '-mm' }", script)
        self.assertEqual(script.count("& $captureTool @captureArgs"), 1)
        self.assertLess(script.index("if (-not $validation.Complete)"), script.index("if ($captureExitCode -ne 0)"))
        nonzero_case = script[script.index("if ($captureExitCode -ne 0)"):]
        self.assertIn("Write-Warning", nonzero_case)
        self.assertNotIn("throw", nonzero_case)


if __name__ == "__main__":
    unittest.main()
