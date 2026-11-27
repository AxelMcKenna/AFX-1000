# Held bypass correction and isolated branch cutover

This candidate corrects bypass ownership using actual TBP73 connectivity. E_C1 supplies E_U11 and stays on main AUX; E_C5 also returns to main AUX. E_C29 and E_C36 move to held AUX alongside their physically connected E_U1 and E_U2 VDD branches. E_C9 remains the E_U3 held bypass. E_C13 remains intended for E_U4, but their 13.17 mm separation and absent positive route need a placement/routing revision.

Native schematic comparison against `../held_rail/authored` checks all 1104 components and the union of existing pin keys: exactly four supply pin changes and four value changes, no added ERC violations. The two inherited ERC naming warnings remain. Exact selected capacitor MPNs and all inherited footprint assignments are checked separately.

C29/C36/C9/C13 are specified as KEMET C0805C104K5RACTU: 100 nF ±10%, 50 VDC X7R, 0805, −55 to 125 °C. Manufacturer [primary sheet](https://search.kemet.com/component-documentation/download/specsheet/C0805C104K5RACTU) is archived under `primary/`; its dimensions are 2.0±0.2 × 1.25±0.2 × 0.78±0.10 mm. This fixes the unspecified MPN; it does not establish a guaranteed effective capacitance at actual bias, temperature and age. Existing 0805 footprints are retained.

`board_native.py` uses the isolated `../routed/native-04` PCB, never the accepted PCB. It retargets the complete three-object positive supply groups U1/C29, U2/C36 and U3/C9: two pads and their entire existing track in each group. No track is cut and no partial branch is left with inconsistent net names. Every group membership, original fill and full physical pad identity must remain unchanged; only the declared nine object net names and four capacitor values change. All 55 formerly anonymous pads remain uniquely matched to the prior full physical identities. Remaining shared main-AUX AUP and VIN/LDO branches are deliberately still pending a complete branch cutover design.

C29 and C36 ground pads remain disconnected: these are not yet working bypass loops. Their positive traces are 3.99 and 7.09 mm long respectively. This checkpoint does not qualify placement, supply distribution, ground return, timing or schematic/PCB parity.

The four TPS3703 DSE 0.15 mm copper-gap violations against the unchanged 0.20 mm board rule remain unwaived. No fabrication qualification or acceptance is implied.

Power/reset constraints remain conditional: 200 µF effective reservoir, total drain ≤100 mA, 4.7 Ω ±3% feed, ≤20 mV distribution drop, and ≤1 µs logic allocation yield an 81.00348 µs held-reservoir interval above 3.6 V and 50.00348 µs remaining after supervisor and assumed logic delay. Actual current, driver/MOSFET turnoff, RESET loading, capacitor effectiveness, startup/recharge and thermal behavior remain unqualified. The corresponding calculations and primary sources remain in `../held_rail`.
