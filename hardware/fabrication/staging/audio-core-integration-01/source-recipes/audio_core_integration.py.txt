"""Combine the selected E12-R2/E09/E08 circuits for codec co-location.

Preserves the original symbols and pin types. Only declared interface nets
cross sheets. No codec land is invented, and no PCB or analog approval follows.
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
OUT = ROOT / "staging/audio-core-integration-01"
PROJECT = "audio_core"
SOURCES = {
    "ADC": (ROOT / "staging/adc-driver-native-01", "adc_driver", 100, {"J2"}),
    "CODEC": (REPO / "hardware/electronics/converter", "converter", 200, {"J1", "J2"}),
    "DAC": (ROOT / "staging/dac-receiver-closed-native-01", "dac_receiver", 300, {"J1"}),
}
MAPS = {
    "ADC": {n: n for n in ("AGND", "P12", "N12", "V5_REG", "ADC_LP", "ADC_LN", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2")},
    "CODEC": {n: n for n in ("AGND", "V5_REG", "ADC_LP", "ADC_LN", "ADC_RP", "ADC_RN", "REF_ADC1", "REF_ADC2", "DAC_LP", "DAC_LN", "DAC_RP", "DAC_RN", "CHIP_EN")},
    "DAC": {n: n for n in ("AGND", "P12", "N12", "DAC_LP", "DAC_LN", "DAC_RP", "DAC_RN")},
}
MAPS["ADC"].update({"SENSE_" + n: "ADC_" + n for n in ("LP", "LN", "RP", "RN")})
MAPS["ADC"]["DRV_ENABLE"] = "CHIP_EN"
REMOVE_FLAGS = {"ADC": set(), "CODEC": {"#FLAG1", "#FLAG2"}, "DAC": {"#FLAG0", "#FLAG1", "#FLAG2"}}


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "AFX:audio-core:01:" + name))


def prop(symbol, name):
    return next(p for p in children(symbol, "property") if p[1] == name)


def renamed(ref, domain, base):
    if ref.startswith("#"):
        return "#" + domain + "_" + ref[1:]
    prefix, number = re.fullmatch(r"([A-Z]+)([0-9]+)", ref).groups()
    return prefix + str(int(number) + base)


def point(node):
    return tuple(round(float(x), 4) for x in node[1:3])


def remove_instance(tree, symbol):
    """Remove only a generated header/flag's own terminal stubs and labels."""
    identifier = first(symbol, "lib_id")[1]
    library = next(s for s in children(first(tree, "lib_symbols"), "symbol") if s[1] == identifier)
    unit = str(first(symbol, "unit")[1])
    units = [s for s in children(library, "symbol") if str(s[1]).endswith(("_" + unit + "_1", "_0_1"))]
    pins = [p for s in units for p in children(s, "pin")]
    at = first(symbol, "at")
    assert float(at[3]) == 0
    origin = point(at)
    anchors = {(round(origin[0] + float(first(p, "at")[1]), 4),
                round(origin[1] - float(first(p, "at")[2]), 4)) for p in pins}
    assert anchors, identifier
    wires = [w for w in children(tree, "wire") if anchors & {point(p) for p in children(first(w, "pts"), "xy")}]
    ends = anchors | {point(p) for w in wires for p in children(first(w, "pts"), "xy")}
    removals = [symbol, *wires]
    removals += [n for n in tree if isinstance(n, list) and n and n[0] in ("label", "no_connect") and point(first(n, "at")) in ends]
    for node in removals:
        tree.remove(node)


def source_files():
    paths = [Path(__file__)]
    for folder, name, _, _ in SOURCES.values():
        paths.extend(folder / p for p in (name + ".kicad_sch", "fp-lib-table", "sym-lib-table"))
        paths.append(folder / ("generated/netlist.xml" if name == "converter" else "netlist.xml"))
    paths.extend(REPO / p for p in (
        "hardware/electronics/adc_driver/revision2/integration.json",
        "hardware/electronics/adc_driver/integration.json",
        "hardware/electronics/converter/dependencies.json"))
    return paths


