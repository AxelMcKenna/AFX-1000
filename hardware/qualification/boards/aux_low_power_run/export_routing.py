"""Export source-bound native routing inputs inside isolated Linux KiCad."""

import contextlib
import json

from hardware.electronics.rail_disconnect.revision28.native_pad_geometry import export
from hardware.electronics.rail_disconnect.revision28.u14_residual_inventory import main

from .verify_e28 import WORK


def run():
    native = WORK / "generated/native-placement"
    target = WORK / "generated/routing-inputs"
    target.mkdir(exist_ok=False)
    pads = export(native / "rail_disconnect.kicad_pcb")
    (target / "pads.json").write_text(json.dumps(pads, indent=2) + "\n")
    with (target / "inventory.log").open("w") as log, contextlib.redirect_stdout(log):
        main(WORK / "rail_disconnect.kicad_pcb", native / "rail_disconnect.kicad_pcb",
             native / "drc.json", target / "components.json")
    print("Exported actual native pads and connected components")


if __name__ == "__main__":
    run()
