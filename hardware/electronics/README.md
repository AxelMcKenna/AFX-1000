# Electronics sources and checks

Each board directory owns its editable KiCad design, generator, BOM, independent verification contract and small generated records. Shared EDA utilities live in `common/`. Board guides describe their current scope and physical checks.

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


## Regeneration

Run tools as modules from the repository root with Python 3.11+:

```sh
python3 -m hardware.electronics.converter.generate
python3 -m hardware.electronics.converter.verify --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -p 'test_*.py'
```

See [audio-design research](../../research/hardware/audio-design-history.md), the [component shortlist](../../research/hardware/components.md), [firmware guide](../firmware/README.md), [validation index](../validation/README.md), and [artifact policy](../../docs/artifacts.md).
