# AUX regulator placement candidate

A compact eight-part TPS7A1601 auxiliary-supply cell passes current native-pad
clearance and courtyard/body/support/height screening. **Candidate only:** the
board has not been modified, routed or natively revalidated at these positions.
The [survey](survey.json) binds the actual source board, capture and checks.

| Part | Candidate position, mm | Face / angle |
| --- | --- | --- |
| P_U102 regulator | 190.5, 130 | Front / 90° |
| P_C113 input | 187.8, 124.1 | Front / 90° |
| P_C106 main output | 190.5, 135.5 | Front / 0° |
| P_C107 output bypass | 195.5, 138.6 | Front / 0° |
| P_C110 delay | 190.175, 125 | Front / 90° |
| P_R109 bottom feedback | 186.9, 134 | Front / 90° |
| P_R108 upper feedback | 189, 134 | Back / 0° |
| P_R130 trim | 193, 132 | Back / 0°, unchanged |

Seven components move; R130 is already local. Every numbered terminal in this
cell is currently isolated in native copper, so regrouping need not prune
existing routes. This screen includes all current stationary pads/tracks/vias,
0.21 mm foreign-copper screening, drilled features, mounting reserves, 0.3 mm
courtyard/body spacing and existing assembly context. It makes no full-housing
fit claim. The old mechanical capture's C204 envelope is refreshed from its
identical C205 back-side template using the verified TBP22 relocation evidence.

Straight pad-center distances are 3.289 mm for the main input connection,
3.387 mm for both main output and output-return connections, and 2.075 mm for
delay. These are placement distances, not proof that direct traces are legal.
The main input, output and delay capacitors share the regulator's front side.

[TI TPS7A16 sections 9 and 10](https://www.ti.com/lit/ds/symlink/tps7a16.pdf)
call for close capacitors on the regulator side, a direct output-capacitor ground
return, and separate input/output ground regions joined at regulator ground.
The high-impedance feedback node needs protection from coupled signals. Preserve
those constraints while routing; the back-side upper/trim resistors require a
reviewed local connection. Effective capacitance, total AUX load, thermal
operation, startup and partial-power conditions remain unresolved.

The current accepted layout is the
[U23 quiet-return checkpoint](../two-board-power-u23-quiet-native-01/README.md).
