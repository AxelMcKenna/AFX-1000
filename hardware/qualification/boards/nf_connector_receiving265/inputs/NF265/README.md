# NF05R265 — retained-ARM UV fault and defined LED midpoint paths

Private schematic successor to sealed NF05H261. This packet implements a concrete UV-to-fault path and individual LED shunts. It is **not a PCB, an adopted E28 circuit, or physical qualification**. Earlier 249/261, NF04R, FPC and mechanical seals remain unchanged.

The native KiCad export contains 265 components, zero ERC errors, and the same two identified isolated-secondary `ground_pin_not_ground` warnings at U19/U24. Every declared pin and value matches the actual XML. Independent primary-role checks verify all seven TPS3890 maps: VDD4, RESET6; the four original floating supervisors remain unchanged. Thirteen tests pass. The three-package clearance fixture passes and its enlarged-pad control fails as required; it is only a footprint fixture.

## Circuit change and fault states

U56 remains RAW5-powered and drives U57, which physically removes the common LED energy supply on absolute AUX undervoltage. New AUX-powered U58 (SN74LVC1G14DCKR) accepts its 5.5 V-tolerant Schmitt input. Spare U48 inversion and U51 AND produce:

```
N19_SAFE = N19_SAFE_SOURCE AND ABS_AUX_READY
N19_F_SOURCE = N19_ARM_CONDITIONED AND NOT(N19_SAFE)
```

The exported path is U58.4 → U48.12 → U51.11 → U47.2 → U35.8 → U45.3/.6 → U46.3/.6 → U34.6/.4 → J1.14. This uses the existing E28 shared fault latch; its split-request wiring, reset priority, loaded delay and minimum recognized pulse remain unimplemented receiving requirements. UV/SAFE does **not** reset the retained ARM latch. Before ARM, missing UV readiness holds the existing permit sequence and watchdog wait; after ARM, loss of readiness asserts the source-fault cone. Sixteen actual-pin Boolean combinations verify that settled behavior. Deep AUX corruption, short UV pulses, source collapse and actual physical GLOBAL-OFF duration remain held.

J1.7 is now an **ABS_AUX_FAULT monitor output only**, loaded by R17 and bounded external receiving load. It is no longer an external RESET input. No legacy switch or host driver may drive it. ARM/START contacts remain locally generated monitor outputs, not commands from a PC or unmapped MCU GPIO.

R5/R12 now shunt the first LED in each two-LED string; new R98/R99 shunt the second. Both MID nodes have actual 10 kΩ resistive paths. R4/R11 become 499 Ω, R97 becomes 680 Ω, and C99 becomes 100 nF C0G. The independently powered UV recovery screen is 71.843–161.371 ms under explicitly stated CT reset/current/leak requirements. This is not a guaranteed physical OFF interval.

## DC, drive and power comparisons

`generated/LED-DC-network.json` solves the actual seven-node resistor network over 65,536 DC cases / 262,144 LED-current comparisons. LED open/ideal-short states and driver open/ground states are diagnostic extremes. A separate Norton enclosure agrees with the attained maximum: 7.504732 µA, or 9.005679 µA after ×1.2, against a **receiving** 10 µA hot relay-return requirement. The primary return-current row is only at 25 °C / 1200 mA contact current. Powered/partial-power OD leakage, arbitrary negative injection, nonlinear transient behavior and optical recovery remain unaccepted. No guessed LED forward voltage is used in this OFF-state comparison. Both resistor shunts are real; this does not turn a lumped capacitance into a distributed shutdown-time bound. **Actual loaded cutoff upper time stays null.**

The separate ON-state comparison uses complete receiving Vf 1.0–1.4 V, receiving switch RON 0.5 Ω, full resistor error ±3%, and the actual 2.3 V / 8 mA LVC VOL test point. It gives ≥3.142 mA LED current and ≤6.6112 mA total sink current; the latter ×1.2 remains below 8 mA. The 20 µA AUP VCC−0.1 V row is retained for command loading. U58 input leakage is 5 µA, not the 1 µA assumption applicable to a different part. Its discrete threshold rows are not silently treated as a continuous AUX specification.

