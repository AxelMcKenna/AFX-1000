# Voltage monitor mode straps and supply branch

The LTC2910 disable and polarity-select inputs connect to system ground. A 0.40 mm trace supplies the monitor pull-up resistor M_R113 from the existing 3.3 V rail. The rail review checks the new branch against its adjacent ground plane. Loaded current and temperature performance remain to be measured. KiCad verifies 2 intended joins and 1,360 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | P_U25:13 to P_C103:2 | B.Cu | 1.77 |
| 0.40 | M_R113:1 to M_U8:6 | F.Cu | 7.76 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