def build():
    assert not OUT.exists(), "Preserve prior integration candidates"
    OUT.mkdir()
    (OUT / "source-recipes").mkdir()
    shutil.copyfile(Path(__file__), OUT / "source-recipes/audio_core_integration.py.txt")
    root_id = uid("root")
    root = read_sexpr(f'''(kicad_sch (version 20250114) (generator afx_audio_integration)
      (uuid {root_id}) (paper "A4")
      (title_block (title "AFX-1000 shared audio core") (rev "AC01")
        (comment 1 "Co-location integration candidate; codec land and physical layout incomplete"))
      (lib_symbols) (sheet_instances (path "/" (page "1"))) (embedded_fonts no))''')
    expected, reference_map, input_paths = {}, {}, source_files()
    sym_table = read_sexpr('(sym_lib_table (version 7))')
    footprint_sources = {}
    for index, (domain, (folder, name, base, removed)) in enumerate(SOURCES.items(), 2):
        original = folder / (name + ".kicad_sch")
        tree = read_sexpr(original.read_text())
        parts, pins = netlist(folder / ("generated/netlist.xml" if name == "converter" else "netlist.xml"))
        sheet_id = uid("sheet:" + domain)
        reference_map[domain] = {ref: renamed(ref, domain, base) for ref in parts}
        remove = removed | REMOVE_FLAGS[domain]
        for s in list(children(tree, "symbol")):
            if prop(s, "Reference")[2] in remove:
                remove_instance(tree, s)
        for s in children(tree, "symbol"):
            old = prop(s, "Reference")[2]
            new = renamed(old, domain, base)
            prop(s, "Reference")[2] = new
            unit = int(first(s, "unit")[1])
            first(s, "instances")[:] = read_sexpr(f'''(instances (project "{PROJECT}"
              (path "/{root_id}/{sheet_id}" (reference "{new}") (unit {unit}))))''')
        for label in children(tree, "label"):
            old = str(label[1])
            if old in MAPS[domain]:
                label[0], label[1] = a("global_label"), MAPS[domain][old]
                label.insert(2, [a("shape"), a("passive")])
        first(tree, "generator")[1] = a("afx_audio_integration")
        for ref in parts.keys() - removed:
            new = reference_map[domain][ref]
            nets = {pin: (None if net.startswith("unconnected-") else MAPS[domain].get(net, domain + "/" + net))
                    for pin, net in pins[ref].items()}
            expected[new] = dict(source_domain=domain, source_ref=ref, value=parts[ref].findtext("value"),
                                 footprint=parts[ref].findtext("footprint") or "", pins=nets)
        target = OUT / (domain.lower() + ".kicad_sch")
        target.write_text(sexpr(tree) + "\n")
        y = 35 + 43 * (index - 2)
        root.append(read_sexpr(f'''(sheet (at 30 {y}) (size 72 24)
          (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {sheet_id})
          (property "Sheetname" "{domain}" (at 30 {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
          (property "Sheetfile" "{target.name}" (at 30 {y+25.27} 0) (effects (font (size 1.27 1.27)) (justify left top)))
          (instances (project "{PROJECT}" (path "/{root_id}" (page "{index}")))))'''))
        for library in children(read_sexpr((folder / "sym-lib-table").read_text()), "lib"):
            library = copy.deepcopy(library)
            uri = first(library, "uri")[1].replace("${KIPRJMOD}", str(folder))
            original_library = Path(uri)
            assert original_library.is_file()
            input_paths.append(original_library)
            target_library = OUT / original_library.name
            assert not target_library.exists()
            shutil.copyfile(original_library, target_library)
            first(library, "uri")[1] = "${KIPRJMOD}/" + original_library.name
            sym_table.append(library)
        for lib in children(read_sexpr((folder / "fp-lib-table").read_text()), "lib"):
            nick = first(lib, "name")[1]
            footprint_sources.setdefault(nick, []).append(first(lib, "uri")[1].replace("${KIPRJMOD}", str(folder)))
    assert len(expected) == 210
    notes = [
        "Single physical audio PCB target: ADC driver + codec + DAC I/V/receiver.",
        "Only declared globals connect sheets. Four prototype analog headers removed.",
        "Force and sense must meet at actual ESS input pads; logical joining is not physical proof.",
        "CHIP_EN/driver-enable timing retains original interface; reference/partial-power qualification is open.",
        "ESS footprint deliberately absent. No generic QFN substitution; not ready for fabrication.",
    ]
    for i, note in enumerate(notes):
        root.append(read_sexpr(f'(text {json.dumps(note)} (at 112 {40+12*i} 0) (effects (font (size 1 1)) (justify left)) (uuid {uid("note"+str(i))}))'))
    (OUT / (PROJECT + ".kicad_sch")).write_text(sexpr(root) + "\n")
    (OUT / "sym-lib-table").write_text(sexpr(sym_table) + "\n")
    profile = dict(meta=dict(filename=PROJECT + ".kicad_pro", version=1),
                   erc=dict(rule_severities={n: "error" for n in
                       ("single_global_label", "four_way_junction", "simulation_model_issue", "footprint_filter")}))
    (OUT / (PROJECT + ".kicad_pro")).write_text(json.dumps(profile, indent=2) + "\n")
    (OUT / "expected-circuit.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in input_paths},
        reference_map=reference_map, cross_sheet_net_maps=MAPS,
        removed_analog_boundary_headers={d: sorted(v[3]) for d, v in SOURCES.items()},
        duplicate_external_power_flags_removed={d: sorted(v) for d, v in REMOVE_FLAGS.items()},
        footprint_library_sources=footprint_sources, electrical_parts=210,
        original_parts_values_and_pin_types_preserved_except_declared_boundary_removals=True,
        actual_ADC_pad_star_geometry_verified=False, codec_footprint_assigned=False,
        driver_enable_reference_timing_qualified=False, raw_DAC_scale_resolved=False,
        physical_partition_and_housing_receiving_complete=False, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Combined210 parts on three sheets; four raw-analog headers removed; native export/ERC pending")


def review():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    record = json.loads((OUT / "construction.json").read_text())
    assert all(sha(REPO / p) == digest for p, digest in record["source_sha256"].items())
    assert not (OUT / "native-review.json").exists()
    libraries = OUT / "libraries"
    libraries.mkdir(exist_ok=False)
    expected = json.loads((OUT / "expected-circuit.json").read_text())
    fp_table = read_sexpr('(fp_lib_table (version 7))')
    library_sources = {}
    for nick in sorted({p["footprint"].split(":")[0] for p in expected.values() if p["footprint"]}):
        destination = libraries / (nick + ".pretty")
        destination.mkdir()
        names = {p["footprint"].split(":")[1] for p in expected.values() if p["footprint"].startswith(nick + ":")}
        for name in names:
            choices = [Path(uri.replace("${KICAD10_FOOTPRINT_DIR}", os.environ["KICAD10_FOOTPRINT_DIR"])) / (name + ".kicad_mod")
                       for uri in record["footprint_library_sources"][nick]]
            choices = [p for p in choices if p.is_file()]
            assert choices, (nick, name)
            assert len({sha(p) for p in choices}) == 1, "Different same-name library lands require reconciliation"
            source = choices[0]
            library_sources.update({str(p): sha(p) for p in choices})
            shutil.copyfile(source, destination / source.name)
        fp_table.append(read_sexpr(f'(lib (name "{nick}") (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{destination.name}") (options "") (descr "Captured used source lands"))'))
    (OUT / "fp-lib-table").write_text(sexpr(fp_table) + "\n")
    inputs = [p for p in OUT.iterdir() if p.is_file() and p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_pro", ".json")]
    inputs += [OUT / "sym-lib-table", OUT / "fp-lib-table"]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    commands = []
    for label, options in (
        ("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "--output", str(OUT / "netlist.xml")]),
        ("erc", ["sch", "erc", "--severity-all", "--format", "json", "--output", str(OUT / "erc.json")]),
    ):
        command = ["kicad-cli", *options, str(OUT / (PROJECT + ".kicad_sch"))]
        p = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (OUT / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append(dict(command=command, returncode=p.returncode))
        assert p.returncode == 0, (label, p.stdout, p.stderr)
    erc = json.loads((OUT / "erc.json").read_text())
    violations = [v for sheet in erc["sheets"] for v in sheet["violations"]]
    assert erc["ignored_checks"] == [], "Every native ERC category must remain enabled"
    assert all(sha(REPO / p) == digest for p, digest in hashes.items())
    proof = dict(source_sha256=hashes, captured_library_source_sha256=library_sources,
        captured_library_sha256={str(p.relative_to(OUT)): sha(p) for p in libraries.rglob("*.kicad_mod")},
        native_version=erc["kicad_version"], complete_native_commands=commands,
        ERC_findings=len(violations), ERC_ignored_checks=erc["ignored_checks"],
        raw_export_sha256={n: sha(OUT / n) for n in ("netlist.xml", "erc.json")},
        PCB_DRC_performed=False, PCB_layout_present=False, fabrication_released=False)
    (OUT / "native-review.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("Native shared-core export complete; ERC findings", len(violations), "; no PCB/physical approval")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "review"))
    args = parser.parse_args()
    (build if args.action == "build" else review)()
