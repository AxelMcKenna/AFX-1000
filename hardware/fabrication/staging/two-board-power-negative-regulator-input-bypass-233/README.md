# Negative regulator input bypass

P_C69, the 100 nF bypass capacitor, now sits beside P_C67, the 22 µF input capacitor for the LT3090 regulator P_U11. Both capacitors connect to its RAW_N17 input. A 1.56 mm bottom trace joins their input lands. A 3.12 mm bottom trace joins P_C69 to the existing ground via at P_U11 pin 3. Two 0.30 mm through drills carry RAW_N17 from P_C67 to the regulator's input contacts. The traces to those contacts are 0.90 mm and 0.50 mm wide.

KiCad verified all three intended pad-group joins and 991 remaining opens. The closest modeled body clears the capacitor by 0.42 mm. The plane review measures both new via clearances, the regulator input lands and the copper beneath existing traces.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
