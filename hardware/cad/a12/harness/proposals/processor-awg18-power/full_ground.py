"""Native E19 multiport AGND basis for later complete external-network embedding."""

import argparse
import hashlib
import json
from pathlib import Path

from analyze import SCENARIOS
from mesh import Mesh, response

from hardware.electronics.common.sexpr import read_sexpr

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]


def run(folder, step, scenario):
    manifest = REPO / "hardware/wiring/generated/system-interconnect.json"
    wires = json.loads(manifest.read_text())["wires"]
    ports = set()
    for w in wires:
        if w["net"] != "AGND":
            continue
        for end in ["from", "to"]:
            b, h, p = w[end]
            if b == "processor_carrier":
                ports.add(h + "." + p)
    assert "J1.2" in ports
    ports.remove("J1.2")
    ports |= {"U1.20", "U1.40"}
    drives = {p: (p, "F.Cu") for p in sorted(ports)}
    measures = dict(drives, **{f"C{i}.2": (f"C{i}.2", "B.Cu") for i in range(11, 21)})
    pcb = folder / "generated/filled.kicad_pcb"
    pads = folder / "generated/pads.json"
    m = Mesh(read_sexpr(pcb.read_text()), json.loads(pads.read_text()), "AGND", step)
    s = SCENARIOS[scenario]
    rows = {}
    for t in [20, 100]:
        n = m.network(s["copper_mm"], s["centroids_mm"], temp=t)
        rows[str(t)] = response(n, ("J1.2", "B.Cu"), drives, measures)
        print("FullAGND", folder.name, step, scenario, t, len(drives), "ports", flush=True)
    report = dict(
        source_sha256={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [manifest, pcb, pads, HERE / "full_ground.py", HERE / "mesh.py", HERE / "analyze.py"]
        },
        ground_port_names=sorted(ports),
        scenario=scenario,
        grid_mm=step,
        networks=rows,
        all_manifest_connector_AGND_ports_present=True,
        unknown_external_current_and_internal_ground_sharing_remain_symbolic=True,
        external_network_already_embedded=False,
        no_missing_current_assumed_zero=True,
        full_pdn_qualified=False,
        physical_qualified=False,
    )
    target = folder / "generated" / f"full-ground-{scenario}-grid{step:g}.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print("WROTE", target, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--folder", type=Path, default=HERE)
    p.add_argument("--step", type=float, default=0.1)
    p.add_argument("--scenario", choices=SCENARIOS, default="cu70")
    a = p.parse_args()
    run(a.folder.resolve(), a.step, a.scenario)
