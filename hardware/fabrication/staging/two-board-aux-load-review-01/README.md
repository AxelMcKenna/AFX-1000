# Current two-board AUX load review

The historical AX03 90 mA planning screen cannot be transferred unchanged to
the current power board. This review inventories the actual TBP25 netlist and
identifies the changed loads. It does not qualify the full supply or release
either board for fabrication.

[Machine-readable inventory and calculations](review.json) bind the current
native netlist, native review, historical model and manufacturer documents by
SHA-256. Regeneration uses
`python -m hardware.fabrication.assess_two_board_aux_load` from the repository
root and refuses to overwrite an earlier report.

[Independent verification](verification.json) checks inventory coverage,
current arithmetic, capacitor charge, thermal calculations and source hashes.

## Actual rail inventory

| AUX terminal category | Count |
| --- | ---: |
| IC supply pins | 81 |
| IC inputs tied directly to AUX | 13 |
| Capacitor terminals | 86 |
| Resistor terminals | 45 |
| Connector terminals | 2 |
| Clamp-diode terminal | 1 |
| Regulator output | 1 |
| Total | 229 |

The two connector terminals and the clamp path remain in the ledger; their
eventual loads and partial-power behavior must be resolved. The report lists
every terminal, IC family, direct resistor branch and direct capacitor.
Resistor terminal counts are not independent full-rail loads: divider series
paths and logic states must be solved before summing current.

All 86 direct capacitors return to AGND. They total **28.4 µF nominal**:
two 10 µF capacitors and 84 100 nF capacitors. Charging that nominal inventory
to 2.7 V in 1 ms alone requires **76.68 mA average**; 10 ms requires 7.668 mA.
These are charge/ramp comparisons, not actual startup predictions. Actual
capacitance tolerances, bias, IC capacitance, capacitors behind other nodes,
the regulator's ramp and simultaneous circuit load are still required.

## Changed buffer and current margin

AX03 assumed eight SN74AUP3G17 triple buffers. The actual circuit has seven
and an **SN74LVC3G17DCUR at E_U42**. The earlier E_U42 had one active input;
its two unused inputs were grounded. All three inputs are now active, with
the two additional channels driving NF control interfaces. This change
therefore affects both package current and input-dependent current.

The comparison below changes only this package and its active-input count
in the old model. It retains every other historical allocation and its 1.2
factor; it does not claim a reconciled current-board total.

| Extra current allocated per active LVC input | Historical worst overlap | U42-only revised overlap | Margin to 90 mA |
| --- | ---: | ---: | ---: |
| 100 µA | 89.357 mA | 89.608 mA | +0.392 mA |
| 250 µA | 89.357 mA | 90.148 mA | −0.148 mA |
| 500 µA | 89.357 mA | 91.048 mA | −1.048 mA |

The break-even allocation is **208.84 µA per active LVC input**, before any
other reconciliation. TI's 500 µA delta-ICC row applies at VCC 3–5.5 V with
one input at VCC−0.6 V; it does not establish a bound at the actual AUX voltage
or throughout input transitions. The 10 µA no-load package row likewise has
specified input conditions. These rows support a sensitivity comparison,
not a guaranteed current sum.
[TI SN74LVC3G17, section 6.5](https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf)

The current E_U42 datasheet field still points to SN74AUP3G17. Correct that
metadata in the next native revision while retaining the selected LVC part
and pin connections. The LVC substitution was made for output-drive reasons;
reverting it merely to recover the old current estimate would discard that
design requirement.

POWER_READY also has a real released-state load: R110 feeds the two
10 kΩ/22 kΩ enable branches. At 2.7 V, nominal resistance and zero EN source
current, the AUX draw is **158.824 µA**. The older P03 model represented this
state with a 2 µA leakage allowance. Use the full shared-enable model for
tolerance and EN-current corners. Its asserted-state pull-up load is already
included in the old fault calculation and must not be added twice.

The four Si8751 drivers each retain a 10 kΩ, 1% TT resistor to AGND.
The manufacturer's 9.5 mA maximum row is specified with IN=VDD and TT=10 kΩ;
the four-device sum at those conditions is 38 mA. Actual divided inputs,
TT tolerance and switching require applicable bounds. The OFF-current
140 nA entry is typical, not a maximum.
[Skyworks Si8751/52, table 4.1](https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf)

## Thermal screen

Using assumed VIN=13.2 V, AUX=2.3 V, 90 mA output and a 100 µA ground-current
allocation gives **0.98232 W** regulator dissipation. At 85°C local ambient,
keeping the junction at or below 125°C requires a complete thermal path of
**40.72°C/W or less**. At 55°C the corresponding limit is 71.26°C/W.

TI lists 66.2°C/W for the DGN package under its standard thermal test
conditions. Applying that value gives about 150°C junction at the 85°C
scenario. This is a screening comparison, not the actual board's thermal
prediction. The added local copper and vias do not establish installed
thermal resistance. Verify the intended enclosure ambient and complete
heat path before accepting the linear-regulator design.
[TI TPS7A16, sections 6.4 and 10.3–10.4](https://www.ti.com/lit/ds/symlink/tps7a16.pdf)

## Required continuation

- Reconcile present E/P/N IC, resistor and output loads by actual circuit
  state, including threshold transitions and fault overlap. Preserve the NF
  reserve until ownership is established, avoiding duplicate output loads.
- Establish applicable current bounds and startup charge/ramp behavior;
  decide whether the current LDO and thermal path have sufficient margin.
- Correct E_U42's datasheet metadata and resolve capacitor MPN/derating.
- Then finish AUX source, distribution, power-good and return routing using
  those electrical requirements.

No copper or circuit values changed in this review. Power remains at 2,447
opens and signal at 251. The current fabrication status remains TBP25.
