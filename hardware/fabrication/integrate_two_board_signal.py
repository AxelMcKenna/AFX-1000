"""TBI01: source-bound signal schematic and PCB net integration, never a release.

Only the existing AC04 pin schedule authorizes cross-source joins. Source
net partitions are compared against the native export, including every pin.
The independent power inputs remain separate pending the distribution design.
"""
import copy
import csv
import hashlib
import json
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO / "hardware/fabrication/staging"
OUT = STAGING / "two-board-signal-integration-01"
CAD = STAGING / "two-board-placement-cad-03"
SCHEDULE = STAGING / "audio-main-integration-04b/audio-leg-connections.csv"
SOURCES = {
    "A": (STAGING / "audio-main-controls-06", "audio_core", "native-netlist.xml"),
    "D": (STAGING / "digital-led16-closed-native-01", "digital_core", "netlist.xml"),
}
PROJECT = "signal_main"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def uid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "AFX:TBI01:" + s))


def prop(node, name):
    return next(p for p in children(node, "property") if p[1] == name)


def read_netlist(path):
    tree = ET.parse(path)
    parts = {c.attrib["ref"]: c for c in tree.findall("./components/comp")}
    pins = {}
    for net in tree.findall("./nets/net"):
        for n in net.findall("node"):
            pins[(n.attrib["ref"], n.attrib["pin"])] = net.attrib["name"].lstrip("/")
    return parts, pins


