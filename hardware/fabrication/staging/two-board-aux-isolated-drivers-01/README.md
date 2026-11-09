# TBP50 isolated-driver load reconciliation

Four Si8751 drivers share E28_MASTER_ENABLE, driven by E_U29 pin 7 from AUX.
Their four 100 Ω / 10 kΩ input dividers add **1.102378 mA** at the conditional
2.7 V, −3% resistor corner. The shared output also drives E_R104 and E_R141,
whose **0.337574 mA** is already in the output-pulldown ledger. Its combined
resistive load is **1.439952 mA**; only the four new divider branches should
be added to the previous current inventory.

[Analysis](analysis.json) binds the actual input, timing, MOSFET gate, Miller
capacitor and negative-bank clamp connections. [Independent verification](verification.json)
checks all 4,096 resistor/voltage cases with a separate nodal matrix, plus 16
pin-current transfer pairs. Maximum source-current disagreement is 4.99e-17 A.

## Input-side conditions

Each driver has a 10 kΩ timing resistor from TT to ground and no parallel TT
capacitor. TT is an internally driven control pin: AUX/10 kΩ is not its current.
The package supply term must account for this connection without adding a
fictitious direct AUX resistor load.

| Driver | Input series / pulldown | Timing resistor | Gate series / bleed | MOSFET pair |
| --- | --- | --- | --- | --- |
| E_U1 | E_R4 / E_R5 | E_R3 | E_R1 / E_R2 | E_Q1 / E_Q2 |
| E_U2 | E_R12 / E_R13 | E_R11 | E_R9 / E_R10 | E_Q3 / E_Q4 |
| E_U3 | E_R20 / E_R21 | E_R19 | E_R17 / E_R18 | E_Q5 / E_Q6 |
| E_U4 | E_R28 / E_R29 | E_R27 | E_R25 / E_R26 | E_Q7 / E_Q8 |

Under the receiving assumptions of MASTER HIGH ≥1.85 V, LOW ≤0.45 V and zero
input leakage, the worst driver-input levels are 1.830562 V HIGH and 0.445802 V
LOW. Comparing against the most restrictive thresholds over AUX 2.3–2.7 V
leaves 0.480562 V HIGH margin and 0.129198 V LOW margin. The 3.1 mA source-current
screen has 1.660048 mA remaining after the resistor loads.

These margins do not qualify the complete master net. Receiver currents,
external E_J6/E_J9 loads, simultaneous output loading, ground/supply drops and
transition behavior still require accounting. The 1.85/0.45 V limits come from
the AUP table at 2.3 V and 3.1 mA; using those limits throughout the proposed AUX
range is explicitly a receiving envelope here. Recorded current-transfer
coefficients describe how each driver-input leakage affects the shared output.
No leakage bound is invented for Si8751 from the Si8752 diode-input entries.

## Output-side conditions

Each driver feeds two CSD18540Q5B MOSFET gates through 22 Ω, with a 20 MΩ
gate-to-common bleed. Each Miller capacitor is 10 pF with a 15 kΩ series
limiter to its corresponding drain. E_U2 and E_U4 also have external
TLP4590AF clamps through N_R7/N_R14, each 220 Ω, and connector contacts.

The [primary review](primary-review.json) records the table conditions. The
four-driver 38 mA sum applies to the stated 10 kΩ timing-resistor test point;
it is not yet an accepted installed current limit. OFF current has no maximum
in that table. The driver's timing measurements use a 100 pF gate load.

The two-MOSFET capacitance sum is 6.50 nF typical / 8.46 nF maximum at the
MOSFET table condition. Their 10 V gate-charge sum is 82 nC typical / 106 nC
maximum at its separate table condition. These show why the driver timing
numbers cannot be transferred directly; neither capacitance nor charge is an
installed full-temperature timing model. Clamp overlap, hot gate leakage,
Miller transients and actual switching charge remain to be qualified.

Gate bleeds and clamp currents belong to the isolated output load model;
they are not direct AUX voltage/resistance branches. Their effect on input
supply current needs the driver conversion behavior. Changing TT to save
current would also require rechecking startup timing; no such change is made.

This completes the shared input-resistor ownership calculation, not driver
current or unit timing acceptance. No copper changed and fabrication remains
unreleased. Continue with the remaining package/pin ledger and actual driver
startup/fault loads before accepting the AUX source and installed thermal path.
