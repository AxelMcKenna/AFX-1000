"""Four-layer finite 3V3 distribution matrices; currents remain nested in Seed input."""

import hashlib
import json
from pathlib import Path

from analyze import SCENARIOS
from mesh import Mesh, response

from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent


def run():
    pcb = ROOT / "generated/filled.kicad_pcb"
    native = json.loads((ROOT / "generated/pads.json").read_text())
    tree = read_sexpr(pcb.read_text())
    rows = []
    for net, source in [("V3V3_IO", "U1.38"), ("V3V3_ANALOG", "U1.21")]:
        targets = {
            p["ref"] + "." + p["pin"]: (p["ref"] + "." + p["pin"], "F.Cu")
            for p in native["pads"]
            if p["net"] == net and p["ref"].startswith("J")
        }
        for scenario, s in SCENARIOS.items():
            m = Mesh(tree, native, net, 0.1)
            for temp in [20, 100]:
                n = m.network(s["copper_mm"], s["centroids_mm"], temp=temp)
                r = response(n, (source, "F.Cu"), targets, targets)
                r.update(
                    net=net,
                    scenario=scenario,
                    temperature_c=temp,
                    grid_mm=0.1,
                    finite_holes=n["finite_holes"],
                )
                rows.append(r)
    report = dict(
        source_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        pad_geometry_sha256=hashlib.sha256((ROOT / "generated/pads.json").read_bytes()).hexdigest(),
        source_sha256={
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ["subrails.py", "mesh.py", "analyze.py"]
        },
        results=rows,
        nested_output_currents_not_added_to_R1_input=True,
        allocated_IO_loads_a={"J6.2": 0.035 + 0.020, "J2.2": 0.020},
        unallocated_IO_loads=[
            "LED logicJ11.3",
            "SDMMCJ12.2",
            "AS5600J9.2/J10.2",
            "GPIOpassives and dynamic/transient currents",
        ],
        V3V3_ANALOG_pot_current_requires_source_voltage_pot_tolerance_and_leakage_model=True,
        source_Daisy_regulator_voltage_and_ground_reference_bounds_accepted=False,
        complete_endpoint_qualified=False,
        physical_qualified=False,
    )
    (ROOT / "generated/3v3-matrices.json").write_text(json.dumps(report, indent=2) + "\n")
    print("WROTE subrails", len(rows), "matrices")


if __name__ == "__main__":
    run()
