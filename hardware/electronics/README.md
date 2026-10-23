# Electronics sources and checks

Each board directory owns its editable KiCad design, generator, BOM, independent verification contract and small generated records. Shared parsing, solvers, symbols, placement and provenance utilities live in `common/`. Board guides record the current scope and remaining physical checks.

The [E21 power-load review](POWER-LOAD-E21.md) includes E20's driver load and
revises the supply, input ramp/current and digital switch bank. Conditional
screens pass; full startup, stability, thermal, layout and physical work remain open.

The [E23 input/protection PCB](input_protection/README.md) routes the 48-part
input circuit. Its native checks cover connectivity, geometry and parity;
conditional A07 rear-panel integration passes modeled clearance checks.
Physical power/protection and assembly qualification remain open.

[E24 main-supply placement](power_supply/README.md) adds all 157 supply components
on a six-layer 84 × 38 mm candidate. Nonrouting native DRC and parity pass;
333 open connections remain in that preserved snapshot. The separate
[current copper work](power_supply/routing/README.md) has 219 segments/53 vias
across both bucks, a filled ground region and 273 open connections, with zero
native DRC/parity issues. Its 53 path checks and 36 tooling tests pass. The 5.8 V
pre-rail feeds the 5 V linear-regulator IN lands and engineering test header;
separate feedback and quiet returns are included. Raw generators, linear/
precision stages, actual copper/reference loss, loop/thermal/EMI and housing/
physical qualification remain unfinished.

| Board | Scope |
| --- | --- |
| [output_stage](output_stage/README.md) | Output drivers and gain switching |
| [bypass](bypass/README.md) | Independent watchdog/relay drive |
| [audio_bypass](audio_bypass/README.md) | Stereo bypass contacts |
| [button_test](button_test/README.md) | Passive button-fit fixture |
| [dac_receiver](dac_receiver/README.md) | DAC I/V and receiver |
| [input_range](input_range/README.md) | Input range and preamplifier |
| [converter](converter/README.md) | Converter and startup qualification |
| [sequenced_bypass](sequenced_bypass/README.md) | Input/relay sequencing |
| [adc_driver](adc_driver/README.md) | ADC drivers and bias |
| [rail_monitor](rail_monitor/README.md) | Rail and bias monitoring |
| [power_supply](power_supply/README.md) | Main rail generation |
| [input_protection](input_protection/README.md) | Input protection |
| [rail_disconnect](rail_disconnect/README.md) | Rail disconnects and interlocks |
| [control_inputs](control_inputs/README.md) | Digital control-input hub |
| [processor_carrier](processor_carrier/README.md) | Processor and knob carrier |
| [led_driver](led_driver/README.md) | 96-channel LED/display driver; supply integration open |

## Regeneration

Run from the repository root with Python 3.11+. Supply the native KiCad CLI path when required:

```sh
python3 -m hardware.electronics.converter.generate
python3 -m hardware.electronics.converter.verify --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -p 'test_*.py'
```

PCB routing additionally requires the dependencies documented by each board. Generators and verifiers retain small review drawings, exported netlists and verification JSON in their board's `generated/` directory. Editable KiCad files remain tracked. Large release archives and mechanical exports follow the [artifact policy](../../docs/artifacts.md).

The earlier E01–E19 circuit, converter, gain and noise discussion is preserved as [audio-design research](../../research/hardware/audio-design-history.md). The [component shortlist](../../research/hardware/components.md), [firmware guide](../firmware/README.md) and [validation index](../validation/README.md) provide the related system context. Historical stage descriptions are retained in the research notes; use each board's guide for its current implementation and limitations.
