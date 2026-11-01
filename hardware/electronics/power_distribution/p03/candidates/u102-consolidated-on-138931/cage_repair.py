"""Remove two actual surface routing fences before reconnecting their nets.

Native connectivity evidence previously showed trapped guard pins and AUX delay.
No component/pin/net is changed; each removed net remains a routing obligation.
"""

import gzip
import hashlib
import json

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import OUT, ROOT, coded, named


def implement():
    pcb = ROOT / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = OUT / f"history/before-cage-repair-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    for obj in list(children(tree, "segment")):
        if str(first(obj, "layer")[1]) != "F.Cu":
            continue
        net = nets[str(first(obj, "net")[1])]
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        match = net == "INPUT_OV" and (
            abs(a[1] - 15.25) < 1e-6
            and abs(b[1] - 15.25) < 1e-6
            and min(a[0], b[0]) < 27.5
            and max(a[0], b[0]) > 25
            or abs(a[0] - 27.5) < 1e-6
            and abs(b[0] - 27.5) < 1e-6
            and min(a[1], b[1]) < 15.3
            and max(a[1], b[1]) > 14.5
        )
        match |= (
            net == "VIN_IC"
            and abs(a[0] - 29.5) < 1e-6
            and abs(b[0] - 29.5) < 1e-6
            and min(a[1], b[1]) < 20
            and max(a[1], b[1]) > 20
        )
        if match:
            tree.remove(obj)
            removed.append(dict(net=net, start_mm=a, end_mm=b, width_mm=float(first(obj, "width")[1])))
    pcb.write_text(sexpr(named(tree)) + "\n")
    (OUT / "cage-repair.json").write_text(
        json.dumps(
            dict(
                prior_sha256=digest,
                archive=str(archive.relative_to(ROOT)),
                removed_surface_fences=removed,
                native_connectivity_and_current_path_extraction_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Removed actual surface fences", removed)


if __name__ == "__main__":
    implement()
