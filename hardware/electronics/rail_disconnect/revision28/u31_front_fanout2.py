"""Fine-grid physical escapes for the two source-bound F-face ordinary gates."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, read_sexpr, sexpr
from .band_local_escape import escape
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u31-front-placement2-work"
WORK = ROOT / "generated/u31-front-fanout2-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    t = read_sexpr(blob.decode())
    r = Router(t)
    rows = []
    for ref in ("U31",):
        p = next(p for p in r.by_ref[ref] if p["pin"] == "7")
        result, reason = escape(r, p, maxdistance=4, step=0.025)
        assert result, reason
        rows.append(dict(ref=ref, pin=7, net=p["net"], actual_escape=result, reason=reason))
        stems = []
        for i in (1, 2, 3, 4, 5, 6, 8):
            p = next(p for p in r.by_ref[ref] if p["pin"] == str(i))
            end = (p["xy"][0] + (-0.5 if i <= 4 else 0.5), p["xy"][1])
            good = legal_line(r, p["net"], 0, p["xy"], end, 0.2)
            if good:
                r.path(p["net"], 0, [p["xy"], end], 0.2)
            stems.append(dict(p, xy=end if good else p["xy"]))
        for i in (2, 3, 6, 1, 4, 5, 8):
            p = next(p for p in stems if p["pin"] == str(i))
            result, reason = escape(r, p, maxdistance=4, step=0.025)
            rows.append(dict(ref=ref, pin=i, net=p["net"], actual_escape=result, reason=reason))
            print(ref, i, bool(result), reason, flush=True)
    for ref in ("C76",):
        for p in r.by_ref[ref]:
            result, reason = escape(r, p, maxdistance=3, step=0.025)
            rows.append(dict(ref=ref, pin=p["pin"], net=p["net"], actual_escape=result, reason=reason))
            print(ref, p["pin"], bool(result), reason, flush=True)
    added = []
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL, f"rmx:E28:analogfrontfanout:{digest}:{i}:{sexpr(n)}"
                            )
                        )
                    ),
                ]
            )
            added.append(sexpr(n))
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
    (WORK / "generated/fanout.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=digest,
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                attempts=rows,
                actual_new_copper=added,
                no_old_copper_removed=True,
                qualification=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
