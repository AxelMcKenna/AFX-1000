# Right audio receiver series resistor

A_R324 moves to the rear next to A_R518. The buffer output reaches the resistor through its existing via, and a short rear trace connects the resistor to the right receiver. Both traces share a grounded In6 reference. The placement report records body and mounting clearances. KiCad verifies the intended pad joins and 85 remaining open connections. The ES9292QPRO footprint and installed analog performance remain outstanding.

| Net | Endpoints | Length (mm) |
|---|---|---:|
| /A_DAC/BUF_OUT_R | A_R324:1 to A_U305:7 | 3.37 |
| A__RECV_R | A_R324:2 to A_R518:1 | 2.40 |

[Resistor placement](component-placement.json) · [Ground references](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