def build():
    assert not OUT.exists(), "Keep prior evidence immutable"
    OUT.mkdir()
    paths = {Path(__file__), SCHEDULE, CAD / "library-bundle.json"}
    fpmap = {v["ref"]: v["new"] for v in json.loads((CAD / "library-bundle.json").read_text())["library_identifier_map"]}
    data = {role: read_netlist(folder / nl) for role, (folder, _, nl) in SOURCES.items()}
    joins, aliases = [], {}
    for row in csv.DictReader(SCHEDULE.open()):
        if row["peer_role"] != "digital_core":
            continue
        endpoints = [("A", row["audio_header"], row["audio_pin"]), ("D", row["peer_header"], row["peer_pin"])]
        keys = [(r, data[r][1][(ref, pin)]) for r, ref, pin in endpoints]
        # Reject stale schedule/pin meanings instead of silently joining names.
        assert all(n.split("/")[-1] == row["net"] for _, n in keys), (row, keys)
        new = "LINK_" + row["net"]
        for key in keys:
            assert key not in aliases or aliases[key] == new
            aliases[key] = new
        joins.append(dict(bundle=row["bundle"], endpoints=endpoints, source_nets=keys, integrated_net=new))
    assert len(joins) == 19
    expected = {}
    for role, (parts, pins) in data.items():
        for ref, component in parts.items():
            newref = role + "_" + ref
            expected[newref] = dict(source_role=role, source_ref=ref,
                value=component.findtext("value"), footprint=fpmap.get(newref, component.findtext("footprint") or ""),
                pins={pin: aliases.get((role, net), role + "::" + net)
                      for (r, pin), net in pins.items() if r == ref})
    root_id = uid("root")
    root = read_sexpr(f'''(kicad_sch (version 20250114) (generator afx_tbi01)
      (uuid {root_id}) (paper "A3") (title_block (title "AFX-1000 integrated signal main")
      (rev "TBI01") (comment 1 "Development: unrouted; ESS footprint and mechanical/process approval missing"))
      (lib_symbols) (sheet_instances (path "/" (page "1"))) (embedded_fonts no))''')
    table = read_sexpr('(sym_lib_table (version 7))')
    instances = {}
    page = 2
    for role, (folder, name, nl) in SOURCES.items():
        paths.update([folder / nl, folder / "sym-lib-table", folder / (name + ".kicad_sch")])
        source_root = read_sexpr((folder / (name + ".kicad_sch")).read_text())
        assert not children(source_root, "symbol")
        for lib in children(read_sexpr((folder / "sym-lib-table").read_text()), "lib"):
            lib = copy.deepcopy(lib)
            source = Path(first(lib, "uri")[1].replace("${KIPRJMOD}", str(folder)))
            paths.add(source)
            nickname = "TBI01_" + role + "_" + str(first(lib, "name")[1])
            target = OUT / "symbols" / (nickname + ".kicad_sym")
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            first(lib, "name")[1] = nickname
            first(lib, "uri")[1] = "${KIPRJMOD}/symbols/" + target.name
            table.append(lib)
        for sheet in children(source_root, "sheet"):
            oldsheet = str(prop(sheet, "Sheetname")[2])
            source = folder / str(prop(sheet, "Sheetfile")[2])
            paths.add(source)
            tree = read_sexpr(source.read_text())
            assert not children(tree, "sheet") and not children(tree, "hierarchical_label")
            sid = uid(role + ":" + oldsheet)
            filename = role + "_" + source.name
            for lib in children(first(tree, "lib_symbols"), "symbol"):
                lib[1] = "TBI01_" + role + "_" + str(lib[1])
            for s in children(tree, "symbol"):
                oldref = str(prop(s, "Reference")[2])
                ref = role + "_" + oldref if not oldref.startswith("#") else "#" + role + "_" + oldref[1:]
                prop(s, "Reference")[2] = ref
                first(s, "lib_id")[1] = "TBI01_" + role + "_" + str(first(s, "lib_id")[1])
                if ref in fpmap:
                    prop(s, "Footprint")[2] = fpmap[ref]
                unit = int(first(s, "unit")[1])
                first(s, "instances")[:] = read_sexpr(f'(instances (project "{PROJECT}" (path "/{root_id}/{sid}" (reference "{ref}") (unit {unit}))))')
                instances[ref] = "/" + root_id + "/" + sid + "/" + str(first(s, "uuid")[1])
            for label in children(tree, "label") + children(tree, "global_label"):
                old = str(label[1])
                net = old if label[0] == "global_label" else oldsheet + "/" + old
                if (role, net) in aliases:
                    label[1] = aliases[(role, net)]
                    if label[0] == "label":
                        label[0] = a("global_label")
                        label.insert(2, [a("shape"), a("passive")])
                elif label[0] == "global_label":
                    label[1] = role + "__" + old
            (OUT / filename).write_text(sexpr(tree) + "\n")
            x, y = (25 if role == "A" else 210), 30 + 32 * (page - (2 if role == "A" else 8))
            root.append(read_sexpr(f'''(sheet (at {x} {y}) (size 72 20)
              (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {sid})
              (property "Sheetname" "{role}_{oldsheet}" (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
              (property "Sheetfile" "{filename}" (at {x} {y+21.27} 0) (effects (font (size 1.27 1.27)) (justify left top)))
              (instances (project "{PROJECT}" (path "/{root_id}" (page "{page}")))))'''))
            page += 1
    notes = ["Daisy Seed 3 retained. 19 scheduled header-pin pairs become 16 shared nets.",
             "All original electrical connectors retained pending connector-removal and distribution review.",
             "Analog and digital source 5V inputs remain separate; no implied power/return routing approval.",
             "ESS U201 is present in the schematic but has no approved land pattern or PCB placement.",
             "No fabrication release: power integration, electrical placement, routing, cooling and full fit remain open."]
    for i, note in enumerate(notes):
        root.append(read_sexpr(f'(text {json.dumps(note)} (at 25 {245+7*i} 0) (effects (font (size 1.2 1.2)) (justify left)) (uuid {uid("note"+str(i))}))'))
    (OUT / (PROJECT + ".kicad_sch")).write_text(sexpr(root) + "\n")
    (OUT / "sym-lib-table").write_text(sexpr(table) + "\n")
    for ext in [".kicad_pcb", ".kicad_pro", ".kicad_dru"]:
        p = CAD / (PROJECT + ext)
        paths.add(p)
        shutil.copyfile(p, OUT / p.name)
    for name in ["fp-lib-table"]:
        paths.add(CAD / name)
        shutil.copyfile(CAD / name, OUT / name)
    shutil.copytree(CAD / "libraries", OUT / "libraries")
    paths.update(p for p in (CAD / "libraries").rglob("*") if p.is_file())
    (OUT / "expected-circuit.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    (OUT / "symbol-paths.json").write_text(json.dumps(instances, indent=2) + "\n")
    (OUT / "interface-joins.json").write_text(json.dumps(joins, indent=2) + "\n")
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
                  electrical_parts=len(expected), scheduled_pin_pairs=len(joins),
                  unique_shared_nets=len(set(aliases.values())),
                  all_electrical_connectors_retained=True, native_validation_pending=True,
                  power_board_integrated=False, routing_complete=False, fabrication_released=False)
    assert len(expected) == 467
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "source_sha256"}))


if __name__ == "__main__":
    build()
