# DC01 — combined digital/control schematic

The selected processor carrier, three control expanders and 96-channel LED
driver circuit are combined on three hierarchical sheets. There are **138
electrical parts / 709 exported terminals**. The isolated Linux KiCad 10.0.7
export has **zero ERC findings**, with every category enabled.

Five internal headers are removed: processor J2/J11, control J4/J5 and LED J1.
Fourteen explicit global nets connect the sheets. All other source-local nets
stay separate. Original retained component values, lands and pin nets are
checked independently against the three original exported circuits.

The control reset joins CODEC_RUN, following the existing E18 **external codec
profile, Seed D0**. Manual bypass status joins BYPASS_SENSE. The original LED
series resistors, 3.3-to-5 V translator, blanking and supply supervisors remain;
the merge does not bypass them or connect the 5 V LED outputs to MCU pins.

Reference offsets are processor +1000, controls +2000 and LED +3000.
`construction.json` records every original-to-new reference. Retained external
headers keep their original pin ordering. The AC03 audio connection schedule
still names the earlier development carrier; adopting DC01 for the whole unit
requires remapping its processor peers to J1005/J1006 and renewing the harness
record. There is no approved production harness in this candidate.

The [placed successor](../digital-core-placement-03/README.md) uses these exact
circuits. This schematic's own project intentionally has no PCB.

```sh
python -m hardware.fabrication.audit_digital_core --check
python -m unittest discover -s tests/tooling -p 'test_digital_core_integration.py' -v
```

Power/return routing, LED dissipation and coupling into the pot ADC/reference,
actual parts, connectors, harnesses, installed fit and thermal performance
remain unfinished. ERC and source parity do not qualify circuit operation.
No manufacturing release or order is made.
