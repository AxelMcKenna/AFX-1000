# E10 input-range PCB candidate

This separate **54 × 36 × 1.6 mm, six-layer candidate** implements the unchanged 28-part E10 schematic. Four Ø2.4 mm M2 holes have all-layer copper/via keepouts with 3.7 mm radius. It does not replace the existing A11 `audio_carrier`, which belongs to the output-stage board. This candidate has no assigned housing datum, component-height allocation or physical fit qualification.

The checked copper has **371 segments, 25 conventional through vias, zero native all-severity/all-track DRC or schematic-parity violations, and zero open connections** in KiCad 10.0.7. Native connectivity closure is an engineering milestone, not a fabrication release or measured preamplifier performance.

## Reproduce

```sh
python3 -m hardware.electronics.input_range.pcb.generate --reviewed --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_range.pcb.check --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -p test_input_range_pcb.py -v
```

`reviewed-copper.json` replays the checked copper only after the complete freshly generated placement matches its recorded hash. `generate --route` instead makes a new conservative routing attempt using the shared E25 routing primitives with board-specific rectangular bounds, clearances, drill exclusions and mounting keepouts. Every generation invalidates the existing verification record. A new attempt must pass the independent checker before use.

The preserved placement-only board is `generated/placed.kicad_pcb`; it has 50 connections before routing. Parent circuit values, all component pins, relay contacts, supply polarity, selected footprint names, faces/poses and mounts are independently checked against a fresh native schematic export and E10's authored circuit contract. The checker reports real native opens rather than trusting the route recipe or search-success flags. The six local feedback/output-to-feedback branches also have independent actual F.Cu graph checks: at least 0.25 mm width and a 12 mm construction limit. Those are layout rules, not a stability or bandwidth guarantee.

## Wiring boundary

J1 is `PROC_IN_L / AGND / PROC_IN_R`; J2 is `PRE_OUT_L / AGND / PRE_OUT_R`. J3 requires protected `P12 / AGND / N12`. J4 retains the parent's local `5V / GAIN_LOW` coil interface. The system harness explicitly connects that local `5V` to **protected `5V_DIG`**, never analog `V5_REG` or an unprotected `_SRC` rail. See the [system interconnect review](../../../wiring/SYSTEM.md).

## Remaining qualification

This exploratory routing uses six layers but **does not implement an uninterrupted analog ground plane**. Quiet returns, coil-current segregation, reference planes, amplifier bypass loops, input guards/capacitance, crosstalk, gain/calibration, stability, noise, distortion and overload/partial-power behavior need design review and measurement. Zero DRC does not establish any of them.

Component values and library footprints are inherited interface candidates. Exact passive/header part numbers, effective capacitance, purchased relay/amplifier package tolerances, copper stackup, soldering/stencil details, fasteners, strain relief and actual lead/body heights remain unqualified. The model deliberately leaves `MPN` empty instead of turning a generic resistor value into a purported purchase part number.

`generated/verification.json` fingerprints the current sources, actual PCB, native records and reused helpers. It keeps physical/audio/assembly and build-ready flags false. No board was ordered, powered, placed into the housing or measured in this work.
