SC01 positive-rail startup schematic draft

This is a separate, reviewable native KiCad schematic for +19 V and +12 V. It does not modify P03, E28, the retained B2B banks, protected capacitors, frozen CAD, or any operating PCB. Native ERC has zero errors and six declared unresolved-footprint warnings. The exported 56-component netlist passes the independent manufacturer-pin/topology contract. This is a draft acceptance, not electrical or fabrication qualification.

Open `positive_startup.kicad_sch` in KiCad. The actual exported vector drawing and CPU-rendered previews are under `generated/`. Components use explicit pin-function blocks and net labels; the exported netlist, rather than the appearance of a generic block, defines each connection. `bom.csv` and each symbol's note record unselected parts and interfaces. The six footprint warnings are C1/C2/U2 and C101/C102/U102: exact film capacitor parts and Toshiba footprint review remain unfinished. The engineering header footprints are placeholders, not selected operating connectors.

The circuit order is source → retained B2B hard-off bank → SC01 shunt/pass MOSFET → all protected reservoir bulk and loads. Only the small 100 nF controller bypass remains before the pass element. The schematic explicitly represents retained E28 C4 and C12 after the new limiter; it has not rewired those canonical boards. This ordering prevents the controller from completing an ordinary empty-load startup before a late upstream bank closure. It does not prove reset, precharge or partial-power behavior.

