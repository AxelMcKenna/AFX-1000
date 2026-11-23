# Negative 19 V drain sense resistor

N_R71 (1 MΩ) now sits on the back of the board beside N_Q1 and controller N_U18. The 0.40 mm pick-off connects the resistor directly to N_Q1 pin 2. The 0.20 mm sense trace connects its other terminal to N_U18 pin 16. Each branch changes layer once, with a nearby ground via joining the two reference planes. The pad-to-pad distance to the MOSFET dropped from 108.5 mm to 5.7 mm. The distance to the controller dropped from 92.1 mm to 8.5 mm. Both terminals were previously open. [Placement and enclosure dimensions](component-placement.json)

KiCad verified 2 new connections and 781 remaining opens.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N19_POST_NF | N_Q1:2, N_R71:1 | F.Cu, B.Cu | 2.57 |
| /N_negative_startup_protection/N19_DRAIN_SENSE | N_U18:16, N_R71:2 | F.Cu, B.Cu | 19.37 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
