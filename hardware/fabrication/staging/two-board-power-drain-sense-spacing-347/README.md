# Negative 19 V drain sense clearance

N_U18 pin 16 shares a package edge with the gate-drive pin. Outside the first 2.2 mm of its pin escape, the revised sense trace has at least 0.465 mm clearance to gate-drive and switching copper, up from 0.244 mm. The existing sense via and the resistor remain in place. KiCad verified continuous ground coverage and the same 779 open connections.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_DRAIN_SENSE | N_U18:16, existing sense via | F.Cu | 19.47 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
