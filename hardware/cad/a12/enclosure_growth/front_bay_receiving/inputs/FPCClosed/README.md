# FPC01 private combined fan power and health PCB

This new 66 × 38 mm, four-layer candidate combines FP01 and FH02 into **84 actual parts**. Fresh KiCad ERC, PCB DRC, warnings, schematic parity and open-connection counts are all **zero**. It is a routed receiving proposal; it is not a released or physically qualified board.

The two redundant six-pin interboard headers are removed. RAW5, return and switched-power tach signals are actual PCB nets. The fan-switch FAULT outputs were unused by FH02 and are explicitly NC. No operating-current reduction or connector-loss credit is taken. J201 requires a **new operating DIG force branch from P03 J23/J21**; the P03 J3 engineering header is forbidden. J4 interrupts only P03 J106.3 → E28 J5.3 POWER_RUN. It never drives E28_MASTER_ENABLE, and raw fan power remains live after the health contact opens.

The board keeps the firmware's real ATtiny84A SOIC pin contract, 4 MHz crystal, sensor filters, independent watchdog and RAW5 fault latch. Captured FH02 firmware and all parent circuits remain unchanged. The latch prevents watchdog retry from reclosing the contact after a captured timeout; HEALTH physically stuck high before its first timeout can still permit the initial window. Sensor ADC error, crystal timing, first heartbeat, supervisor ramps and contact cutoff remain receiving/bench conditions.

Three same-value C0G capacitors use supported 0603 packages: C20/C21 are 15 pF C0603C150J5GACTU, and C7 is 2.7 nF C0603C272J5GACTU. C7's manufacturer Table 1A selects thickness code CF; Table 2A gives 0.80 ± 0.07 mm. The additional 0.10 mm seat is a receiving allocation. C7's anchor/rotation is unchanged, and the other 83 complete footprints are identical to the last pre-repair routing checkpoint. Native TI DCU0008A and DGN0008C lands replace two generic patterns that could not meet the retained clearance rules. Process/stencil acceptance is still open.

Clock and ADC paths, regulator input/output/delay loops and fan force paths are deliberate literal copper. The high-impedance watchdog timing escape uses two off-pad tented barrels and a short B.Cu path to avoid trapping WD_EN. Ground escapes were installed before signal routing. In1.Cu remains an uncut return plane, with **zero signal tracks**. Every SMT copper pad has a native via exclusion; all through-vias explicitly request front/back tenting. Unfilled via-in-pad is not permitted. Physical leakage, effective capacitance, loop impedance, return coupling and noise have not been qualified.

`generated/current-native.json`, `closed-drc.json`, `erc.json` and `final-review.json` bind the actual closed source. The review independently compares native schematic, PCB, BOM and firmware pins and checks literal route geometry at 10 nm comparison quantization. Nine portable tests include sensor-swap, plane-cut, removed via-exclusion, deleted crystal-route and wrong-POWER_RUN mutations. Routing attempts and their rejected findings are preserved under `routing/`; their historical counts are not current acceptance evidence. Freerouting's DSN view declares In1 as power and omits its wire-only keepout because the router incorrectly treats legal through-vias as keepout conflicts; native In1 rules remain present and are checked after import. Automatic trace neckdown was disabled after the first attempt violated the native minimum width.

The receiving pose is world (14, 180.5, 3.5) with Rx +90°: native +X → world +X, native +Y → world +Z, front components toward −Y. PCB maximum 1.76 mm and **all rear leads plus solder ≤1.0 mm** are unaccepted fabrication/assembly requirements. No board supports, final wire exits, mating tolerances, strains, fan cooling or airflow are accepted. The immutable earlier receiving snapshot remains under `generated/receiving-placement-66x38`; C7's smaller envelope is a declared successor, not silent adoption by its mechanical receipt.

The complete FH02 receiving current is 16.279 mA, guarded to 19.535 mA. Composition adds no functional current. The separate DIG 2.42 A proposal remains conditional. `power-analysis.json` distinguishes normal allocation, simultaneous switch current-limit diagnostics and the incomplete post-fault standby ledger. Supply/return voltage, actual copper loss, hot ampacity, local heat, fan startup/stall, source guard behavior, contact/partial-power behavior, installed cooling, acoustic/EMC/ESD, assembly and all physical release gates remain false.

Run the portable review/tests from the repository root:

```sh
.venv/bin/python -m hardware.qualification.boards.fan_health.composite.review
.venv/bin/python -m unittest hardware.qualification.boards.fan_health.composite.test_composite -v
```

The native build/routing scripts preserve their explicit intermediate stages. A sealed handoff must not be regenerated in place; create a successor for further repair.
