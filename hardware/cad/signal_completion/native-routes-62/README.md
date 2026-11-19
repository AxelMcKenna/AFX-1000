# Right ADC common-mode clamp

A_R129 pin 2 connects to A_D102 pin 3 through 17.41 mm of 0.20 mm copper and one 0.60/0.30 mm via. Both surface traces have a continuous adjacent ground reference up to the via clearance. KiCad verifies 65 remaining connections. The via changes the nearby ground pour by up to 0.0103 mm² per layer outside its nominal clearance. Existing adjacent traces retain their ground reference. The right ADC driver input remains open. The common-mode drive and clamp behavior still require measurement.

[Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
