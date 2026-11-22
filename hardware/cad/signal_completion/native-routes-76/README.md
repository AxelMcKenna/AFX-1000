# Right ADC negative feedback resistor connection

A_R119 pin 1 now joins the existing A__ADC_RN via on the front layer. A short detour of the inner PD_R control trace clears the projection of the feedback trace where the In1 ground pour is interrupted. Ground on In4 provides the local return there and connects to In1 through nearby ground vias. No new vias are required. KiCad verifies 50 remaining connections and the missing A_U201 codec footprint.

[Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
