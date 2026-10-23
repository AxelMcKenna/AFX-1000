# E11 independently sequenced stereo bypass

E11 implements the independent input-settling circuit required by E10 and its
matching F02 status interface. It replaces the E02 driver and E03 contact
projects **for the external converter profile**. Those projects remain historical
and retain the default onboard bring-up wiring. Do not combine their duplicate
relays, drivers or logic with E11. This is an editable schematic prototype;
there is no E11 PCB or complete enclosure placement.

The [native schematic](sequenced_bypass.kicad_sch) contains 55 physical components:
watchdog and supply supervisors, Schmitt logic, an edge-armed output latch,
three MOSFET coil drivers, two stereo relays and a separate input timer.
The [integration contract](integration.json), [BOM](bom.csv),
[exported circuit](generated/sequenced_bypass.svg) and
[verification record](generated/verification.json) describe this revision.

## Operating sequence

K1's released contacts connect dry input directly to output. K2's released
contacts disconnect the processing input. With healthy 3.3V/5V, a live audio
watchdog and E09 ANALOG_OK, Q3 independently energizes K2. K1 remains dry while
the input settles. Both gain-request edges restart qualification. Manual bypass
clears K1's output latch directly but leaves K2 connected while health is valid;
this keeps the input warm for a quick return from bypass.

U7 is an LTC6994-1 with rising-edge delay, DIVCODE6/POL0, divider262144 and
383kΩ RSET. The programmed delay is 2.008s. A recognized low input immediately
removes readiness and the next high starts a full new interval. This avoids
depending on complete discharge of a large timing capacitor after a short reset.
The [manufacturer datasheet, pages12–14](https://www.analog.com/media/en/technical-documentation/data-sheets/LTC6994-1-6994-2.pdf)
defines that counter-based qualification behavior.

The [conditional timing screen](generated/electrical-screens.json) uses the
**3% full-temperature IC limit**, plus a 1% total RSET allocation, giving
1.928–2.089s. Reserving 50ms for relay closure/bounce leaves at least1.878s
after input connection, above E10's required1.2s. The resistor, mechanical
and operating-condition allocations still require parts selection and measurement.
The relay's published rated-condition switching time is not a universal
temperature/voltage/bounce guarantee.

U7 transfers its current input at the end of power-up initialization without
waiting a full programmed delay. Therefore U4's CT is connected to3.3V through
100kΩ, selecting a guaranteed180–420ms reset-release interval. That holds
TIMER_ENABLE low while U7 starts. **U7 startup≤100ms is a design allocation**,
not a manufacturer-specified maximum; scope tests over ramps/dips are required.
Do not accept the circuit solely from the nominal startup graph.

R15/C9 and the Schmitt XOR detect isolated rising/falling gain steps. The
datasheet doesn't give a guaranteed3.3V threshold table. The screen explicitly
assumes thresholds within0.25–0.75 of VIO, effective C9 within0.7–1.3µF, bounded
GPIO levels and input leakage. Its reset-pulse bounds are conditional on that
envelope. U7's published5ns pulse recognition is typical; the design allocates
recognition of pulses≥100µs. Qualify real pulse trains, gain-contact bounce,
brownout recovery and glitches on hardware. This is not arbitrary-glitch proof.

INPUT_READY and PROCESS_OK asynchronously clear the latch when unqualified;
the final output drive is also directly AND-qualified. If MCU_PERMIT is held
high through a fault or settling interval, readiness recovery cannot rearm Q.
A fresh permit edge is required. Firmware adds1,250ms continuously high status,
then the existing350ms stable rearm before that edge. See the
[F02 firmware guide](../../firmware/EXTERNAL-CONVERTER.md).

## Interfaces

| Connector | Pins in order |
| --- | --- |
| J1 power | 5V, AGND, 3V3; regulated inputs only |
| J2 MCU/rear | AGND, heartbeat D13, permit D29, gain D9, latch Q D30, bypass sense MCP0x22 GPA1 |
| J3 qualification/manual | 3V3, PROCESS_OK closed-contact loop, ANALOG_OK, AGND, BYPASS_SENSE |
| J4 optional coil access | 5V, BYPASS_LOW, 5V, INPUT_LOW; accesses the included K1/K2, never duplicate remote coils |
| J5 gain coils | 5V, GAIN_LOW; E05 J3 and E10 J4 |
| J6 input status | AGND, INPUT_READY to MCP0x22 GPA3 |
| J7 line input | IN_L, AGND, IN_R; source selection/normalling is upstream |
| J8 line output | OUT_L, AGND, OUT_R |
| J9 analog stages | PROC_IN_L, AGND, PROC_IN_R to E10 J1; PROC_OUT_L, AGND, PROC_OUT_R from E05 J2 |

GPA3 needs a **270kΩ receiving-end pull-down** and no internal pull-up. The
static HCS output-load screen remains below20µA including its downstream gate
and allocated MCP input leakage. ANALOG_OK on GPA2 keeps its separate47kΩ
receiving pull-down. Both belong on the unfinished control/status PCB. The Q
feedback pin senses the logic latch, not actual relay contact closure.

All returns share AGND. This name does not create a separate logic ground or
justify routing coil currents through audio reference paths. Place local bypass
capacitors at their ICs and keep coil loops, TVS returns, timing SET/DIV traces,
clocks and audio paths appropriately separated on the future PCB. J4 is optional
test/access wiring; production connector and harness parts remain unselected.

## Verification and remaining work

```sh
python3 -m hardware.electronics.sequenced_bypass.generate
python3 -m hardware.electronics.sequenced_bypass.verify --kicad-cli /path/to/kicad-cli
python3 hardware/firmware/verify.py --toolchain /path/to/arm-toolchain/bin
```

Native KiCad10.0.7 ERC has zero violations. The verifier checks every exported
component value and pin, including intentional NC pins, all256 powered Boolean
combinations, seven stateful startup/fault/gain sequences, fresh E10/E05/E09
interfaces, nominal relay land geometry and native footprint pad numbers.
Timing screens include16 divider and512 conditional gain-RC corners.
All eight firmware host suites pass, and both actual ARM profiles build.

These checks do not simulate propagation races, coil/contact dynamics,
unpowered CMOS/MOSFET behavior, welded contacts or actual audio transients.
Exact passive qualification, PCB routing, rail generators/monitors, ADC driver,
complete enclosure/wiring fit and physical power/bypass/audio measurements remain
open. The existing A03/E07 clearance record excludes E08–E11 components.

Primary references: [LTC6994 Rev.C](https://www.analog.com/media/en/technical-documentation/data-sheets/LTC6994-1-6994-2.pdf),
[SN74HCS86 Rev.C](https://www.ti.com/lit/ds/symlink/sn74hcs86.pdf),
[TPS3808 Rev.N](https://www.ti.com/lit/ds/symlink/tps3808.pdf),
[G6K relay](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf).
Source provenance and unselected parts are recorded in [dependencies.json](dependencies.json).
