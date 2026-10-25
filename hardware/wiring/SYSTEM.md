# Standalone system interconnect review

The generated [pin table](generated/system-interconnect.csv) and [source-hashed packet](generated/system-interconnect.json) describe the higher-headroom **external-converter** design. They do not apply to B1 or the onboard-codec profile.

This review covers 320 logical pin pairs across 13 boards: protected input power and readiness, source and protected rails, converter clocks/control and raw analog boundaries, bypass/gain/health interfaces, all 32 front contact functions, ten potentiometers and 96 LED sink channels. With `--kicad-cli`, every saved netlist is compared to a fresh native schematic export. All header nets also match the component manifests; actual PCB header lands are checked where a PCB exists. E25 uses its preserved placement candidate, not in-progress routing.

```sh
python3 -m hardware.wiring.system --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -p test_system_interconnect.py -v
```

Without `--kicad-cli`, the command checks the saved exports and marks fresh native export evidence false. Both modes keep fabrication and assembly release flags false.

## Interfaces that need particular care

The legacy local `5V` coil nets on the input-range, output-stage and sequenced-bypass boards map to **protected `5V_DIG`**. The alias is allowed only at the documented board/header/pin. It does not equate `V5_REG` with `5V_DIG`, and neither protected rail is interchangeable with its `_SRC` input. The processor carrier's documented reset/bypass aliases and the converter-to-ADC driver enable alias are similarly explicit.

The LED driver input has 1.27 mm pitch, while the processor interface has 2.54 mm pitch. Pin correspondence does not make those connectors mechanically interchangeable: the adapter, mating parts and current ratings remain unselected. Raw DAC, ADC and reference interfaces have no qualified cable-length or signal-integrity allowance.

Front controls and lamps use logical contact names. Actual purchased switch, pot, jack, display and LED terminal numbers are **not verified** by this table. The two release selector endpoints remain distinct; asserting both is an invalid state. Returns for the first two button groups are allocated across both ground contacts. This does not qualify return-current paths or contact assemblies.

E11 J4 is optional access to the relay coils already on that board. It is not another relay load or an instruction to add duplicate coils. Raw-rail and interlock diagnostic headers are also kept separate from load power.

## Outstanding assemblies

The packet explicitly lists 24 required unassigned header pins: the two four-pin angle/touch interfaces, eight SD socket interface pins and eight LED-anode supply contacts. Selecting the actual sensors, SD socket and emitter/display assemblies must resolve their terminal numbers, pull-ups, anodes, current/inrush and partial-power behavior.

Every board terminal serving multiple logical conductors appears in the fanout list. The required splice, distribution board or multi-contact assembly has not been selected. Multiple rows sharing a terminal do not authorize crimping several wires into one unspecified contact. There are no wire cut lengths, connector MPNs or production current/resistance ratings in this review.

The failed existing 5 V wiring-loss screens remain in [the source-power review](README.md). The new source-regulation work is a separate candidate; a passing logical pin map does not validate that power architecture. Some analog/converter/monitor/bypass boards still have no routed PCB. Full return topology, shield strategy, harness paths, audio/clock integrity, strain relief, powered operation and physical fit remain open.
