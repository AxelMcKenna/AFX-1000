# E13 independent rail-window monitor

E13 adds a native KiCad schematic for eight independent UV/OV windows. All
sixteen comparator outputs and local supply qualification must be healthy for
`PRE_ANALOG_OK` to reach the E09 converter. A failed window inhibits CHIP_EN,
ANALOG_OK and the E11 processing-input/wet-output drives in the settled model.
The schematic passes zero-violation native ERC and exact exported pin/value
checks for all 181 physical components. It has no PCB or enclosure placement.

This circuit monitors supplies. Main supply generation and overvoltage
disconnects remain unfinished. Removing processing eligibility does not prevent
an excessive rail voltage from damaging an IC. Actual fault response, startup,
partial power and brownout behavior require physical measurement.

## Interfaces and limits

| Header | Pins in order |
| --- | --- |
| J1 | 5V_DIG, V3V3_IO, AGND |
| J2 | P19, AGND, N19, P12, N12, V5_REG |
| J3 | AGND, NBIAS_L, NBIAS_R; bias from E12 J4.3/4 |
| J4 | AGND, PRE_ANALOG_OK; to E09 J5.1/5 |

All grounds share the analog reference; this drawing does not define a split
ground-plane arrangement. Production connectors and physical routing are open.
The following negative-rail numbers are magnitudes.

| Rail | Required normal generation | Conditional accepted fault envelope |
| --- | --- | --- |
| P19, N19 | 18.81–19.19 V | 18.392–19.608 V |
| P12, N12 | 11.88–12.12 V | 11.616–12.384 V |
| NBIAS_L, NBIAS_R | 0.1838–0.256 V | 0.16–0.27 V |
| V5_REG | 4.975–5.025 V | 4.90–5.10 V |
| 5V_DIG | 4.90–5.10 V | 4.70–5.30 V |

E13 distinguishes normal regulation from a wider fault envelope. The earlier
analog circuit records retain their original normal-rail assumptions. E13
re-screens their conditional voltage/headroom allocations across the wider
envelope; it does not establish noise, distortion or guaranteed amplifier swing
there. The master-output headroom allocation has only about 109 mV remaining at
the worst rail, so actual loaded swing and gain/DC tolerance need measurement.

## Circuit

Four TLV1824IDR quad open-drain comparators implement UV and OV checks. An
OPA4192ID inverts the two negative main rails at gain 0.1 and the two negative
bias rails at gain 8.06. REF5025EIDR, the enhanced E-grade reference, supplies
the individual threshold dividers. Comparator outputs each have a 10 kΩ pull-up
to V3V3_IO and independent 20 MΩ positive feedback. They are combined through
four SN74LVC08APWR AND packages. Shared open-drain comparator wiring would
couple the hysteresis and is not used.

Each negative-bias sense input adds at most 27.03 µA to its E12 pump. Combined
with E12's conservative 19.366 mA allocation, this remains below the 20 mA
characterized-load screen. That calculation is not a measured current/ripple
or startup guarantee. Maximum allocated reference load is about 2.914 mA,
below the selected reference's 10 mA rating.

Two TPS3808 supervisors qualify logic power and coarse analog 5 V. The analog
supervisor senses through a divider and has a fixed 300 ms nominal release
delay (180–420 ms bounds). Its earliest release exceeds the allocated 100 ms
reference/amplifier startup. The allocation is unmeasured. A separate final
330 kΩ pull-down and E09's actual 47 kΩ receiver pull-down keep the final static
output load below 100 µA. Full supply-ramp and unpowered-output behavior remains
open.

[F03 firmware](../../firmware/EXTERNAL-CONVERTER.md) waits for chip-ID responses
before configuring the hardware-disabled codec. It probes every 5 ms, requires
20 ms of observed correct responses and faults after five seconds. No GPIO was
added. Configuration and runtime failures still latch dry bypass. The E11/F02
input quiet interval, manual bypass and fresh-permit requirements are retained.

## Conditional allocations

Precision divider and gain resistors are specified as 0.01%, 5 ppm/°C, with a
total 0.1% error allocation including temperature and aging. Exact MPNs are not
selected. Feedback resistors allocate 5% total error. The reference allocates
0.1% total error, including initial, temperature, line/load and an explicit
aging/thermal reserve. Its 2.2 µF output capacitor must retain at least 1 µF
effective capacitance over bias and temperature.

Comparator input offset allocates ±5 mV at 5 V. The manufacturer's full-temperature
±4 mV table is specified at 12 V and its PSRR is typical, so this 5 V bound is
an engineering allocation requiring qualification. Comparator off-state leakage
allocates 1 µA because the cited table lacks a guaranteed maximum. Other bounds
and their use are explicit in [electrical-screens.json](generated/electrical-screens.json).
These assumptions must not be presented as manufacturer guarantees.

## Verification and reproduction

```sh
python3 -m hardware.electronics.rail_monitor.generate
python3 -m hardware.electronics.rail_monitor.verify --kicad-cli /path/to/kicad-cli
```

The [native record](generated/verification.json) covers all package pins,
114 resistor values/paths, 51 capacitor connections/values and 12 IC selections;
eight rail windows across 73,728 allocated corners; positive same-corner
hysteresis; all 131,072 powered combinations of the sixteen window outputs and
coarse qualification; and fresh exported E09/E11/E12 interfaces. Fresh E05/E08
exports support the conditional wider-rail headroom screen. Seventeen stateful
single-fault cases also check the monitor/E09/E11 chain: each comparator or coarse
qualification failure drops input and wet output, clears the latch, restarts
the input timer and prevents a held-high permit from rearming after recovery.
These use nominal discrete timer/latch models and do not establish physical timing.
Logic propagation,
timer dynamics, analog overload, reverse power, reference startup, complete
weighted noise/THD and physical fault timing are not simulated or measured.

Sources, selected package references and unresolved procurement/layout items
are recorded in [dependencies.json](dependencies.json). The review package is
for design review, not fabrication or assembly release.
