# FPC_M2 — protected NF control-power branch

New private 91-part successor to sealed 84-part FPC01-M1. Seven parts add a third TPS2553DBVR-1 protected output, local input/output bypasses, a current-setting resistor, and a keyed PH output. Every complete original footprint, pad, pose, value and symbol path remains identical. Every original track/via object remains identical. All16 all-layer clip keepouts, zone contracts, stackup and outline remain unchanged; actual copper fills were renewed for the added objects. Parents M1/340 and NF05R265 remain sealed and unchanged.

The actual PCB and schematic pass strict native ERC, all-severity/all-track DRC, connectivity, schematic parity and ignored-check review with **zero findings**. All75 ground pads attach to the actual In1 reference plane; all136 conventional vias are front/back tented. There are no In1 signal tracks. These results establish native electrical closure, not physical fit, PDN, EMI, startup, fabrication or cooling qualification.

## New circuit and physical receiving proposal

U401 IN1/EN3 are tied to the existing operating `FAN5V_IN` rail. GND2 returns to the real ground plane. ILIM5 uses R401220 kΩ. OUT6 feeds only `NF_RAW5` and J401.1; J401.2 is ground. FAULT4 is explicitly NC; internal current-limit/latch behavior remains active. The output is always available when RAW5 is present, independent of E28 MASTER, so fans and NF shutdown controls stay powered when protected loads shut down. No MCU output or automatic retry RC drives EN.

The actual proposed destination is NF J1.3 / J1.2 control power/ground. This is **not** its separate J6 TMR-primary feed or negative-force interface. Supply originates from P03 operating J23/J21; test-only J3 is prohibited. NF AUX also returns through its AGND: the conservative receiving arithmetic is49.132243 mA on the NF return and447.376483 mA on the shared FPC return, not the35.132243/433.376483 mA positive-current numbers. Any other AGND cable becomes a parallel return that requires explicit coupled analysis; no double-crimp or ideal quiet-star connection is assumed. This proposal adds an interface; no parent harness or combined unit has adopted it.

New front poses are U401(12.5,18,270°), R401(12.5,21.1), J401(5,24.2). Four rear0603 bypasses are at x11.6/13.4, y15.0/18.4. New source/current-limit/output loops use six ordinary0.65/0.30 mm tented vias, a declared0.3 mm output escape and0.5 mm force run. All84 existing parts stay fixed. Actual manufacturer DBV lands are1.1×0.6 mm,2.6 mm column spacing,0.95 mm pitch,R0.05. The Fab/receiving model includes maximum body plus stated mold flash:2.25×3.55 mm and1.45 mm maximum seating-plane height; the courtyard is4.2×3.8 mm. Exact maximum mold flash/assembly geometry is retained for fresh MCAD, not replaced by a generic package box.

C401/C402 are real parallel input bypasses; C403/C404 are parallel output bypasses. Each is KEMET C0603C104K5RACTU100 nF50 V X7R. The **receiving** effective minimum60 nF per part gives120 nF input, above TI's100 nF recommendation; actual bias/aging/life/effective-C remains unaccepted. The manufacturer maximum body0.95 mm plus0.10 mm receiving seat gives1.05 mm rear projection, inside the inherited1.2 mm SMD envelope. Actual local-loop inductance and high-value output bulk needs during unknown ISO bursts remain bench holds.

J401 candidate is JST B2B-PH-K-S / PHR-2 / SPH-002T-P0.5S with Alpha3049 AWG26. Its current rating2 A applies AWG24; no hot AWG26 rating is inferred. The selected contact wire/insulation range accepts the candidate nominal wire size, while crimp tooling, retention, soldering, bend radius13.462 mm and strain transfer remain unqualified. **The inherited1.76 mm PCB scenario fails the PH catalog's0.8–1.6 mm applicable board-thickness range.** Native board nominal1.6 mm is not a guarantee of a manufactured maximum1.6 mm. A selected actual≤1.6 mm stack/process or another connector is required before adoption. No tolerance waiver is taken.

## Current, voltage and fault comparisons