The selected controller is LM5069MM-1/NOPB, the supported latch-off version. Its pins are SENSE1, VIN2, UVLO3, OVLO4, GND5, TIMER6, PWR7, PGD8, OUT9, GATE10. CSD19536KTT is gate1/drain-tab2/source3. The genuine TI ramp circuit uses MMBT5401LT1G PNP base1/emitter2/collector3, with emitter at the ramp capacitor, collector at ground and base through 1.02 kΩ to GATE. The 1N4148W diode has anode at GATE and cathode at the capacitor. These connections were checked against [TI's LM5069 Rev G](https://www.ti.com/lit/ds/symlink/lm5069.pdf), [TIDA-010070 section 2.4.1.4/Figure 13](https://www.ti.com/lit/ug/tidues3/tidues3.pdf), and the original component documents whose hashes are in the report.

The ramp capacitors are requirements: 4.7 µF for +19 V and 0.68 µF for +12 V, with an assumed effective ±10% interval. Their exact film MPNs, leakage, aging, temperature behavior and footprints are unselected. A 100 V rating is requested because this capacitor follows GATE, which can rise above the output voltage. Copying the reference drawing's 50 V label would not establish adequate transient margin. The timing capacitors likewise require an actual selected part and leakage bound.

A current [Toshiba TLP170GM](https://toshiba.semicon-storage.com/info/TLP170GM_datasheet_en_20230522.pdf?did=69102&prodName=TLP170GM) normally open photorelay joins the upper UV divider only when illuminated. Its actual pins are anode1/cathode3/output4/output6. The final selection replaces the investigated TLP175A, whose retrieved PDF is marked unsuitable for new designs. The LED draws from its local after-bank positive rail through a resistor. A BSS138BK sink, 10 kΩ gate-source pull-down and 10 kΩ LED shunt provide the passive default-off request. Manufacturer off-leakage, on-resistance, low-voltage gate-drive and trigger entries have specific test conditions; full-temperature default-off and LED-operate behavior are not proved by the nominal network.

ENABLE requires a separate 3.0–3.6 V digital high, 0–0.1 V low and bounded unpowered leakage. E28 J9's 2.5 V signals are incompatible directly. A real translator and sequencer are not implemented; do not connect J9 to this port. Each enable draws a declared approximately 0.374 mA upper planning load from its digital driver. There is no V2V5_AUX connection or additional steady AUX draw. The positive source still pays the LED/controller/divider current, and the digital supply must budget the control current.

PG_RAW is pulled toward the protected 12/19 V rail and must never connect directly to a logic input. It indicates small pass-device VDS, not independently valid absolute output voltage. A level-safe receiver, absolute-voltage-good check and system sequencing remain missing. Q1's body diode allows protected output charge to backfeed SENSE/VIN when the source or bank disappears. Reverse blocking, charged-load restart, ramp-capacitor reset, discharge and partial-power health gating remain open. A single LM5069 pass device must not be represented as reverse isolation.

The following are conditional planning screens, with all assumptions retained in `generated/analysis.json`:

| Quantity | +19 V | +12 V |
| --- | ---: | ---: |
| Output-only ramp interval | 1.92–12.32 s | 0.176–1.127 s |
| Fast local bulk/live-load current, including new output allowances | 45.01 mA | 170.03 mA |
| Local input total including new overhead | 49.64 mA | 174.58 mA |
| Additional overhead above the old 3 mA controller reserve | 1.63 mA | 1.55 mA |
| R_PWR candidate | 20 kΩ | 39.2 kΩ |
| UV rising scenario | 15.16–16.92 V | 10.12–11.22 V |
| OV rising scenario | 20.22–22.29 V | 12.66–13.94 V |

The source-current rows include explicit LED/divider, PG, Schottky leakage and OUT-bias allowances. Some are unverified temperature envelopes; no missing current is silently assigned zero. Full source hot capacity, transients, all downstream capacitance, waveform-dependent loads and concurrent activation still require validation.

The 91 mΩ WSL2512R0910FTA shunt screen includes initial tolerance, 75 ppm/K over a declared 100 K component excursion, and separate load-life/solder-test drift terms including their absolute 0.5 mΩ terms. This gives 87.0425–94.9575 mΩ in that sensitivity, conditional current limit 0.511–0.707 A and circuit-breaker threshold 0.842–1.494 A. It is not an approved mission-profile lifetime bound. Fault thresholds are much larger than the normal ramp-current targets.

A 470 nF timing-capacitor scenario with effective ±10% and an unverified ±0.1 µA leakage allowance gives zero-start insertion 0.196–0.742 s and zero-start fault charging 13.24–42.25 ms. Residual TIMER voltage can shorten a later fault window; its full initial/reset envelope is missing. The report leaves the guaranteed fault interval null. Gate precharge/postcharge and complete startup time are also unbounded.

TI's 40 µA design-guide value plus a separate 2 µA allowance is used for fast ramp planning. The 22 µA table maximum is specified at GATE−OUT=5 V and is not a full-trajectory guarantee. Likewise the power-limit table only provides specific 48 V/test-resistor conditions. Selected-value power-limit intervals are sensitivity calculations; guaranteed gain/offset corners at 12/19 V remain null. The low-current sense-voltage recommendation and normal-load power coordination are screened without inventing transfer accuracy.

The CSD19536KTT SOA comparison uses the actual Rev C graph, a conservative manually read DC point and TI's application derating method. It is conditional on case temperature ≤100 °C, VDS ≤50 V including dynamics, applicable controller limits and a separately safe initial breaker pulse. Those conditions, graph-reading uncertainty and the real thermal path are not established. No hot-short, long-ramp or repetitive SOA pass is claimed.

The +19 V conservative 4.7 µF/50 mA planning case misses the provisional five-second target. A separate unimplemented 1.2 µF/100 mA comparison has approximately 3.15 s output-only worst planning time, but requires a different source/sequence/capacitance/thermal validation. It is not this schematic. The negative counterpart and whole-unit concurrent startup remain future work.

Reproduction:

```sh
python -m hardware.qualification.boards.startup_circuit.generate --kicad-cli /path/to/kicad-cli
python -m hardware.qualification.boards.startup_circuit.analyze
python -m hardware.qualification.boards.startup_circuit.verify
python3 -S -m unittest hardware.qualification.boards.startup_circuit.test_startup_circuit
```

Numerical reproduction uses external manufacturer PDFs at the recorded `/private/tmp/afx-*.pdf` paths to bind their hashes; portable tests require no CAD tools, downloads or PDFs. Nine tests cover actual exported pins, reversed diode/PNP mutations, upstream protected-bulk and AUX-path mutations, shunt drift, residual timer holds, five-second/current-budget constraints, integrated live-load energy and saved source/evidence integrity. Physical tests performed: zero. All PCB, whole-unit startup, reverse-current, SOA, thermal and fabrication-release flags remain false.
