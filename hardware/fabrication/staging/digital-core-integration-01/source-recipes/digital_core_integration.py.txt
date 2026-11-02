"""DC01: co-locate the processor, control expanders and LED drivers.

This preserves the selected circuits and replaces five inter-board headers
with explicit shared nets. Mac CAD is never loaded. Native review runs only
inside the isolated Linux KiCad environment.
"""

import argparse
import copy
import json
import shutil
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication import audio_core_integration as common
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO / "hardware/fabrication/staging"
OUT = STAGING / "digital-core-integration-01"
PROJECT = "digital_core"
SOURCES = {
    "PROCESSOR": ("processor-carrier-native-01", "processor_carrier", 1000, {"J2", "J11"}),
    "CONTROLS": ("control-inputs-native-01", "control_inputs", 2000, {"J4", "J5"}),
    "LED": ("led-driver-native-01", "led_driver", 3000, {"J1"}),
}
SHARED = {
    "AGND", "V3V3_IO", "5V_DIG", "SCL", "SDA", "CODEC_RUN",
    "BYPASS_SENSE", "MODE_SEND_RETURN", "ANALOG_OK", "INPUT_READY",
    "LED_MOSI", "LED_SCK", "LED_XLAT", "LED_BLANK",
}
MAPS = {domain: {n: n for n in SHARED} for domain in SOURCES}
MAPS["CONTROLS"].update(CONTROL_RESET_N="CODEC_RUN", MANUAL_BYPASS="BYPASS_SENSE")


def build():
    assert not OUT.exists(), "Preserve earlier construction and review evidence"
    OUT.mkdir()
    root_id = common.uid("DC01:root")
    root = read_sexpr(f'''(kicad_sch (version 20250114) (generator afx_digital_integration)
      (uuid {root_id}) (paper "A4")
      (title_block (title "AFX-1000 combined digital/control PCB") (rev "DC01")
       (comment 1 "Development integration; physical layout and receiving incomplete"))
      (lib_symbols) (sheet_instances (path "/" (page "1"))) (embedded_fonts no))''')
    expected, reference_map, footprint_sources = {}, {}, {}
    paths = [Path(__file__), REPO / "hardware/electronics/control_inputs/integration.json",
             REPO / "hardware/fabrication/audio_core_integration.py"]
    sym_table = read_sexpr('(sym_lib_table (version 7))')
    for index, (domain, (folder_name, name, base, removed)) in enumerate(SOURCES.items(), 2):
        folder = STAGING / folder_name
        paths.extend(folder / p for p in (name + ".kicad_sch", name + ".kicad_pcb", "netlist.xml", "review.json", "fp-lib-table", "sym-lib-table"))
        tree = read_sexpr((folder / (name + ".kicad_sch")).read_text())
        parts, pins = netlist(folder / "netlist.xml")
        sheet_id = common.uid("DC01:sheet:" + domain)
        reference_map[domain] = {ref: common.renamed(ref, domain, base) for ref in parts}
        for symbol in list(children(tree, "symbol")):
            ref = common.prop(symbol, "Reference")[2]
            if ref in removed or (domain != "PROCESSOR" and ref.startswith("#")):
                common.remove_instance(tree, symbol)
        for symbol in children(tree, "symbol"):
            ref = common.prop(symbol, "Reference")[2]
            new = common.renamed(ref, domain, base)
            common.prop(symbol, "Reference")[2] = new
            unit = int(first(symbol, "unit")[1])
            first(symbol, "instances")[:] = read_sexpr(f'''(instances (project "{PROJECT}"
              (path "/{root_id}/{sheet_id}" (reference "{new}") (unit {unit}))))''')
        for label in children(tree, "label"):
            old = str(label[1])
            if old in MAPS[domain]:
                label[0], label[1] = a("global_label"), MAPS[domain][old]
                label.insert(2, [a("shape"), a("passive")])
        for ref in parts.keys() - removed:
            expected[reference_map[domain][ref]] = dict(
                source_domain=domain, source_ref=ref, value=parts[ref].findtext("value"),
                footprint=parts[ref].findtext("footprint") or "",
                pins={pin: (None if net.startswith("unconnected-") else MAPS[domain].get(net, domain + "/" + net))
                      for pin, net in pins[ref].items()})
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
            original = Path(first(library, "uri")[1].replace("${KIPRJMOD}", str(folder)))
            paths.append(original)
            target_lib = OUT / original.name
            assert not target_lib.exists()
            shutil.copyfile(original, target_lib)
            first(library, "uri")[1] = "${KIPRJMOD}/" + original.name
            sym_table.append(library)
        for lib in children(read_sexpr((folder / "fp-lib-table").read_text()), "lib"):
            footprint_sources.setdefault(first(lib, "name")[1], []).append(
                first(lib, "uri")[1].replace("${KIPRJMOD}", str(folder)))
    assert len(expected) == 138
    notes = [
        "One proposed PCB: Seed processor carrier + 3 control expanders + 96 LED sink channels.",
        "Five headers removed; original component values, lands and signal conditioning retained.",
        "CONTROL_RESET_N joins CODEC_RUN, per E18 external-codec profile (Seed D0).",
        "Manual bypass status joins BYPASS_SENSE; no isolated or power reference is renamed.",
        "Placement, routing, power/return/thermal and complete-unit receiving remain unfinished.",
    ]
    for i, note in enumerate(notes):
        root.append(read_sexpr(f'(text {json.dumps(note)} (at 112 {40+12*i} 0) (effects (font (size 1 1)) (justify left)) (uuid {common.uid("DC01:note:"+str(i))}))'))
    (OUT / (PROJECT + ".kicad_sch")).write_text(sexpr(root) + "\n")
    (OUT / "sym-lib-table").write_text(sexpr(sym_table) + "\n")
    (OUT / (PROJECT + ".kicad_pro")).write_text(json.dumps(dict(
        meta=dict(filename=PROJECT + ".kicad_pro", version=1),
        erc=dict(rule_severities={n: "error" for n in
                 ("single_global_label", "four_way_junction", "simulation_model_issue", "footprint_filter")})), indent=2) + "\n")
    (OUT / "expected-circuit.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    record = dict(
        revision="DC01", source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        reference_map=reference_map, cross_sheet_net_maps=MAPS,
        removed_headers={d: sorted(v[3]) for d, v in SOURCES.items()},
        footprint_library_sources=footprint_sources, electrical_parts=138,
        duplicate_power_flags_removed=["CONTROLS:#FLAG0", "CONTROLS:#FLAG1", "LED:#FLAG0", "LED:#FLAG1", "LED:#FLAG2"],
        physical_layout_complete=False, manufacturing_process_accepted=False,
        integrated_power_return_thermal_and_harness_qualified=False, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    (OUT / "source-recipes").mkdir()
    shutil.copyfile(Path(__file__), OUT / "source-recipes/digital_core_integration.py.txt")
    print("DC01 built: 138 parts; native export/ERC pending")


def review():
    common.OUT, common.PROJECT = OUT, PROJECT
    common.review()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "review"))
    args = parser.parse_args()
    (build if args.action == "build" else review)()
