# Negative converter input inductor

A 1.00 mm wide front-layer trace connects the existing module-feed via to P_L7 pin 1. P_C70, on the back directly beneath P_L7, already reaches this via. The 1.796 mm trace ends inside the inductor land and uses the existing ground reference on In1. The switching terminal at pin 2 still requires routing.

KiCad verified the intended join and 828 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_MODULE_FEED_IN | P_C211:1, P_L7:1 | F.Cu | 1.80 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
