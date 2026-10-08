"""Dialog storage contracts and source-level request replay.

The replay executes the small Papyrus request body's assignments/branches with
stub provider callbacks. It is not a Papyrus VM or an in-game verification.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/papyrus/SKI_ConfigBase.psc").read_text(encoding="utf-8")


def body(name):
    match = re.search(rf"(?ims)^Function {name}\([^\n]*\)\s*\n(.*?)^EndFunction", SOURCE)
    if not match:
        raise AssertionError(f"Missing function: {name}")
    return re.sub(r";[^\n]*", "", match.group(1))


def replay(name, values):
    """Translate only the small request-body subset; unknown syntax fails."""
    lines = []
    indent = 0
    for line in body(name).splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "EndIf":
            indent -= 1
            continue
        if line == "Else":
            indent -= 1
            lines.append("    " * indent + "else:")
            indent += 1
            continue
        line = re.sub(r"\bNew (?:Float|Int)\[(\d+)\]", r"[0] * \1", line)
        line = re.sub(r"^String (\w+) =", r"\1 =", line)
        if line.startswith("If "):
            condition = re.sub(r"!(?!=)", "not ", line[3:])
            lines.append("    " * indent + "if " + condition + ":")
            indent += 1
        else:
            # A function return terminates the replay, not the unittest.
            line = "raise StopIteration" if line == "Return" else line
            lines.append("    " * indent + line)
    try:
        exec("\n".join(lines), {"__builtins__": {"StopIteration": StopIteration}}, values)
    except StopIteration:
        pass


class DialogStorageTests(unittest.TestCase):
    def test_open_repairs_storage_before_any_provider_callback(self):
        code = body("OpenConfig")
        self.assertLess(code.index("InitializeDialogStorage()"), code.index("SetPage("))
        self.assertLess(code.index("InitializeDialogStorage()"), code.index("OnConfigOpen()"))

    def test_initialization_allocates_all_three_arrays_unconditionally(self):
        prefix = body("InitializeDialogStorage").split("If ", 1)[0]
        for field, kind, count in (("slider", "Float", 5), ("menu", "Int", 2), ("color", "Int", 2)):
            self.assertIn(f"_{field}Params = New {kind}[{count}]", prefix)

    def test_every_request_allocates_after_validation_before_defaults_and_dispatch(self):
        for kind, count, element in (("Slider", 5, "Float"), ("Menu", 2, "Int"), ("Color", 2, "Int")):
            with self.subTest(kind=kind):
                code = body(f"Request{kind}DialogData")
                alloc = code.index(f"_{kind.lower()}Params = New {element}[{count}]")
                self.assertLess(code.index("IsValidPageIndex(a_index)"), alloc)
                self.assertLess(alloc, code.index(f"_{kind.lower()}Params[0]"))
                self.assertLess(alloc, code.index(f"OnOption{kind}Open("))
                self.assertLess(alloc, code.index(f"On{kind}OpenST()"))

    def run_request(self, kind, old, authored, state_based=False, valid=True):
        field = f"_{kind.lower()}Params"
        sent = []
        calls = []
        states = []
        values = {
            "a_index": 10, "_currentPageNum": 3, "_activeOption": -1,
            "_stateOptionMap": ["budget" if state_based else ""] * 128,
            "STATE_DEFAULT": 0, "STATE_SLIDER": 2, "STATE_MENU": 3, "STATE_COLOR": 4,
            "_state": 0, field: old, "JOURNAL_MENU": "Journal Menu",
            "MENU_ROOT": "_root.ConfigPanelFader.configPanel",
            "IsValidPageIndex": lambda index: valid,
            "GetState": lambda: "previous", "GotoState": states.append,
        }

        def callback(option=None):
            calls.append(option)
            self.assertEqual(values["_state"], values[f"STATE_{kind.upper()}"])
            self.assertIsNot(values[field], old)
            if authored is not None:
                values[field][:] = authored

        values[f"OnOption{kind}Open"] = callback
        values[f"On{kind}OpenST"] = callback
        values["UI"] = SimpleNamespace(**{
            "InvokeFloatA" if kind == "Slider" else "InvokeIntA":
                lambda menu, target, args: sent.append((target, list(args)))
        })
        replay(f"Request{kind}DialogData", values)
        if valid:
            self.assertEqual(calls, [None if state_based else 778])
            self.assertEqual(states, ["budget", "previous"] if state_based else [])
            self.assertEqual(values["_state"], 0)
            self.assertEqual(len(sent), 1)
            self.assertTrue(sent[0][0].endswith(f".set{kind}DialogParams"))
        else:
            self.assertEqual(calls, [])
            self.assertEqual(sent, [])
            self.assertIs(values[field], old)
        return sent

    def test_slider_recovers_null_wrong_size_and_stale_buffers(self):
        for old in (None, [], [0], [0, 0, 0, 1, 1], [9] * 8):
            for state_based in (False, True):
                for authored in ([200, 200, 25, 500, 5], [0, 0, -255, 255, 1], [.5, .5, 0, 1, .01]):
                    with self.subTest(old=old, state=state_based, authored=authored):
                        sent = self.run_request("Slider", old, authored, state_based)
                        self.assertEqual(sent[0][1], authored)

    def test_menu_and_colour_callbacks_also_receive_repaired_storage(self):
        for kind, params in (("Menu", [2, 1]), ("Color", [0x80D0FF, 0xFFFFFF])):
            for old in (None, [], [0], [3] * 9):
                for state_based in (False, True):
                    with self.subTest(kind=kind, old=old, state=state_based):
                        self.assertEqual(self.run_request(kind, old, params, state_based)[0][1], params)

    def test_skyui_defaults_remain_when_provider_does_not_override_them(self):
        for kind, defaults in (("Slider", [0, 0, 0, 1, 1]), ("Menu", [-1, -1]), ("Color", [-1, -1])):
            self.assertEqual(self.run_request(kind, None, None)[0][1], defaults)

    def test_invalid_requests_do_not_allocate_or_dispatch(self):
        for kind in ("Slider", "Menu", "Color"):
            self.run_request(kind, None, None, valid=False)

    def test_setters_retain_skyui_array_slot_contract(self):
        for name, assignments in {
            "SetSliderDialogStartValue": ["_sliderParams[0] = a_value"],
            "SetSliderDialogDefaultValue": ["_sliderParams[1] = a_value"],
            "SetSliderDialogRange": ["_sliderParams[2] = a_minValue", "_sliderParams[3] = a_maxValue"],
            "SetSliderDialogInterval": ["_sliderParams[4] = a_value"],
        }.items():
            code = body(name)
            self.assertIn("If _state != STATE_SLIDER", code)
            for assignment in assignments:
                self.assertIn(assignment, code)


if __name__ == "__main__":
    unittest.main()
