# Reference filter capacitor placement

P_C242 moved from (230.00, 152.00) to (226.25, 132.00) mm and rotated 90° on B.Cu. This puts the 100 nF filter capacitor near the OPA2192 buffer and P_C247. The original straight-line separation between the two capacitors' filter pads was 19.50 mm. A 2.48 mm trace now connects them. A 1.65 mm return connects P_C242 to a local ground via outside its body envelope. Both traces are 0.25 mm wide and have continuous ground underneath.

The modeled body clears its closest neighbor P_C247 by 0.30 mm. The body, traces and via clear the modeled cradle by more than 59 mm. The paired placement check confirms only the intended capacitor pose changed. Installed housing fit and assembly tolerances still need qualification.

KiCad 10.0.7 verifies both intended pad-group merges and 1,642 remaining open connections. The ground via contacts In6.Cu and an independent refill reproduces all earlier plane geometries. Geometry DRC and schematic parity pass. ERC retains the two isolated-reference warnings. The buffer input and remaining capacitor-bank branches still require routing.

[Placement comparison](component-placement.json) · [Updated assembly capture](capture.json) · [Paired placement](placement.json) · [Trace and via geometry](routes.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-monitor-ground-28/README.md)
