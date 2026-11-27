# Right fan input decoupling

The 100 nF F_C302 is on the component side beside F_U301. Its two front copper branches run 4.38 mm from the capacitor to the switch input and 3.08 mm to the switch ground. The capacitor previously sat at (53.5, 179.5) mm. Its new center is (39.5, 178.75) mm. The closest modeled neighboring body is 0.35 mm away.

KiCad verified the new 5 V join and preserved every existing pad group, leaving 970 opens. The complete path from the regulator to the fan supply remains open.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
