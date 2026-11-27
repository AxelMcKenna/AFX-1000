# ADC reference capacitors and codec readiness routing

A short rear trace joins the ADC1 reference lands of A_C212 and A_C213. One driver readiness via moves 0.35 mm. The signal follows an inner layer between the relocated via and its existing destination, clear of the two rear capacitor lands. KiCad verifies the reference capacitor join, preservation of the readiness network and 83 remaining open connections. Codec placement and analog performance remain outstanding.

| Net | Endpoints | Length (mm) |
|---|---|---:|
| A__REF_ADC1 | A_C212:1 to A_C213:1 | 1.20 |
| /A_CODEC/DRIVER_SETTLE_READY | A_U212:4 to A_U208:3 | 21.38 |

[Ground references](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
