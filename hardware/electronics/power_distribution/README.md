# P01: conditional 5 V source and distribution redesign

P01 replaces the narrow source-voltage budget with a reviewable new-PSU candidate. It preserves the existing targets at the E25 protected-board star: **4.975–5.025 V analog and 4.90–5.10 V digital**. It does not modify or qualify the routed main supply, E25 placement/routing, A11 housing or existing failed harness screen. The candidate needs a new PSU schematic, PCB and mechanical review; the proposed ICs are not drop-in replacements.

```text
VIN_PROTECTED ── new TPS62903 ── 5V_DIG_SRC ── E25 switches ── 5V_DIG star
existing V5_PRE ── new LT3045 ── V5_REG_SRC ── E25 switches ── V5_REG star
       └─ ADR4550B 5V reference ── reused OPA4192 unity SET buffer ── LT3045 SET
```

Both regulator feedback paths stay on the **source side**. Disconnecting E25 cannot open a regulator feedback loop. LT3045 OUTS connects to its local output capacitor; its exposed pad is ground, unlike the existing LT3080 output pad. `spec.py:circuit()` contains a checked replacement pin/net and passive contract. This is not a native schematic, ERC result or PCB.

The [TPS62903 datasheet](https://www.ti.com/lit/ds/symlink/tps62903.pdf), §§5–8, supports external feedback, 3–17 V input and 3 A output. The model uses ±0.9% FB error over its full temperature range, ±70 nA leakage, a 14.7 kΩ + 33 Ω / 2 kΩ divider and ±0.1% total resistor bounds. A 21 kΩ MODE resistor selects external FB/1 MHz/forced PWM without output discharge. Its 50 µF direct-output capacitance limit is an unresolved issue with E25's 4,700 µF bulk: the series-resistance exception does not establish stability for this assembly.

The [LT3045 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/3045fa.pdf), pp3,12,16,23, permits an external SET source that sinks its current and limits fault clamp current. Reusing U5C with local unity DC feedback after 6.8 kΩ isolation avoids the SET-current voltage error of a passive reference connection. The model includes ±2 mV output offset and additional line/load/voltage reserves; changed buffer compensation, minimum effective local capacitance, larger remote bulk and load steps remain unverified.

The [ADR4550B datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/adr4520_4525_4530_4533_4540_4550.pdf), Tables6/9, supplies initial, temperature-box, line and load limits. It is supplied from V5_PRE, avoiding the insufficient headroom of the digital 5 V rail. Assembly shift, thermal hysteresis, humidity and aging have a separate **unqualified ±2 mV requirement**; typical drift graphs are not guaranteed lifetime bounds. The buffer retains the earlier conservative [OPA4192](https://www.ti.com/lit/ds/symlink/opa4192.pdf) offset/bias limits. Input dropout, SET drive/sink/clamp and extra V5_PRE current are calculated independently.

## Distribution requirements and result

The candidate assumes at most 350 mm supply plus 350 mm return conductor, each at least 2.08 mm², and copper at most 85°C. These are routing/selection requirements, not cut lengths or a released wire gauge. Four mated contacts across the source harness must each remain at or below 1 mΩ hot and at end of life. PCB requirements cover source-header copper, E25 and the protected-star spreading region: 4 mΩ total analog or 8 mΩ digital, plus a separate 1 mΩ common-ground transfer bound. The current routed boards/engineering headers do not prove these requirements.

Analog J2 AGND is shared by five rails. The model bounds its return magnitude by their **0.605 A sum**, without relying on cancellation of positive/negative currents. Ground displacement can also raise analog voltage and is included at the high corner. The common-ground error is charged against **2.406 A**, including digital current. Digital and analog power returns must remain separate until the defined star; connecting them elsewhere adds an unmodeled shared segment.

`generated/analysis.json` records independently signed source corners, hot supply/return wire, every contact/copper allocation, FET path, ground transfer, ripple and load-step reserves. Expected allocated protected-star ranges are approximately **4.978–5.019 V analog and 4.902–5.097 V digital**. The baseline sources fail when evaluated through the same complete allocated path. Passing this conditional calculation does not establish that the new parts, harnesses or routed copper meet it.

This target boundary is the **E25 protected-board output star**, before outgoing load connectors and fanouts. The star-spreading copper allowance is not a second harness. Outgoing protected-load harnesses, their additional contacts and endpoint rail voltages require a separate budget. The test suite explicitly demonstrates that an additional pair of connector ends can exhaust the digital margin.

The startup/thermal section keeps full-system holds visible: large-bulk loop stability, late switch closure/inrush, oscillator and inductor limits, total buck loss, PCB thermal resistance, reference aging and partial-power behavior. A slow soft-start calculation only applies when E25 is conducting before the ramp; it does not bound late gate closure. SD-card 3.3 V current/inrush, external logic loads and production fanouts remain unresolved. All physical, fabrication and build-ready flags remain false.

```sh
python3 -m hardware.electronics.power_distribution.analyze
python3 -m hardware.electronics.power_distribution.analyze --check
python3 -m unittest discover -s tests/tooling -p 'test_power_distribution.py' -v
```
