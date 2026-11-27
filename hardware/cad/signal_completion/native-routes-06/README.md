# Stereo output series resistors

A_C513 pin 1 connects to A_R503 pin 2 on the left channel. A_C514 pin 1 connects to A_R507 pin 2 on the right. Each connection uses a single 0.25 mm bottom-layer trace. The left trace measures 9.575 mm and the right measures 7.400 mm. The parallel coupling capacitors A_C501 and A_C502 still need routing.

Each trace has a local In6.Cu analog ground pour stitched near both ends. The ground reference covers the full trace width outside the plated signal pad clearance. KiCad 10.0.7 reports 138 opens and zero geometry findings before and after refill. ERC passes. Schematic parity flags the missing A_U201 footprint. Placement matches the assembly capture for both boards.

[Connectivity](native-review.json) · [Copper and ground returns](reference-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-05/README.md)

Run the ground-return and connectivity checks from the repository root with KiCad Python.

```sh
python3 -m hardware.cad.signal_completion.verify_output_returns hardware/cad/signal_completion/native-routes-05 hardware/cad/signal_completion/native-routes-06
```
