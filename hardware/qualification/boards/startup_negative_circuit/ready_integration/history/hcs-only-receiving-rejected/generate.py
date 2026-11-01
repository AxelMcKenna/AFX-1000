"""NF04R READY-only successor. Never edits NF03C or an active PCB route."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent
CHANGES = {
    "U44": {"9": "N19_COMPLETE", "10": "N19_READY", "8": "N19_OUTPUT_QUALIFIED",
            "12": "N12_COMPLETE", "13": "N12_READY", "11": "N12_OUTPUT_QUALIFIED"},
    "U48": {"3": "N19_OUTPUT_QUALIFIED", "4": "NOT_N19_OUTPUT_QUALIFIED",
            "5": "N12_OUTPUT_QUALIFIED", "6": "NOT_N12_OUTPUT_QUALIFIED",
            "9": "NF_NOT_OUTPUT_VALID", "8": "NF_OUTPUT_VALID"},
    "U46": {"9": "NOT_N19_OUTPUT_QUALIFIED", "10": "NOT_N12_OUTPUT_QUALIFIED",
            "8": "NF_NOT_OUTPUT_VALID"},
    "J1": {"30": "NF_OUTPUT_VALID"},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def components():
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    for name, record in manifest.items():
        assert sha(ROOT / "sources" / name) == record["sha256"], name
    parent = json.loads((ROOT / "sources/nf03c-components.json").read_text())
    parts = copy.deepcopy(parent)
    for c in parts:
        for pin in c["pins"]:
            if pin["number"] in CHANGES.get(c["ref"], {}):
                pin["net"] = CHANGES[c["ref"]][pin["number"]]
                if c["ref"] == "J1":
                    assert pin["number"] == "30"
                    pin["name"], pin["kind"] = "NF_OUTPUT_VALID", "passive"
    assert len(parts) == 231
    return parts


def main():
    assert not (ROOT / "handoff.json").exists(), "Create a successor to sealed evidence"
    parts = components()
    generate(ROOT, "NF04R", "negative_startup_ready", parts,
             [(20, 45, "NF04R: NEW READY-only spare-gate wiring. No physical/startup/PCB acceptance."),
              (20, 55, "J1.30 VALID = both COMPLETE AND both protected UV/OV READY. Never gate GLOBAL_MASTER/ARM/START with VALID."),
              (20, 65, "E28 READY receiver/default-low pull-down/Schmitt conditioning and final permission AND remain separate integration work.")],
             (1100, 3450), [(name, round(x / 2.54) * 2.54, 20.32) for name, x in [
                 ("AGND", 20), ("GUARDED_12V_FORCE", 90), ("DIG5_FORCE", 170),
                 ("AUX2V6", 250), ("N19_P03_SRC", 330), ("N12_P03_SRC", 410),
                 ("N19_VIN", 490), ("N12_VIN", 570)]])
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    env = dict(os.environ, KICAD_CONFIG_HOME="/private/tmp/afx-nf04r-kicad-config")
    commands = []
    for args in [[cli, "--version"],
                 [cli, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(out / "netlist.xml"), str(ROOT / "negative_startup_ready.kicad_sch")],
                 [cli, "sch", "erc", "--format", "json", "--output", str(out / "erc.json"), str(ROOT / "negative_startup_ready.kicad_sch")]]:
        run = subprocess.run(args, env=env, text=True, capture_output=True, timeout=120)
        commands.append(dict(command=args, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr))
        assert run.returncode == 0, commands[-1]
    (out / "native-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    actual, pins = netlist(out / "netlist.xml")
    for c in parts:
        for p in c["pins"]:
            if p["net"] is None:
                assert pins[c["ref"]].pop(p["number"]).startswith("unconnected-(")
    expected = {c["ref"]: {p["number"]: p["net"] for p in c["pins"] if p["net"] is not None} for c in parts}
    assert set(actual) == set(expected) and pins == expected
    issues = [v for s in json.loads((out / "erc.json").read_text())["sheets"] for v in s["violations"]]
    counts = {k: sum(v["severity"] == k for v in issues) for k in ["error", "warning"]}
    assert counts == {"error": 0, "warning": 2}, counts
    assert all(v["type"] == "ground_pin_not_ground" for v in issues), issues
    assert {v["items"][0]["description"] for v in issues} == {
        "Symbol U19 Pin 4 [GND1, Power input, Line]",
        "Symbol U24 Pin 4 [GND1, Power input, Line]"}, issues
    report = dict(scope="Native NF-only READY successor; not E28 integration", parts=len(parts),
                  ERC=counts, pin_parity_differences=0, exact_intended_pin_net_changes=CHANGES,
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / "sources/manifest.json", ROOT / "components.json"]},
                  artifact_sha256={str(p.relative_to(ROOT)): sha(p) for p in [ROOT / "negative_startup_ready.kicad_sch", out / "netlist.xml", out / "erc.json", out / "native-commands.json"]},
                  e28_native_integration_implemented=False, PCB_implemented=False,
                  receiving_logic_levels_and_loading_qualified=False, physical_qualified=False,
                  startup_qualified=False, fabrication_released=False)
    (out / "native-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("NF04R:", len(parts), "parts; ERC", counts, "; exact native pin-map parity")


if __name__ == "__main__":
    main()
