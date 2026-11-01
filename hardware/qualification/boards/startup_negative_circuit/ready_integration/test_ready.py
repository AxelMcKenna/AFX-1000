"""Evaluate the actual spare-gate net graph, including protected UV/OV gates."""

import copy
import itertools
import json
import unittest

from .generate import CHANGES, ROOT, components, sha

INPUTS = ["N19_COMPLETE", "N12_COMPLETE", "N19_OUTPUT_UV_GOOD",
          "N19_OUTPUT_OV_GOOD", "N12_OUTPUT_UV_GOOD", "N12_OUTPUT_OV_GOOD"]


def ready(parts, values):
    drivers = {}
    for c in parts:
        pins = {p["number"]: p["net"] for p in c["pins"]}
        if c["part"] in ["SN74HCS08PWR", "SN74HCS32PWR"]:
            for a, b, y in [("1", "2", "3"), ("4", "5", "6"),
                            ("9", "10", "8"), ("12", "13", "11")]:
                if pins[y]:
                    assert pins[y] not in drivers
                    drivers[pins[y]] = ("AND" if "HCS08" in c["part"] else "OR", pins[a], pins[b])
        elif c["part"] == "SN74HCS14PWR":
            for a, y in [("1", "2"), ("3", "4"), ("5", "6"),
                         ("9", "8"), ("11", "10"), ("13", "12")]:
                if pins[y]:
                    assert pins[y] not in drivers
                    drivers[pins[y]] = ("INV", pins[a])
        elif c["part"] == "SN74AUP2G14DCKR":
            for a, y in [("1", "6"), ("3", "4")]:
                assert pins[y] not in drivers
                drivers[pins[y]] = ("INV", pins[a])

    def node(name, visited=frozenset()):
        if name in values:
            return values[name]
        if name == "AGND":
            return False
        if name == "AUX2V6":
            return True
        assert name not in visited, ("Combinational feedback in READY cone", name)
        gate, *inputs = drivers[name]
        v = [node(n, visited | {name}) for n in inputs]
        return not v[0] if gate == "INV" else all(v) if gate == "AND" else any(v)

    connector = next(c for c in parts if c["ref"] == "J1")
    export = next(p["net"] for p in connector["pins"] if p["number"] == "30")
    return node(export)


class Ready(unittest.TestCase):
    def test_all_64_protected_voltage_completion_combinations(self):
        for bits in itertools.product([False, True], repeat=6):
            self.assertEqual(ready(components(), dict(zip(INPUTS, bits))), all(bits), bits)

    def test_active_gates_force_and_startup_pins_unchanged(self):
        parent = json.loads((ROOT / "sources/nf03c-components.json").read_text())
        changed = components()
        for before, after in zip(parent, changed):
            expected = copy.deepcopy(before)
            for p in expected["pins"]:
                if p["number"] in CHANGES.get(before["ref"], {}):
                    p["net"] = CHANGES[before["ref"]][p["number"]]
                    if before["ref"] == "J1":
                        p["name"], p["kind"] = "NF_OUTPUT_VALID", "passive"
            self.assertEqual(after, expected)
        self.assertEqual(len(changed), 233)
        self.assertEqual({c["ref"] for c in changed} - {c["ref"] for c in parent}, {"U49", "C88"})

    def test_parent_is_bound_to_its_sealed_component_inventory(self):
        handoff = json.loads((ROOT / "sources/nf03c-handoff.json").read_text())
        self.assertEqual(sha(ROOT / "sources/nf03c-components.json"), handoff["files_sha256"]["components.json"])

    def test_completion_latch_cannot_hide_a_later_voltage_fault(self):
        values = dict.fromkeys(INPUTS, True)
        self.assertTrue(ready(components(), values))
        for failed in INPUTS:
            fault = dict(values, **{failed: False})
            self.assertFalse(ready(components(), fault), failed)

    def test_wrong_final_inverter_polarity_is_detected(self):
        parts = components()
        inverter = next(c for c in parts if c["ref"] == "U48")
        next(p for p in inverter["pins"] if p["number"] == "9")["net"] = "AGND"
        bad = [bits for bits in itertools.product([False, True], repeat=6)
               if ready(parts, dict(zip(INPUTS, bits))) != all(bits)]
        self.assertEqual(len(bad), 63)


if __name__ == "__main__":
    unittest.main()
