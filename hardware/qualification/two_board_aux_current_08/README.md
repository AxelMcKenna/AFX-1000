# Current-board AUX load ownership

This checkpoint transfers the existing resistor/output load models onto the TBP71 netlist and prevents duplicate terms. It does **not** establish a complete supply-current bound or regulator feasibility.

`reconcile.py` verifies every snapshot hash, all 81 IC supply pin maps, resistor nominal values and connection sets. Net names differ only by the KiCad root slash, which is normalized with a one-to-one assertion. All 45 direct AUX resistor roots are covered exactly once across 44 networks. The old large corner tables remain in their source analyses; snapshots omit those tables and retain the original digest. This work validates model transfer, not a new solution of every original corner.

| Source-port contribution | Conditional maximum |
|---|---:|
| 44 direct AUX resistor networks | 15.474894 mA |
| 22 AUX logic output pulldowns | 1.557097 mA |
| Four isolated-driver input resistor branches | 1.102378 mA |
| Protection reference output | 0.204079 mA |
| Four amplifier outputs at nominal negative rails | 0.492821 mA |
| Monitor reference output | 0.707209 mA |
| Fast-overvoltage comparator output | 0.036734 mA |
| **Conditional source-port sum** | **19.575212 mA** |

The source models use different stated voltage/state domains and unresolved total resistor-error allocations. The sum is a sensitivity envelope within those models, not an accepted whole-unit worst-case. In particular, the amplifier calculation only covers nominal negative rail voltages; fault voltages, common-mode violations, clamping and external currents need further models.

## Ownership corrections

The 12 negative-rail output pulldowns are a subset of the 22 logic pulldowns. They must not be added as a second subtotal. E_U42's N_R15/N_R16 are also already included. E_R94 loads the reference output and is accounted in that model. E_R104/E_R141 are counted in the logic subtotal and excluded from the additional isolated-driver input term. The READY network and PG/Q103 sink paths are already owned by the direct AUX networks. Shared reference/pullup resistors use separate source-port currents, not duplicated resistor dissipation. Historical AX03 and NF/E28 reserves are neither added nor silently reduced.

## Regulator and startup sensitivity

The four Si8751 devices' 38 mA figure comes from four times the specified 9.5 mA row with IN=VDD and TT=10 kΩ. The common table condition uses a 100 pF gate load; the installed FET pair differs. OFF current is typical-only. Thus 19.575212 + 38 = **57.575212 mA** is only a table-condition sensitivity. It leaves 32.424788 mA relative to the old 90 mA design allocation before the other 77 package currents, transition currents, leakage, switching, external interfaces and clamps. [Skyworks Si8751/52, table 4.1 and its note](https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf).

TPS7A16's 100 mA output capability is distinct from its current limiter. The electrical table specifies 101/225/400 mA minimum/typical/maximum at VIN=3 V and VOUT at 90% of nominal. Neither 90 mA nor 100 mA is a fault-current ceiling. Input voltage and package dissipation constrain operation; the actual installed thermal resistance remains unverified. The DELAY capacitor controls power-good timing after the output crosses its threshold, not the output charging ramp. [TI TPS7A16 Rev F, sections 6.5, 7.3.4–7.3.6 and 10.3–10.4](https://www.ti.com/lit/ds/symlink/tps7a16.pdf).

The current 87 direct capacitors total 28.5 µF nominal. Charging that nominal capacitance to 2.7 V in 1 ms requires 76.95 mA average before simultaneous circuit load. Combining that arithmetic with the table-condition sensitivity gives 134.525212 mA; at 5 ms it gives 72.965212 mA. These are not predictions of the actual ramp or a demonstrated startup failure. Tolerance, bias, aging, transient load/state sequencing and the regulator's actual ramp still need qualification. The state ledger deliberately leaves startup/run/fault totals unset rather than substituting one incomplete sum for each state.

## Verification and next work

`verify.py` independently checks source hashes, native AUX resistor membership, port uniqueness and arithmetic. It rejects four injected errors: a duplicate NF output term, a missing AUX resistor branch, a changed total and an unsupported feasibility claim. Current native topology transfer passes; no board, BOM or schematic was changed.

Next: bind no-load package ICC and transition-current conditions for all 29 orderable families; derive actual active-input/output states and switching loads; reconcile external/clamp paths; establish total resistor and capacitor receiving bounds; then evaluate startup and thermal feasibility. A current subtotal alone does not establish functional logic thresholds or source voltage margin: the existing 2.3 V low-screen boundary leaves no margin to the LTC2910's 2.3 V minimum before distribution drop.
