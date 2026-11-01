# SC02 — negative startup schematic draft

This separate 60-part native KiCad draft puts an **LM5067MM-1/NOPB limiter after each retained negative B2B bank and before all protected bulk**. It provides reviewable −19 V and −12 V circuits, actual exported pin contracts, conditional calculations and explicit failures. It does not alter E28, P03, SC01 or frozen mechanical kits. There is no PCB, fabrication release, validated ramp, complete startup bound or physical test result.

[Native schematic](negative_startup.kicad_sch), [native SVG](generated/schematic-svg/negative_startup.svg), [full CPU preview](generated/schematic-preview.png), [−19 V left](generated/n19-left.png), [−19 V right](generated/n19-right.png), [−12 V left](generated/n12-left.png), [−12 V right](generated/n12-right.png), [BOM](bom.csv), [analysis](generated/analysis.json), [native ERC](generated/erc.json), [independent verification](generated/verification.json).

## Actual negative topology and interfaces

The [TI LM5067 Rev D](https://www.ti.com/lit/ds/symlink/lm5067.pdf) VSSOP pin map is **1 VCC, 2 UVLO, 3 OVLO, 4 PWR, 5 VEE, 6 TIMER, 7 SENSE, 8 GATE, 9 OUT, 10 PGD**. Thresholds and controller capacitors reference **VEE**, the negative after-bank input. VCC receives current through R5 from AGND. The 91 mΩ shunt joins SENSE to VEE. The CSD19536KTT has source at SENSE and drain/tab at the protected negative output. C5's **positive terminal is AGND**; its negative terminal is protected output. D1's anode is protected output and cathode AGND, clamping a positive output excursion. D2's cathode is AGND and anode VEE, the correct negative TVS orientation. Independent export mutations reject positive-controller pin mapping, reversed FET/diodes/electrolytic, ground-referenced TIMER and bulk moved ahead of the limiter.

J1 is after-bank negative input/AGND. J2 is protected negative output/AGND. The frozen E28 planning contract identifies C8 = 1500 µF/35 V ±20% on N19 and C16 = 220 µF/35 V ±20% on N12. They are represented electrically downstream here. **The canonical boards have not been rewired.** All other load/input capacitance, crossrail current and wiring inductance must be inventoried at integration. Moving this limiter after the bank addresses the empty-load late-bank-closure bypass, but does not establish behavior with an already charged load or missing rail.

J3 requires HOST3V3 = 3.0…3.6 V and separate ENABLE3V3 HIGH = 3.0…3.6 V, LOW = 0…0.1 V, referenced to AGND. This deliberately retains SC01's unresolved interface requirement: **E28 J9's 2.5 V status cannot connect directly.** No translator or sequencing logic is claimed. HOST3V3 powers the TLP170GM relay LEDs through 680 Ω; BSS138BK sinks them and has a 10 kΩ gate pulldown. Its normally-open contact joins the upper UV divider while the lower divider stays tied to VEE. The scenario gives about 2.09 mA minimum LED current and 3.71 mA maximum host current per relay, plus up to 0.374 mA per enable input. Those are calculations using stated 25 °C driver/relay conditions, not hot trigger/default-OFF guarantees. The digital power budget, host leakage, missing-host states and actual receiver remain open. **No V2V5_AUX connection or added AUX current** is present.

J4 carries **negative-voltage PG_RAW/VEE/AGND**, never GPIO. The PG pullup goes to AGND, and its bad-state current belongs to the input-side source overhead, not the protected load. PGD only checks small FET VDS; TI also explicitly states PGD is high when VCC−VEE <2 V. Independent absolute output/VCC checks and a safe receiver are therefore required before declaring ready.

## Concrete supply and ramp failures

**The −12 V stage does not establish the recommended VCC operating condition.** Rev D §7.3 specifies at least 2 mA into VCC; the internal zener is specified at 12.35…13.65 V/2 mA. A passive feed from 11.9…12.07 V cannot establish that regulated condition. R105 = 330 Ω and a deliberately unverified 1.2 mA load scenario leave about 11.50 V at VCC−VEE, above the 8.7 V enable-POR maximum in that scenario, but this does not override §7.3 or establish guaranteed operation. TI's advertised −9 V system range requires clarification against the recommended-current/table conditions for this use. No external VCC bleed, phantom positive-rail feed or extra DC/DC is used to disguise the gap. The −19 V 2 kΩ comparison gives >2.6 mA at the declared 18.9 V input allocation, but actual source minimum, temperature transfer and die cooling still need proof.

The LM5069 positive PNP circuit cannot simply be mirrored. The negative pass FET's source is nearly fixed while its drain falls. SC02 instead exposes an **experimental** R3/C1 series drain-to-gate feedback network plus C2 from gate to source and a 10 Ω gate stopper. The concept is inferred from [ADI LT4250L/H p8 Figure 6a](https://www.analog.com/media/en/technical-documentation/data-sheets/4250lhfa.pdf). The controller here is LM5067; values, loop compatibility and fault behavior are **not approved by TI or ADI for this combination**. Direct PDF retrieval failed, so the primary parsed reference was used; exact original circuit-image verification remains open. SC02's explicit netlist is the proposed engineering circuit, not a claimed certified reproduction.

| Conditional input | N19 | N12 |
|---|---:|---:|
| C1 effective ±10% trial, bipolar film ≥100 V | 1.5 µF | 1.0 µF |
| C2 effective ±10% anti-injection trial, film ≥25 V | 22 µF | 10 µF |
| R3 trial | 82 Ω | 100 Ω |
| Frozen local bulk including initial +20% | 1.8 mF | 264 µF |
| Frozen external live load + native bleed | 26.419 mA | 151.265 mA |
| Derived output maximum from frozen ledger | 19.112 V | 12.071 V |
| Output-only ideal ramp with 30…74 µA net current | 0.349…1.051 s | 0.147…0.443 s |
| Full external-cap charge to selected 10 V VGS at 30 µA | ~9.67 s | ~4.48 s |

The 30…74 µA trial comes from the controller's **32…72 µA normal-operation table plus an unverified ±2 µA allowance**. It is not a full trajectory bound. C1 reverses voltage: initially approximately −VSYS and finally +VGS, requiring a bipolar part. Its exact film MPN is unselected. The charge calculation includes **C2·VGS + C1·(VSYS+VGS)**; output-only ramp time omits that gate charge. Adding the zero-start insertion upper scenario (~0.896 s) already pushes both trial full-enhancement sequences above five seconds. This is a conditional failed scenario, not a proven physical startup time. Load-ready voltage, all-bank concurrency, source hot capacity, host boot, reset state and actual controller trajectories remain unbounded.

The anti-injection check uses the CSD's **2.1 V minimum threshold at 25 °C/250 µA** and **61 pF Crss at 50 V/1 MHz**, not a hot nonlinear bound. Selected C2 clears the normal-input charge-divider screen at those test conditions. It **fails** the same screen at the candidate TVS catalogue 25 °C clamp points (38.9/24.4 V): required minimum Cgs is about 28.92/11.68 µF, versus the selected trial minima 19.8/9 µF. That is not a verified input transient waveform, but it precludes a blanket dynamic-OFF claim. Increasing C2 also increases startup and turnoff delay; no silent capacitor tuning closes this tradeoff.

If the controller held GATE_CTRL at VEE during an ideal normal-voltage input step with initially uncharged C1, R3 would initially demand about **235 mA/122 mA** before the RC settles. This conditional clamp-demand calculation is not an actual waveform, but is materially above the controller's 45 mA minimum pull-down testpoint. The added C2, gate stopper, nonlinear controller sink and input rise time must be modeled or measured together. R3 also needs a selected pulse-rated part; an ordinary footprint alone is insufficient.

## Protection, reset and source calculations

The [WSL2512R0910FTA](https://www.vishay.com/docs/30100/wsl.pdf) 91 mΩ shunt sensitivity adds initial 1%, a declared 100 K ×75 ppm/K excursion, one load-life allowance and one solder-heat allowance including their absolute 0.5 mΩ terms. This yields about 87.04…94.96 mΩ, below TI's 100 mΩ selection rule. It is not a qualified lifetime bound. LM5067's own **44…56 mV current-limit and 70…130 mV circuit-breaker** table limits are used, not LM5069's positive-rail limits. Kelvin layout, temperature, pulse rating and test-condition transfer remain open.

R_PWR = 68.1 kΩ/49.9 kΩ gives typical equation values about 5.27/3.86 W. The 16.5…27.5 mV versus 22 mV typical testpoint only supplies a declared gain sensitivity; it is specified at OUT−SENSE =24 V and R_PWR =75 kΩ. No guaranteed selected-value power limit exists here. The candidate has lower normal initial-pass-power scenarios than that scaled sensitivity, but actual modulation, startup timeout and source current still require a complete waveform analysis.

The 470 nF timing-cap trial gives zero-start insertion ~0.166…0.896 s and fault ~11.35…48.99 ms, using ±10% capacitance and an unverified ±0.1 µA leakage allowance. These are not guaranteed windows. **LM5067-1 needs TIMER <0.3 V and a fresh input or UV cycle to reset.** The declared 4.16→0.3 V discharge scenario can take ~2.495 s; arbitrary short ENABLE pulses do not establish reset. Residual TIMER, C1/C2 charge, contact turnoff and partial-power histories are missing. The narrative fault-charge typical differs from the table; calculations use the actual table's 44…140 µA interval.

Large C2/C1 means the controller's circuit-breaker response cannot be substituted for the FET's actual turnoff. The saved report includes Cgs-only discharge examples; they omit Cdv/Miller feedback and are **not turnoff bounds**. The [CSD19536KTT Rev C](https://www.ti.com/lit/ds/symlink/csd19536ktt.pdf) SOA graph is only a conditional reference; case temperature, initial circuit-breaker peak, added-cap fault energy, hot source and reverse-injection waveform are unknown. The worst circuit-breaker table current also exceeds the conditional 1 A/50 V/DC/case100 °C reference used in the report. No SOA pass is asserted.

The FET's body diode conducts SENSE→PROTECTED. A charged negative load can therefore discharge into a collapsed bank; this stage does not provide reverse blocking. Clamps and UV/OV dividers do not qualify charged-load restart, partial-power injection, inductive turnoff or runaway-source energy. The output clamp and input TVS are candidates whose pulse/source/thermal coordination is missing.

The frozen planning contract remains historical. Actual current canonical boards may differ; integration must renew their exact source hashes and complete capacitance/load ledger. The draft includes a conservative input-side overhead sensitivity (VCC feed, UV/OV, bad-state PG pullup, TVS and gate allowance) separately from protected bulk/live load. LED current is paid by HOST3V3. The −12 V supply's missing guarantees prevent either input-current number being an approved source budget.

## Verification and remaining work

Native KiCad reports **0 errors and 8 explicit unresolved-footprint warnings**: C1/C2/C3 and U2 for each rail. Film capacitors, relay land pattern and operating connectors remain unselected; the warning count is not a complete procurement/DFM approval. Other value-requirement passives also need exact MPN/effective-value review. Custom symbols expose actual manufacturer pin numbers; independent contracts check exported connectivity rather than assuming generation correctness. Native ERC establishes connectivity consistency only.

Portable checks cover negative polarity, topology mutations, all protected bulk downstream, reference-domain mistakes, shunt/timer limits, missing gate charge, the −12 V supply failure, incompatible logic, false release flags and every sealed input/evidence hash. Reproduction:

```sh
python3 -m hardware.qualification.boards.startup_circuit_negative.generate --kicad-cli /path/to/kicad-cli
python3 -m hardware.qualification.boards.startup_circuit_negative.analyze
MPLCONFIGDIR=/private/tmp/afx-mpl /path/to/numerical-python -m hardware.qualification.boards.startup_circuit_negative.render_svg
python3 -m hardware.qualification.boards.startup_circuit_negative.verify
python3 -S -m unittest hardware.qualification.boards.startup_circuit_negative.test_startup_negative
```

Before adoption: resolve the −12 V VCC specification with an approved architecture/vendor guidance; validate or replace the experimental ramp including hot input-step and charged/reset states; select actual caps/relay footprints; establish enable/ready translation and sequencing; renew the complete bulk/live-load/source/heat ledger; derive guaranteed power/timer/SOA/turnoff envelopes; then build and measure actual waveforms, controller supply, current, temperature and reset behavior. All physical, startup, reverse-current, SOA, PCB, fabrication and release flags stay false.
