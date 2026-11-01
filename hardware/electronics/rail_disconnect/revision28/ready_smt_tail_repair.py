"""Remove only raw native-proved obsolete F-side J12 signal/return leaf pieces."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/ready-smt-connector2-work"
ORIGINAL = ROOT / "generated/reset-triple-remaining-batch1-work"
WORK = ROOT / "generated/ready-smt-connector3-work"


def main():
    assert not WORK.exists()
    pcb = SOURCE / "rail_disconnect.kicad_pcb"
    blob = pcb.read_bytes()
    t = read_sexpr(blob.decode())
    old = read_sexpr((ORIGINAL / "rail_disconnect.kicad_pcb").read_text())
    report = SOURCE / "generated/drc-ready-smt2.json"
    raw = json.loads(report.read_text())
    receipt = json.loads((SOURCE / "generated/native-ready-smt2.json").read_text())
    assert receipt["pcb_sha256"] == hashlib.sha256(blob).hexdigest()
    original_ids = {str(first(n, "uuid")[1]) for k in ("segment", "via") for n in children(old, k)}
    ids = {
        q["uuid"] for v in raw["violations"] if v["severity"] == "error" for q in v["items"]
    } & original_ids
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    removed = []
    for n in list(t):
        if (
            not isinstance(n, list)
            or not n
            or n[0] not in ("segment", "via")
            or str(first(n, "uuid")[1]) not in ids
        ):
            continue
        net = nets[str(first(n, "net")[1])]
        assert net in {"NF_OUTPUT_VALID_RAW", "AGND"}
        assert n[0] == "segment" and first(n, "layer")[1] == "F.Cu"
        pts = [tuple(map(float, first(n, k)[1:])) for k in ("start", "end")]
        assert min(x for x, y in pts) > 239 and min(y for x, y in pts) >= 147
        # This region has no other actual electrical PAD beyond the replacedJ12.
        for f in children(old, "footprint"):
            ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
            if ref == "J12":
                continue
            from ...output_stage.check_placement import transform

            for pad in children(f, "pad"):
                xy = transform(f, first(pad, "at")[1:3])
                assert not (244 < xy[0] < 248 and 147 < xy[1] < 153), (ref, pad[1], xy)
        removed.append(dict(net=net, literal=sexpr(n)))
        t.remove(n)
    assert removed
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "generated/obsolete-J12-leaf-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                original_pcb_sha256=hashlib.sha256(
                    (ORIGINAL / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                raw_drc_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                removed_native_failed_old_leaf_pieces=removed,
                all_new_physical_barrels_and_mechanical_tabs_preserved=True,
                other_force_quiet_PDN_geometry_unchanged=True,
                physical_and_process_qualification=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(len(removed), "obsolete connectorleafpieces removed; native recheck required")


if __name__ == "__main__":
    main()
