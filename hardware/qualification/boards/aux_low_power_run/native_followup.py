"""Source-bound copper comparison and residual export in isolated KiCad."""

import contextlib
import json
from pathlib import Path

from hardware.electronics.rail_disconnect.revision28.native_force_compare import compare
from hardware.electronics.rail_disconnect.revision28.u14_residual_inventory import main

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"


def run():
    prior = WORK / "generated/native-direct-pose-checked/rail_disconnect.kicad_pcb"
    native = WORK / "generated/native-logic-pour-trial"
    source = WORK / "generated/logic-pour-trial/rail_disconnect.kicad_pcb"
    out = WORK / "generated/logic-pour-followup"
    out.mkdir(exist_ok=False)
    (out / "native-force-comparison.json").write_text(json.dumps(compare(prior,native/source.name),indent=2)+"\n")
    with (out / "inventory.log").open("w") as log, contextlib.redirect_stdout(log):
        main(source,native/source.name,native/"drc.json",out/"components.json")
    print("Native power-copper comparison and residual component export complete")


if __name__=="__main__":
    run()
