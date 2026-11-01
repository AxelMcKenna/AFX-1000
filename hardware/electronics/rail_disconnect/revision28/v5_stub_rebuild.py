"""Rebuild a real missing control-wire stub, checking every track and drill anew."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .focused import legal_line, legal_via
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/v5-backbone-recut-work"
ORIGINAL = ROOT / "generated/coherent-ground-repair-work"
WORK = ROOT / "generated/v5-stub-rebuild-work"


def ident(n):
    return str(first(n, "uuid")[1])


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    blob = path.read_bytes()
    t = read_sexpr(blob.decode())
    gpath = ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json"
    g = json.loads(gpath.read_text())["rows"]["V5_REG_OV_OK"]
    cutp = ROOT / "generated/schmitt-cone-proposal/v5-insertion-cut.json"
    plan = json.loads(cutp.read_text())["plan"]
    recut = json.loads((SOURCE / "generated/V5-physical-recut.json").read_text())
    oldplan = json.loads((ROOT / "generated/schmitt-cone-proposal/backbone-cut-plan.json").read_text())[
        "rows"
    ]["V5_REG_OV_OK"]
    present = {ident(n) for k in ("segment", "via") for n in children(t, k)}
    old = {
        ident(n): n
        for k in ("segment", "via")
        for n in children(read_sexpr((ORIGINAL / "rail_disconnect.kicad_pcb").read_text()), k)
    }
    wanted = (
        set(oldplan["buffered_item_uuids"])
        - set(recut["buffered_original_item_uuids"])
        - set(recut["expanded_ordinary_cut_track_uuids"])
    )
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    code = next(k for k, v in names.items() if v == "V5_REG_OV_OK")
    rt = Router(t)
    accepted = []
    rejected = []
    # This source-level audit explicitly rejects treating a removed historical
    # barrel as an already-existing powered terminal. Rebuilding is new Cu.
    absent_anchors = set(plan["real_upstream_copper_anchor_uuids"]) - present
    assert absent_anchors
    (SOURCE / "generated/current-anchor-audit.json").write_text(
        json.dumps(
            dict(
                status="REJECTED_AS_ALREADY_EXISTING_COPPER_REUSE",
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                historical_anchor_absent_from_actual_source=sorted(absent_anchors),
                missing_historical_copper_count=len(
                    recut["previously_absent_original_objects_not_resurrected"]
                ),
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    candidates = [u for u in wanted - present if g["nodes"][u]["kind"] != "PAD"]
    candidates.sort(key=lambda u: (old[u][0] != "via", u))
    for uid in candidates:
        n = read_sexpr(sexpr(old[uid]))
        first(n, "net")[1] = a(code)
        if n[0] == "via":
            q = tuple(float(v) - 100 for v in first(n, "at")[1:3])
            ok = legal_via(rt, "V5_REG_OV_OK", q)
        else:
            p, q = [tuple(float(v) - 100 for v in first(n, k)[1:3]) for k in ("start", "end")]
            z = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu").index(str(first(n, "layer")[1]))
            ok = legal_line(rt, "V5_REG_OV_OK", z, p, q, float(first(n, "width")[1]))
        if not ok:
            rejected.append(
                dict(
                    uuid=uid,
                    historical_object=sexpr(n),
                    reason="new source foreign pad/track/drill reservation fails exact planning clearance",
                )
            )
            continue
        t.append(n)
        accepted.append(dict(uuid=uid, reintroduced_historical_object_as_NEW_Cu=sexpr(n)))
        rt = Router(t)
    assert set(plan["real_upstream_copper_anchor_uuids"]) <= {ident(n) for n in children(t, "via")}, (
        "Physical upstream barrel must actually be rebuilt"
    )
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for f in SOURCE.iterdir():
        if f.is_file() and (
            f.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or f.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(f, WORK / f.name)
        elif f.suffix == ".pretty":
            shutil.copytree(f, WORK / f.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "generated/actual-stub-rebuild.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                historical_original_sha256=hashlib.sha256(
                    (ORIGINAL / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                native_graph_sha256=hashlib.sha256(gpath.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                accepted_new_real_objects=accepted,
                rejected_historical_objects=rejected,
                new_drill_count=sum(old[r["uuid"]][0] == "via" for r in accepted),
                actual_upstream_anchor_now_physically_present=plan["real_upstream_copper_anchor_uuids"],
                upstream_still_NOT_assumed_connected_to_real_source=True,
                all_original_parts_ports_vias_force_quiet_timing_and_ground_primitives_preserved=True,
                new_drills_and_raw_wire_capacitance_must_be_physically_qualified=False,
                native_all_source_stub_input_and_output_receiver_connections_required=True,
                new_fill_and_full_PDN_extraction_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "New physicalstubobjects",
        len(accepted),
        "rejected",
        len(rejected),
        "newdrills",
        sum(old[r["uuid"]][0] == "via" for r in accepted),
        flush=True,
    )


if __name__ == "__main__":
    main()
