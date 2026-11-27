# Module eFuse slew capacitors

The parallel 100 nF timing capacitors G_C3 and G_C4 connect on the front layer. The DVDT conductor and its dedicated MODULE_RTN return follow matching 3.22 mm paths. They use no vias. Native KiCad refill preserved every existing filled polygon. [Plane and pair checks](plane-review.json)

KiCad verified 2 connections and 761 remaining opens.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /G_module_input/MODULE_DVDT | G_C4:1, G_C3:1 | F.Cu | 3.22 |
| /G_module_input/MODULE_RTN | G_C4:2, G_C3:2 | F.Cu | 3.22 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
