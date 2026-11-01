"""Center declared ordinary/AUX junctions on real existing barrels, not move vias."""

import hashlib
import json
import math
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u11-paired-reconnect-work"
WORK = ROOT / "generated/strict-ordinary-centering-work"
ALLOWED = {"V2V5_AUX", "E28_MASTER_ENABLE", "P19_OV_OK_SCHMITT", "E28_DIG_FOLLOW1"}


def main():
    assert not WORK.exists()
    pcb = SOURCE / "rail_disconnect.kicad_pcb"
    blob = pcb.read_bytes()
    t = read_sexpr(blob.decode())
    raw_path = SOURCE / "generated/drc-u11-paired-reconnect.json"
    raw = json.loads(raw_path.read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    by = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(t, k)}
    mapping = {}
    findings = []
    for row in raw["violations"]:
        if row["type"] != "track_not_centered_on_via":
            continue
        n, v = [by[x["uuid"]] for x in row["items"]]
        assert n[0] == "segment" and v[0] == "via"
        net = names[str(first(n, "net")[1])]
        assert names[str(first(v, "net")[1])] == net
        if net not in ALLOWED:
            continue
        q = tuple(round(float(x), 6) for x in first(v, "at")[1:3])
        ends = [tuple(round(float(x), 6) for x in first(n, k)[1:3]) for k in ("start", "end")]
        p = min(ends, key=lambda p: math.dist(p, q))
        limit = float(first(v, "size")[1]) / 2 + float(first(n, "width")[1]) / 2
        assert math.dist(p, q) <= limit + 1e-6
        key = (net, p)
        assert key not in mapping or mapping[key] == q
        mapping[key] = q
        findings.append(row)
    changes = []
    removed = []
    for n in list(children(t, "segment")):
        net = names[str(first(n, "net")[1])]
        if net not in ALLOWED:
            continue
        before = sexpr(n)
        changed = False
        for k in ("start", "end"):
            node = first(n, k)
            old = tuple(round(float(x), 6) for x in node[1:3])
            q = mapping.get((net, old))
            if q is not None:
                node[1:3] = [a(str(x)) for x in q]
                changed = True
        if not changed:
            continue
        if first(n, "start")[1:3] == first(n, "end")[1:3]:
            t.remove(n)
            removed.append(dict(net=net, before=before, reason="junction collapsed inside existing barrel"))
        else:
            changes.append(dict(net=net, before=before, after=sexpr(n)))
    # Exact duplicates introduced by merging ordinary vertices contain no unique Cu.
    seen = {}
    for n in list(children(t, "segment")):
        net = names[str(first(n, "net")[1])]
        if net not in ALLOWED:
            continue
        ends = frozenset(tuple(round(float(x), 6) for x in first(n, k)[1:3]) for k in ("start", "end"))
        key = (net, str(first(n, "layer")[1]), float(first(n, "width")[1]), ends)
        if key in seen:
            t.remove(n)
            removed.append(
                dict(net=net, before=sexpr(n), reason="exact duplicate Cu after common-vertex centering")
            )
        else:
            seen[key] = n
    assert findings and mapping
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
    (WORK / "generated/ordinary-centering.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                strict_source_DRC_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                allowed_nets=sorted(ALLOWED),
                reported_findings_targeted=len(findings),
                common_vertex_mappings=[dict(net=n, old=p, new=q) for (n, p), q in mapping.items()],
                changed_segments=changes,
                removed_zero_or_duplicate_segments=removed,
                all_vias_all_footprints_force_sense_timing_ground_primitives_and_dimensional_rules_unchanged=True,
                AUX_and_return_PDN_require_new_diagnostic=True,
                native_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Centered",
        len(mapping),
        "commonjunctions addressing",
        len(findings),
        "findings;",
        len(changes),
        "changed/",
        len(removed),
        "zero-or-duplicate ordinarytracks",
    )


if __name__ == "__main__":
    main()
