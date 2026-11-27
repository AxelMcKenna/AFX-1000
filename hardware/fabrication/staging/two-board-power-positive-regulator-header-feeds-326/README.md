# Positive regulator feeds to the rail header

The regulated +19 V and +12 V outputs reach pins 1 and 4 of P_J2. Each 1.00 mm wide feed starts at an existing output via. The +19 V route uses In5 with In6 as its ground reference. The +12 V route uses In2 above In1 ground. Both enter the connector lands through 45-degree approaches. Refilling the board shifted a remote In5 ground boundary around (62, 141) mm. The difference in copper area was below 0.0000001 mm² in each direction. Its island and hole counts were preserved.

At 85 °C and 18 µm copper, the [trace model](feed-drop.json) gives 0.70 mV at 26 mA for the +19 V feed and 10.66 mV at 151 mA for the +12 V feed. These values cover the new copper traces. The barrels, connectors and other portions of each supply and return path still require assessment.

KiCad verified both intended joins and 823 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_P19_SRC | P_U7:9, P_J2:1 | In5.Cu | 22.38 |
| PWR_P12_SRC | P_U8:3, P_J2:4 | In2.Cu | 58.74 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
