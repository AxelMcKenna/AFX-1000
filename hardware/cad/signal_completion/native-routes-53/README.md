# Bypass gain timing network

The timing resistor A_R615 and capacitor A_C609 sit beside A_U608 on the front face. Four short traces connect the gain request, delay input and capacitor return. The capacitor returns through an existing ground via. KiCad confirms the two new pad-group connections, continuous ground under the changed traces and 74 remaining open connections. Timing and installed component heights still require measurement.

[Timing network](timing-network.json) · [Mechanical placement](component-placement.json) · [Connectivity](native-review.json) · [DRC](drc.json) · [ERC](erc.json)
