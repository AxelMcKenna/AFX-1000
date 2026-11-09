"""TBP01: combine six power circuits with explicitly reconciled interfaces.

This first circuit composition retains unresolved NF ports as explicit ports.
No protective stage is bypassed and no physical routing is inherited.
"""
import copy
import json
import shutil
import uuid
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, CAD, prop, read_netlist, sha

OUT = STAGING / "two-board-power-integration-01"
PROJECT = "power_protection"
CAPTURE = STAGING / "two-board-placement-05/capture.json"
CONTRACT = STAGING / "two-board-power-interface-audit-01/interface-review.json"
ROLES = dict(P="power_supply", I="input_protection", E="rail_disconnect", M="rail_monitor",
             N="negative_startup_protection", F="fan_health_protection")


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "AFX:TBP01:" + name))


def build():
    assert not OUT.exists(), "Create successors rather than rewriting evidence"
    cap, contract = [json.loads(p.read_text()) for p in [CAPTURE, CONTRACT]]
    for name, digest in contract["source_sha256"].items():
        assert sha(REPO / name) == digest, name
    paths = {Path(__file__), CAPTURE, CONTRACT, CAD / "library-bundle.json",
             REPO / "hardware/qualification/boards/fan_health/composite/README.md"}
    sources, data = {}, {}
    for role, key in ROLES.items():
        pcb = REPO / cap["sources"][key]["path"]
        assert sha(pcb) == cap["sources"][key]["sha256"]
        sources[role] = pcb.with_suffix(".kicad_sch")
        data[role] = read_netlist(pcb.parent / "netlist.xml")
        paths.update([pcb, pcb.with_suffix(".kicad_sch"), pcb.parent / "netlist.xml", pcb.parent / "sym-lib-table"])
    parent = {}

    def root(key):
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = root(parent[key])
        return parent[key]

    for row in contract["proposed_interfaces"]:
        keys = []
        for endpoint, name in zip(row["endpoints"], row["actual_source_nets"]):
            role, ref, pin = endpoint
            assert data[role][1][(ref, pin)] == name
            keys.append((role, name))
        parent[root(keys[1])] = root(keys[0])
    groups = defaultdict(set)
    for key in list(parent):
        groups[root(key)].add(key)
    special = {
        frozenset(["AGND", "GND"]): "AGND",
        frozenset(["5V_DIG_SRC", "FAN5V_IN"]): "5V_DIG_SRC",
        frozenset(["N19_SRC", "N19_P03_SRC"]): "N19_SOURCE",
        frozenset(["N12_SRC", "N12_P03_SRC"]): "N12_SOURCE",
        frozenset(["N19_SRC", "N19_E28_SRC"]): "N19_POST_NF",
        frozenset(["N12_SRC", "N12_E28_SRC"]): "N12_POST_NF",
        frozenset(["NF_RAW5", "DIG5_FORCE"]): "NF_RAW5",
        frozenset(["POWER_RUN_E28_LEAF", "P03_POWER_RUN"]): "RUN_BEFORE_FAN",
        frozenset(["E28_POWER_RUN", "POWER_RUN"]): "RUN_AFTER_FAN",
        frozenset(["P03_ALL_SOURCES_READY", "P03_SOURCES_READY"]): "P03_SOURCES_READY",
        frozenset(["NF_OUTPUT_VALID", "NF_OUTPUT_VALID_RAW"]): "NF_OUTPUT_VALID",
    }
    aliases, joins = {}, []
    for members in sorted(groups.values(), key=lambda g: sorted(g)):
        names = frozenset(n for _, n in members)
        assert len(names) == 1 or names in special, names
        name = "PWR_" + (next(iter(names)) if len(names) == 1 else special[names])
        assert name not in aliases.values(), (name, members)
        for key in members:
            aliases[key] = name
        joins.append(dict(integrated_net=name, source_nets=sorted(members)))
    forbidden = contract["forbidden_direct_net_joins"]
    for left, right in forbidden:
        assert aliases.get(tuple(left), "::".join(left)) != aliases.get(tuple(right), "::".join(right))
    OUT.mkdir()
    fpmap = {x["ref"]: x["new"] for x in json.loads((CAD / "library-bundle.json").read_text())["library_identifier_map"]}
    expected, instances = {}, {}
    root_id = uid("root")
    tree = read_sexpr(f'''(kicad_sch (version 20250114) (generator afx_tbp01)
      (uuid {root_id}) (paper "A3") (title_block (title "AFX-1000 integrated power/protection development")
      (rev "TBP01") (comment 1 "Unrouted; unresolved NF control/aux/clamp ports; not for fabrication"))
      (lib_symbols) (sheet_instances (path "/" (page "1"))) (embedded_fonts no))''')
    table = read_sexpr('(sym_lib_table (version 7))')
    for page, (role, source) in enumerate(sources.items(), 2):
        folder = source.parent
        sheet = read_sexpr(source.read_text())
        assert not children(sheet, "sheet") and not children(sheet, "hierarchical_label")
        assert not children(sheet, "global_label"), "Current six sources are flat label-only circuits"
        sid = uid(role + ":sheet")
        filename = role + "_" + source.name
        for library in children(first(sheet, "lib_symbols"), "symbol"):
            library[1] = "TBP01_" + role + "_" + str(library[1])
        for symbol in children(sheet, "symbol"):
            oldref = str(prop(symbol, "Reference")[2])
            ref = role + "_" + oldref if not oldref.startswith("#") else "#" + role + "_" + oldref[1:]
            prop(symbol, "Reference")[2] = ref
            first(symbol, "lib_id")[1] = "TBP01_" + role + "_" + str(first(symbol, "lib_id")[1])
            if ref in fpmap:
                prop(symbol, "Footprint")[2] = fpmap[ref]
            unit = int(first(symbol, "unit")[1])
            first(symbol, "instances")[:] = read_sexpr(f'(instances (project "{PROJECT}" (path "/{root_id}/{sid}" (reference "{ref}") (unit {unit}))))')
            instances[ref] = "/" + root_id + "/" + sid + "/" + str(first(symbol, "uuid")[1])
        for label in children(sheet, "label"):
            key = (role, str(label[1]))
            if key in aliases:
                label[1] = aliases[key]
                label[0] = a("global_label")
                label.insert(2, [a("shape"), a("passive")])
        (OUT / filename).write_text(sexpr(sheet) + "\n")
        x, y = 25 + 180 * ((page-2)//3), 30 + 60 * ((page-2)%3)
        tree.append(read_sexpr(f'''(sheet (at {x} {y}) (size 140 28)
          (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {sid})
          (property "Sheetname" "{role}_{ROLES[role]}" (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
          (property "Sheetfile" "{filename}" (at {x} {y+29.27} 0) (effects (font (size 1.27 1.27)) (justify left top)))
          (instances (project "{PROJECT}" (path "/{root_id}" (page "{page}")))))'''))
        for lib in children(read_sexpr((folder / "sym-lib-table").read_text()), "lib"):
            lib = copy.deepcopy(lib)
            path = Path(first(lib, "uri")[1].replace("${KIPRJMOD}", str(folder)))
            assert path.is_file()
            paths.add(path)
            nick = "TBP01_" + role + "_" + str(first(lib, "name")[1])
            target = OUT / "symbols" / (nick + ".kicad_sym")
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, target)
            first(lib, "name")[1] = nick
            first(lib, "uri")[1] = "${KIPRJMOD}/symbols/" + target.name
            table.append(lib)
        parts, pins = data[role]
        for ref, part in parts.items():
            newref = role + "_" + ref
            expected[newref] = dict(source_role=role, source_ref=ref,
                value=part.findtext("value"), footprint=fpmap.get(newref,part.findtext("footprint") or ""),
                pins={pin: aliases.get((role,n), role+"::"+n) for (r,pin),n in pins.items() if r == ref})
    notes = [
        "30 reviewed pin pairs are joined; original power/protection components and connectors remain.",
        "Negative rails pass through NF. NF raw5 uses FPC protection. Fan health interrupts E28 RUN.",
        "NF module return remains separate. GLOBAL_MASTER is not E28_MASTER_ENABLE.",
        "NF buffer/clamp/fault/sense/auxiliary and module-input wiring are still unresolved design ports.",
        "No routed power layout, qualified stack, cooling/support design or full installed-fit release exists."]
    for i, note in enumerate(notes):
        tree.append(read_sexpr(f'(text {json.dumps(note)} (at 25 {220+9*i} 0) (effects (font (size 1.2 1.2)) (justify left)) (uuid {uid("note"+str(i))}))'))
    (OUT / (PROJECT+".kicad_sch")).write_text(sexpr(tree)+"\n")
    (OUT / "sym-lib-table").write_text(sexpr(table)+"\n")
    for name in [PROJECT+ext for ext in [".kicad_pcb",".kicad_pro",".kicad_dru"]] + ["fp-lib-table"]:
        paths.add(CAD/name)
        shutil.copyfile(CAD/name,OUT/name)
    shutil.copytree(CAD/"libraries",OUT/"libraries")
    paths.update(p for p in (CAD/"libraries").rglob("*") if p.is_file())
    assert len(expected) == 1077
    for name, value in [("expected-circuit.json",expected),("symbol-paths.json",instances),("interface-joins.json",joins)]:
        (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    record = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(paths)},
        electrical_parts=len(expected), source_pin_entries=sum(len(p["pins"]) for p in expected.values()),
        scheduled_pin_pairs=30, unique_shared_nets=len(joins), source_net_merges=sum(len(g)-1 for g in groups.values()),
        forbidden_direct_net_joins=forbidden, unresolved_design_holds=contract["unresolved_design_holds"],
        all_electrical_components_and_connectors_retained=True, native_validation_pending=True,
        complete_power_circuit=False, electrical_placement_qualified=False, routing_complete=False, fabrication_released=False)
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:record[k] for k in ["electrical_parts","source_pin_entries","scheduled_pin_pairs","unique_shared_nets","source_net_merges"]}))


if __name__ == "__main__":
    build()
