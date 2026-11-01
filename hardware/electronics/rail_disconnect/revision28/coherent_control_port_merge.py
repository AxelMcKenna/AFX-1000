"""Deliberately combine reviewed U31 and SMT-port changes without duplicate ground routes."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "generated/reset-triple-remaining-batch1-work"
LOGIC = ROOT / "generated/u31-front-edge-repair2-work"
PORT = ROOT / "generated/ready-smt-reconnect-work"
WORK = ROOT / "generated/coherent-control-smt-work"


def objects(t):
    return {str(first(n, "uuid")[1]): n for kind in ("segment", "via") for n in children(t, kind)}


def footprints(t):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(t, "footprint")
    }


def check_native(folder, label):
    src = folder / "rail_disconnect.kicad_pcb"
    r = json.loads((folder / "generated" / ("native-" + label + ".json")).read_text())
    assert r["pcb_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    raw = json.loads((folder / "generated" / ("drc-" + label + ".json")).read_text())
    assert not any(v["severity"] == "error" for v in raw["violations"])
    assert not raw["schematic_parity"]
    assert r["counts"]["erc"] == 0
    return len(raw["unconnected_items"])


def main():
    assert not WORK.exists()
    counts = {
        str(LOGIC): check_native(LOGIC, "u31-edge-repair2"),
        str(PORT): check_native(PORT, "ready-smt-reconnect"),
    }
    b, l, p = [
        read_sexpr((folder / "rail_disconnect.kicad_pcb").read_text()) for folder in (BASE, LOGIC, PORT)
    ]

    def static(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ("footprint", "segment", "via"))]

    assert static(b) == static(l) == static(p), (
        "Outline, zones, stack, rules and net declarations must remain exact"
    )
    bf, lf, pf = map(footprints, (b, l, p))
    assert set(bf) == set(lf) == set(pf)
    assert {r for r in bf if bf[r] != lf[r]} == {"U31", "C76"}
    assert {r for r in bf if bf[r] != pf[r]} == {"J12"}
    bo, lo, po = map(objects, (b, l, p))
    removed = set(bo) - set(po)
    assert not (removed & (set(bo) - set(lo)))
    for ident in removed:
        assert lo[ident] == bo[ident]
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(p, "net")}
    added = []
    excluded = []
    for ident, node in po.items():
        if ident in bo:
            continue
        net = names[str(first(node, "net")[1])]
        pts = [
            tuple(map(float, first(node, k)[1:])) for k in (("at",) if node[0] == "via" else ("start", "end"))
        ]
        use = net == "NF_OUTPUT_VALID_RAW" or (
            net == "AGND" and min(x for x, y in pts) >= 239 and min(y for x, y in pts) >= 145
        )
        assert net in {"NF_OUTPUT_VALID_RAW", "AGND"}
        if use:
            assert ident not in lo
            added.append(copy.deepcopy(node))
        else:
            excluded.append(sexpr(node))
    assert len(added) > 2
    # Both studies also repaired the same old ground islands. Keep the logic
    # study's current set; import only the port-local low-current return branch.
    l[:] = [
        n
        for n in l
        if not (
            isinstance(n, list) and n and n[0] in ("segment", "via") and str(first(n, "uuid")[1]) in removed
        )
    ]
    lf["J12"][:] = copy.deepcopy(pf["J12"])
    l.extend(added)
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in LOGIC.iterdir():
        if path.is_file() and (
            path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or path.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    for path in PORT.iterdir():
        if path.is_file() and (path.suffix in (".kicad_sch", ".kicad_sym") or path.name == "components.json"):
            shutil.copy2(path, WORK / path.name)
    for path in (PORT / "RMX_E28.pretty").glob("JST_B2B_PH_SM4_TB_MechanicalLands.kicad_mod"):
        shutil.copy2(path, WORK / "RMX_E28.pretty" / path.name)
    shutil.copy2(PORT / "generated/bom.csv", WORK / "generated/bom.csv") if (
        PORT / "generated/bom.csv"
    ).exists() else None
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(l) + "\n")
    paths = [
        folder / name
        for folder in (BASE, LOGIC, PORT)
        for name in ("rail_disconnect.kicad_pcb", "rail_disconnect.kicad_sch", "components.json")
    ]
    result = dict(
        input_sha256={str(q): hashlib.sha256(q.read_bytes()).hexdigest() for q in paths},
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_native_opens=counts,
        exact_changed_footprints=["U31", "C76", "J12"],
        port_removed_old_leaf_literals=[sexpr(bo[i]) for i in sorted(removed)],
        imported_port_copper_literals=[sexpr(n) for n in added],
        excluded_duplicate_purpose_remote_ground_stitch_literals=excluded,
        all_original_outline_rules_stack_zone_primitives_and_force_axes_preserved=True,
        all_native_and_PDN_MCAD_and_connector_loading_checks_must_be_fresh=True,
        qualified=False,
    )
    (WORK / "generated/coherent-merge.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Coherent draft written:",
        len(removed),
        "old port pieces removed;",
        len(added),
        "real port copper objects imported;",
        len(excluded),
        "remote ground objects excluded",
    )


if __name__ == "__main__":
    main()
