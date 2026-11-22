# Negative 12 V output monitor feedback

The 0.30 mm trace connects the summing input at N_U13 pin 6 to feedback resistor N_R41 pin 2. N_R40 pin 2 shares the same node. KiCad verified continuity between all three pads after refill. A local ground via connects the surface traces’ two reference layers. The closest switching-node or pass-gate copper on any layer is 17.72 mm away in plan view.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U13:6 | 5.14 | 0.89 |

KiCad verified the expected pad groups. The board has 898 open connections. The monitor threshold and transient response still require bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
