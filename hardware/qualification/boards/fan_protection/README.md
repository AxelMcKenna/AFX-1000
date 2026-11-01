# FP01 — native fan-protection section

FP01 is an **18-part KiCad schematic** for two independently protected Sunon V1 fans. Native ERC has zero findings, and all exported pin/net maps match the circuit specification. Thirteen targeted checks pass. The [native schematic](fan_protection.kicad_sch), [rendered PDF](generated/schematic.pdf) and [preview](generated/schematic-preview.png) are provided. This is a protection section; it is not yet a complete health controller, routed PCB or qualified installation.

Each **TPS2553DBVR-1** is always enabled from the unswitched fan feed, with100 kΩ current programming, two input C0G bypass capacitors, a1 µF output film capacitor, a switched-power tach pullup and an output bleed. The two fan branches remain separate after their switches. Fan leads are assigned black/GND on pin1, red/power on pin2 and yellow/tach on pin3 of newly selected JST XH connectors; these are not factory-supplied Sunon connectors. Exact crimp, wire insulation and mechanical retention still need validation.

The [TI primary specification](https://www.ti.com/lit/ds/symlink/tps2553.pdf), RevF, SHA-256 `413aec7178e722bdeacd701a7d4d4f20e5aa09bee0c60ab2176751b6f1ae6da5`, gives the SOT-23 pin contract **IN1/GND2/EN3/FAULT4/ILIM5/OUT6**. Equation1, including a proposed complete100 kΩ±1% resistor interval, produces **232.021–305.811 mA** per channel. This exceeds the188.4 mA motor provision (157 mA catalogue maximum ×1.2). Actual hot/installed starting current and fan capacitance are unknown, so this does not yet prove successful startup.

Overcurrent and reverse-voltage events latch the selected `-1` variant off until enable/power is cycled. Its ambient thermal shutdown may cycle; this is not an unconditional no-retry guarantee. A stalled motor may draw less than the programmed current limit and continue its own internal restart attempts. **Tach pulse detection and a fail-off E28 interlock are still required.** The2 µs short response is typical, and the deglitch/turnoff rows do not bound this actual motor's transient energy. `maximum_fault_energy_j` remains null.

## Source interface correction

Actual immutable P03 component metadata marks **J3 TEST ONLY** and prohibits an operating5 V harness bypassing the power-stud links. The earlier FV01 suggestion of J3 is therefore superseded. No J3 operating harness is authorized by FP01. A **new branch of the operating digital force path**, referenced to P03.J23 positive and J21 return, is required. The tap, connector, joint stack, copper, wire routing and signed return coupling are not implemented or approved here. Original P03 and FV01 files remain unchanged.

The conditional voltage calculation uses the old provisional source-low4.99223 V,22 mV dynamic/spread allowance,0.15 Ω complete shared loop and0.35 Ω complete branch loop at the stated loads. It gives4.84189 V, compared with the4.2 V planning target (1.2× the fan's3.5 V starting row at25°C). Those resistance intervals and hot/installed restart are not demonstrated; the true full source-to-fan voltage interval remains null.

## Current and signal interfaces

The existing416 mA digital reserve is partitioned, not added twice:

| Allocation | Current |
|---|---:|
| Two V1 motors, catalogue max ×1.2 |376.800 mA|
| Switch/tach/bleed provision |1.723 mA|
| NF03 startup-control interface provision |31.300 mA|
| Remaining health logic/LED allowance |6.177 mA|

The31.3 mA NF03 entry rounds above its reported31.21435 mA guarded diagnostic and remains an interface provision pending that circuit's completed inventory. The140 µA switch supply-current row is measured at20 kΩ/6.5 V; using it at100 kΩ is an explicit receiving allocation, not an applicable guaranteed bound. Actual hot and dynamic consumption remains open. The initial30 mA model and native records are retained under `history/initial30mA-NF-interface/`; the circuit topology is unchanged.

Tach pullups come from **switched fan power**, reducing the direct always-on-host feed path when a branch is disabled. J4 tach can nevertheless reach5 V and needs a5 V-tolerant receiver with power-off protection. No direct3.3 V MCU connection is approved. FAULT is open drain with no onboard pullup; the future valid host supply must provide one. Complete off-state, reverse/backdrive and transient pin behavior remains unverified.

Connectors are [JST XH](https://www.jst-mfg.com/product/index.php?lang=2&series=277): B2B-XH-A input, two B3B-XH-A fan outputs and B6B-XH-A health interface, with XHP housings and SXH-001T-P0.6 contacts. The3 A catalogue rating is for AWG22; it is not assigned to the fan's AWG26 leads. Source, PCB, mated dimensions, current/temperature, crimp and handling checks remain open.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m hardware.qualification.boards.fan_protection.design
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m unittest hardware.qualification.boards.fan_protection.test_protection -v
```

KiCad10.0.7 exports and source copies are retained. The tests independently inspect actual exported package pins, connector assignments, switched tach pullups, absent status pullups, ERC, a primary current-limit table row, resistor uncertainty, source prohibition, current conservation and unsupported acceptance flags. No physical, thermal, ESD, acoustic, source-collapse, complete-health or fabrication qualification is claimed.
