# Codec header clocks

A_R214 pin 2 connects directly to the bit-clock pin on A_J203. A_R215 pin 2 connects directly to word select. The two 0.20 mm bottom-layer traces measure 2.604 mm and 2.608 mm respectively. Each trace has a continuous adjacent In6.Cu ground return outside its plated header pad clearance. The shared pour connects to header ground pin 1 and a 0.60 mm ground via near the resistors. Ground wraps around the combined clearance opening for word select and the nearby PRE_ANALOG_OK via.

KiCad 10.0.7 verifies exactly two additional pad-group connections, reducing the signal board to 134 opens. Independent refills of both board revisions preserve all prior ground and power pours. Geometry and ERC checks pass. Schematic parity still flags the missing A_U201 codec footprint. These checks cover the two local connections. Clock timing and edge quality across the assembled interface still need verification.

[Connectivity](native-review.json) · [Clock routes and ground returns](reference-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-07/README.md)

Run the checks from the repository root with KiCad Python.

```sh
python3 -m hardware.cad.signal_completion.verify_output_returns hardware/cad/signal_completion/native-routes-07 hardware/cad/signal_completion/native-routes-08
```
