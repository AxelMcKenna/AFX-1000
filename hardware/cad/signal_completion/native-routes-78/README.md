# Left-channel ADC common-mode connection

A_U101 pin 2 connects to the existing VOCM_L via through a 4.11 mm front-layer trace. The right-channel bias trace on In3 detours around the common-mode trace's projected return path. Two local In4 ground extensions connect to an existing ground via and a new 0.30 mm ground-stitch drill with a 0.60 mm copper pad. Both signal traces are 0.20 mm wide.

The native copper check verifies full-width ground coverage on In1 and, where that plane is interrupted, a locally stitched return on In4 with clearance through the intervening layers. All pre-existing pad groups are preserved except the intended VOCM_L join. KiCad reports 48 remaining opens and the missing A_U201 codec footprint.

[Routes and return geometry](reference-review.json) · [Connectivity](native-review.json) · [Mechanical placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
