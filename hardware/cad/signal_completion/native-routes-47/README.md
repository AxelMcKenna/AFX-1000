# Left ADC common-mode sense resistor

The A_C103 filter node connects to A_R111 through rear and inner-layer 0.20 mm traces. Both layers reference the same inner ground plane. The bypass gate via moves 0.32 mm to widen a nearby ground-plane web. Each end of the inner trace has a 0.60 mm via with a 0.30 mm drill and a nearby ground via. KiCad verifies the intended pad joins and 81 remaining open connections. The ES9292QPRO footprint and installed analog performance remain outstanding.

| Net | Endpoints | Length (mm) |
|---|---|---:|
| A__ADC_LN | A_C103:2 to A_R111:1 | 16.70 |

[Ground references](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
