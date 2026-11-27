# Converter inductor and amplifier supply

A 1.00 mm trace joins inductor P_L8 directly to diode P_D4 at the Ćuk converter coupling node. A separate 0.35 mm trace connects the LT3080 raw input to the OPA4192 positive supply pin. Both routes have continuous adjacent ground copper and use no vias. KiCad verifies 2 pad-group joins and 1,031 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 1.00 | P_L8:1 to P_D4:2 | F.Cu | 5.99 |
| 0.35 | P_U7:7 to P_U5:4 | F.Cu | 3.41 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