R401 complete±1% receiving spans217.8–222.2 kΩ, inside TI's15–232 kΩ region. Equation1 gives104.14185–145.73895 mA across the stated process/temperature model. The earlier unimplemented249/300 kΩ proposals are rejected as outside this range. NF05R load is29.276869 mA static /35.132243 mA guarded. Additional channel IQ150 µA, EN0.5 µA and board/cap leakage5 µA are separately provisioned;150 µA is a receiving allocation, not a transfer of the120 µA primary210 kΩ/6.5 V row to this220 kΩ circuit.

The guarded total digital partition is2.417376483 A within the unchanged2.44 A receiving proposal. FPC input guarded allocation becomes433.376483 mA, including both fans, health, protection and NF once. Remaining digital allocation is22.623517 mA; this is not a completed whole-source PDN/current proof. The full2.44 A /90 mA AUX planning heat capacity remains37.270336900 W; neither the lower normal BOM sum nor normal I²R is counted twice.

The primary DBV full-temperature RON maximum135 mΩ gives4.743 mV at the guarded NF load. A conditional J201 input4.90–5.20 V receiving screen leaves78.590 mV for actual shared PCB, PH contacts, both wires, signed reference offsets, dynamic loss and uncertainty after applying20% allowance to the100 mV headroom. Actual NF local target remains4.80–5.20 V. No pad, barrel, ground plane, wire or connector is assigned zero resistance. No old FPC PDN/noise result is inherited; a fresh coupled extraction is required.

## Inrush and limits of fault protection

New source-side input capacitors charge **before** U401. Their initial+positive-temperature partial subtotal is0.253 µF. New local output capacitors plus NF's known external inventory total0.718 µF downstream, for0.971 µF overall. IC/internal/wire capacitance and ISO startup-current bursts are unknown. An ideal constant-current calculation with the stated bounded load gives54.103 µs to charge the known downstream subtotal to5.2 V. It is a diagnostic, not a full startup bound. A proposed total80 mA startup-peak receiving target, ×1.2=96 mA, fits below the lower limit; it has not been characterized.

TI's3 ms turn-on row is tested at1 µF/100 Ω and is not transferred to this load. The2 µs short-response value is typical only. The5–10 ms FAULT deglitch row alone does not establish a hard cutoff/rearm/SOA bound under thermal cycling or brownout. At the current-limit upper scenario the limited DC power is0.757843 W;7.57843 mJ over10 ms excludes the unbounded initial peak and is not total fault energy. Reverse-energy, source collapse, thermal retry, shared E28 fault retention and NF's NC-clamp response remain held. **Guaranteed loaded cutoff upper time and complete fault-energy upper limit stay null.**

## Evidence and replays

`generated/final-drc.json`, `generated/erc.json` and `generated/netlist.xml` are actual fresh native outputs. `generated/analysis.json`, `native-reference-check.json`, `generated/local-route.json` and `generated/review.json` bind exact sources. Tests reject changed clock copper, moved parent parts, disabled clip keepouts, a bypassed limiter, out-of-range current-setting values and false thickness/thermal/startup acceptance. Failed initial placements and the175 µm via-clearance trial are preserved.

Early native-Python runs failed before saving a PCB: a detached footprint was flipped, and GUI project initialization was attempted in a headless interpreter. Logs remain. The corrected builder adds each new footprint to the board before flipping; CLI applies/refills the actual project, avoiding GUI settings-manager calls. Parent340/M1 seals were independently rechecked unchanged. Final CLI/native proof is fresh; no failed Mac result is reused.

Primary sources: [TI TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf), §§7.3/7.5/9.3/9.5.1/10.2.1.2.4/12.1 and package pages41/42; [JST PH](https://www.jst.com/wp-content/uploads/2021/01/ePH.pdf); [KEMET exact bypass](https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU); [Alpha3049](https://www.alphawire.com/en/products/wire/hook-up-wire/premium/3049). Captured bytes and parent identities are hashed. Native/reference/model checks leave all physical, current, PDN, noise, source-startup, installed-airflow, thermal and fabrication-release flags false.

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest hardware.qualification.boards.fan_health.composite_nf_branch.test_branch -v
```

The seal rejects regeneration in place. Future stack/connector/fit or routing changes belong in a successor; the current complete unit has not adopted this PCB.