The full guarded digital partition is **2.417189883 A**, inside the unchanged **2.44 A receiving proposal**. The NF RAW5 static/guarded portions are **29.276869 / 35.132243 mA**. These allocations are not measured operating-current bounds. New explicit external READY/FAULT/status load receiving is 0.5 mA: the earlier suggested aggregate 0.3 mA cannot enclose two 15 kΩ host pulldowns plus the declared leakage screen. Including U58, AUX becomes **10.358498 mA normal / 13.718498 mA fault**, guarded, inside new **11/14 mA receiving proposals**. The existing 90 mA source pool has no completed full-temperature aggregate partition; no source-current acceptance is inferred.

The capacity screen remains 37.270336900 W at full 2.44 A / 90 mA pool allocation; the lower BOM subtotal is not used to reduce that planning capacity. The retained 11.4 V / 0.36 Ω constant-power scenario is 2.838846 A at 10.378015 V protected input. Normal feed I²R is not added twice. Fan-limit transient and fault-standby/branch-short heat remain separate incomplete ledgers.

Actual direct RAW5 bypasses are C39/C55 (100 nF X7R) and C97 (100 nF C0G); switched C98 adds another 100 nF. Their partial upper subtotal is 0.465 µF using initial+positive-temperature X7R factors and the C0G ±6% receiving envelope, implying 2.418 µC / 6.2868 µJ at 5.2 V. Internal IC/wire/opto capacitance, ISO startup-current bursts and total inrush remain unknown. Legacy `TOTAL0.22uF` text in inherited C97/C98 values is superseded as a complete-network claim. A proposed FPC_M2 protected branch is not adopted here. The operating feed must originate from P03 J23/J21, never test-only J3.

## Physical and interface scope

`integration-contract.json` carries all actual native connector pins and receiving currents. J6 isolates TMR primary return (`MODULE_INPUT_GND`) from NF quiet AGND; J1.4 stays NC. The primary-current screen is 174.129 mA at 9 V, with unknown input inrush. The approximately 804 Ω feed is on the isolated **secondary**, so it cannot justify primary contact drop. Old J2/J4 1 mm holes are not accepted AWG18 solder interfaces; the independent connector study's new bore/lug/strain proposal remains unimplemented.

Five DCK5 references now use the actual TI DCK0005A drawing: five 0.95×0.40 mm lands, 2.2 mm column centers, 0.65 mm pitch, R0.05, including U58 and the four inherited LVC1G17 drivers. Six DCU and seven DCK6 references retain their corrected manufacturer patterns. The DCK5 primary is [TI SN74LVC1G14](https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf), p34, drawing 4214834/G (11/2024), captured with SHA in `sources/manifest.json`. C99's selected C0G body maximum is 1.8 mm; the old 47 nF body allocation cannot be inherited. U58's DCK5 body maximum is 1.1 mm; seating/solder tolerance remains unaccepted.

The actual courtyard sum is 4532.6832 mm²; ×1.2 = 5439.21984 mm² exceeds the 5075 mm² single-face 2 mm-inset area of the 149×39 proposal. This is an area warning, not a proven packing impossibility. No old 231/233 placement, local bypass geometry, thermal result, airflow or routing is inherited. Full PCB pairing must use actual symbol paths, synchronized FPIDs, and native parity. All fabrication, physical, startup, partial-power, noise, fault-SOA and release gates remain false.

Replays:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest hardware.qualification.boards.startup_negative_circuit.uv_recovery.test_recovery -v
```

Generators reject an existing `handoff.json`; reproduce in a separate copy. `generated/analysis.json`, `generated/equivalence.json`, native raw logs and the package fixture contain the exact comparisons and their scope.
