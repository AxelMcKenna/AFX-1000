"""Move only new U36/C79 off the fixed quiet-via fanout cage; preserve two new barrels."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-receiver-two-drill-work"
ORIGINAL = ROOT / "generated/coherent-ground-repair-work"
GROUND_BASE = ROOT / "generated/schmitt-all-oc-reconnect1-work"
WORK = ROOT / "generated/schmitt-receiver-translation-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    old = read_sexpr((ORIGINAL / "rail_disconnect.kicad_pcb").read_text())
    base = read_sexpr((GROUND_BASE / "rail_disconnect.kicad_pcb").read_text())
    oldids = {str(first(n, "uuid")[1]) for k in ("segment", "via") for n in children(old, k)}
    groundids = {str(first(n, "uuid")[1]) for k in ("segment", "via") for n in children(base, k)}
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    signals = {
        "P19_OV_OK",
        "N19_OV_OK",
        "P12_OV_OK",
        "P19_OV_OK_SCHMITT",
        "N19_OV_OK_SCHMITT",
        "P12_OV_OK_SCHMITT",
    }
    removed = []
    for n in list(t):
        if not isinstance(n, list) or not n or n[0] not in ("segment", "via"):
            continue
        uid = str(first(n, "uuid")[1])
        net = names[str(first(n, "net")[1])]
        pts = [
            tuple(float(v) - 100 for v in first(n, k)[1:])
            for k in (("at",) if n[0] == "via" else ("start", "end"))
        ]
        delete = False
        reason = None
        if (
            net in signals
            and n[0] == "segment"
            and uid not in oldids
            and any(8 <= x <= 15.5 and 11 <= y <= 15.5 for x, y in pts)
        ):
            delete = True
            reason = "new local signal stem replaced for actual U36 translation"
        if (
            net in ("AGND", "V2V5_AUX")
            and uid not in groundids
            and any(6 <= x <= 18 and 9 <= y <= 21 for x, y in pts)
        ):
            assert all(0 < x < 30 and 0 < y < 30 for x, y in pts)
            delete = True
            reason = "new local controller bypass arm rebuilt outside signal exits"
        if delete:
            removed.append(dict(net=net, reason=reason, literal=sexpr(n)))
            t.remove(n)
    moves = []
    for ref, xy in [("U36", (111.5, 113.5)), ("C79", (114.9, 113.5))]:
        f = next(
            f
            for f in children(t, "footprint")
            if any(p[1] == "Reference" and p[2] == ref for p in children(f, "property"))
        )
        before = sexpr(f)
        assert first(f, "layer")[1] == "B.Cu"
        first(f, "at")[1:3] = [a(str(v)) for v in xy]
        moves.append(dict(ref=ref, before=before, after=sexpr(f)))
    # Both actual source-correct receiving drills remain physical objects.
    vias = {
        (names[str(first(v, "net")[1])], tuple(map(float, first(v, "at")[1:]))) for v in children(t, "via")
    }
    assert ("P19_OV_OK", (110.0, 114.6)) in vias and ("P12_OV_OK_SCHMITT", (106.75, 114.6)) in vias
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
    (WORK / "generated/translation.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                original_reference_pcb_sha256=hashlib.sha256(
                    (ORIGINAL / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                protected_ground_reference_pcb_sha256=hashlib.sha256(
                    (GROUND_BASE / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                moves=moves,
                new_cell_stems_removed_for_rebuild=removed,
                all_original_quiet_force_ground_and_terminal_geometry_preserved=True,
                both_explicit_new_receiving_barrels_preserved=True,
                all_circuit_values_and_nodes_unchanged=True,
                all_native_MCAD_PDN_checks_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("U36 B11.5,13.5 / C79 B14.9,13.5; replaced", len(removed), "new local controller stem objects")


if __name__ == "__main__":
    main()
