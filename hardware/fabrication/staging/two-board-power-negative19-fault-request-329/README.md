# Negative 19 V fault request

The fault-request signal connects N_J1 pin 20 to the logic group containing N_U46 pin 1 and N_U45 pin 6. The trace uses In5 and front copper with a single signal via. An existing ground via 1.03 mm from the signal via connects the In6 and In1 return planes.

KiCad verified the intended join and 819 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_FAULT_REQUEST | N_J1:20, N_U46:1 | In5.Cu, F.Cu | 54.94 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
