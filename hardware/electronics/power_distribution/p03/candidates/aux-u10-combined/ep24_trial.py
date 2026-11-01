"""Native-only24-via EP construction experiment; production source stays untouched."""

import gzip
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from hardware.electronics.common.placement import footprint_root
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.power_distribution.p03.route import OUT, ROOT, coded, named


def run():
    cli = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    base = Path(
        "hardware/cad/a12/thermal/generated/native-inputs/p03-ceed963a120145b6a6768c4e30188a5ada0b72a40aff8da56578a4424a370ee4.kicad_pcb.gz"
    )
    raw = gzip.decompress(base.read_bytes())
    t = coded(read_sexpr(raw.decode()))
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(t, "net")}
    removed = 0
    for v in list(children(t, "via")):
        x, y = [float(a) - 100 for a in first(v, "at")[1:3]]
        if int(first(v, "net")[1]) == nets["AGND"] and abs(x - 109) <= 0.85 and abs(y - 8.2) <= 1.2:
            t.remove(v)
            removed += 1
    coords = []
    for i in range(4):
        for j in range(6):
            x, y = 109 + (i - 1.5) * 0.45, 8.2 + (j - 2.5) * 0.45
            coords.append((x, y))
            t.append(
                read_sexpr(
                    f'(via(at {100 + x} {100 + y})(size .55)(drill .2)(layers "F.Cu" "B.Cu")(free yes)(net {nets["AGND"]}))'
                )
            )
    trial = OUT / "trials/ep24"
    pcb = trial / "power_p03.kicad_pcb"
    pcb.write_text(sexpr(named(t)) + "\n")
    for n in ("power_p03.kicad_pro", "power_p03.kicad_dru", "fp-lib-table"):
        shutil.copy2(ROOT / n, trial / n)
    if not (trial / "RMX_P03.pretty").exists():
        shutil.copytree(ROOT / "RMX_P03.pretty", trial / "RMX_P03.pretty")
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/p03-ep24-config",
        KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
    )
    args = [
        str(cli),
        "pcb",
        "drc",
        "--severity-all",
        "--refill-zones",
        "--save-board",
        "--format",
        "json",
        "-o",
        str(trial / "drc.json"),
        str(pcb),
    ]
    r = subprocess.run(args, env=env, capture_output=True, text=True)
    print(r.returncode, r.stdout, r.stderr)
    drc = json.loads((trial / "drc.json").read_text())
    introduced = [v for v in drc["violations"] if v["type"] not in {"track_dangling", "via_dangling"}]
    report = dict(
        base_sha256=hashlib.sha256(raw).hexdigest(),
        native_trial_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        removed_direct_vias=removed,
        new_vias=coords,
        new_via_diameter_mm=0.55,
        new_drill_mm=0.20,
        array_pitch_mm=0.45,
        nominal_hole_gap_mm=0.25,
        nominal_annulus_mm=0.175,
        native_non_dangling_findings=introduced,
        all_native_issues=len(drc["violations"]),
        native_opens=len(drc["unconnected_items"]),
        vendor_construction_accepted=False,
        physical_qualified=False,
        production_source_changed=False,
    )
    (trial / "trial.json").write_text(json.dumps(report, indent=2) + "\n")
    print("introduced", len(introduced), "nativeopens", len(drc["unconnected_items"]))


if __name__ == "__main__":
    run()
