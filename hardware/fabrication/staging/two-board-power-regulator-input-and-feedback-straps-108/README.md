# Regulator input and feedback connections

A 0.60 mm trace joins the two LT3080 raw positive input pins on P_U7. A 0.40 mm connection grounds the second negative feedback input on P_U1 at its exposed ground pad. The adjacent ground plane backs both traces. Upstream raw supply distribution and loaded converter verification remain open. KiCad verifies 2 intended joins and 1,307 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_U7:7 to P_U7:8 | F.Cu | 0.42 |
| 0.40 | P_U1:5 to P_U1:11 | F.Cu | 0.37 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
