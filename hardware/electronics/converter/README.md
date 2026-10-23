# E09 converter core, clock and qualification

E09 is a **60-component native schematic prototype** for the ES9292QPRO core,
local analog regulators, oscillator and hardware qualification. Native ERC and
independent exported pin/value checks pass. This is not a running external-codec
implementation: there is no PCB or enclosure placement. The default firmware
uses the Seed3 onboard codec; the separate [F01 adapter](../../firmware/EXTERNAL-CONVERTER.md)
now cross-compiles for E09, with host-tested startup/qualification policies.
Neither profile has run on hardware.

Open the [KiCad project](converter.kicad_pro),
[schematic view](generated/converter.svg), [BOM](bom.csv),
[pin schedule](components.json), [verification record](generated/verification.json),
[electrical screens](generated/electrical-screens.json) or
[proposed MCU interface](interface-plan.json).
The [E09 review bundle](../../cad/generated/standalone-review-E09.zip) includes
this work alongside E08 and the existing A03/E07 CAD/output PCB.

## Core and supplies

U1's 49 physical pins follow the ESS pin table, including reserved RT1 and the
grounded exposed pad. REXT is intentionally unconnected, selecting internal
fixed 3.3 V references with AVCCH at 4.5 V. Reference decoupling follows the
manufacturer's software-mode drawing: specified tantalum and C0G pairs are kept
distinct from ordinary X7R decoupling. Tantalum positive pad 1 is marked in the
symbols and schedule; exact capacitor MPNs, ESR and effective values are open.

**The codec footprint is unassigned.** The public v0.1 document identifies a
7 × 7 mm 48-QFN and ground pad 49 but does not provide the referenced dimensioned
land/exposed-pad drawing. Obtain that drawing before assigning and routing the
package. A generic QFN outline is not evidence of compatibility.

TPS7A2033PDBVR and TPS7A2045PDBVR generate local A3V3 and A4V5 from an internal
**4.90–5.10 V regulated rail**. This is not the raw adapter input. That lower
bound preserves the regulator's stated accuracy conditions for the 4.5 V output;
an unrestricted USB 5 V source does not meet this contract. The 30 mA and 100 mA
load allocations are design budgets, not guaranteed measured codec currents.

V3V3_IO must be the MCU's own 3.3 V logic domain; it supplies AVDD, oscillator
and qualification logic. Do not connect independent 3.3 V regulator outputs
together. Check the module's available rail-current budget before powering this
load from it. Internal DVDD and reference outputs are decoupled outputs, not
external supply inputs. The eventual mixed-signal PCB needs continuous return
paths and placement review; all local grounds currently share AGND by name.

## Clock and serial interface

Y1 is ECS-2520MVLC-245.7-BN-TR, a 24.576 MHz oscillator explicitly listed by
ECS. The codec is the audio-clock master: divide by 8 for 3.072 MHz BCLK and use
two 32-bit slots for 48 kHz stereo frames. The MCU uses SAI2 dual-slave operation,
with Block B receiving external clocks and Block A synchronized internally.
This keeps MCLK synchronous with the serial clocks, as ESS requires.

The first-year frequency screen combines 50 ppm stability and 3 ppm aging,
giving approximately 47,997.46–48,002.54 frames/s. The 15 pF load, 45–55% duty
cycle, actual edge timing and signal integrity need validation on the PCB.
The oscillator's 150 fs typical jitter is specified at 50 MHz; it is not a
24.576 MHz guarantee. The current SDK also marks its 32-bit SAI mode untested.
ESS's performance table used a 49.152 MHz evaluation-board clock. The supported
24.576 MHz clock plan establishes clock ratios, not an equivalent measured
DNR/THD result; the original audio targets still require measurement.

ESS's I²C table lists **8-bit wire addresses**. Figure 4 shows write 0x30 and
read 0x31 with both address pins low, so the firmware API uses **7-bit 0x18**.
Chip ID is 0xAF at register 225. This does not conflict with the existing
0x20/0x21 controls, 0x30 touch module or 0x36 angle sensor. Only one pullup pair
should be fitted for the complete bus; account for module pullups in parallel.
The modeled 2 kΩ pair allows about 175 pF for a 300 ns rise-time budget.

| Boundary | Connection |
| --- | --- |
| J1 | Same five pins/order as E08 J1: DAC_LP, DAC_LN, AGND, DAC_RP, DAC_RN |
| J2 | ADC_LP, ADC_LN, AGND, ADC_RP, ADC_RN, REF_ADC1, REF_ADC2; input stage unfinished |
| J3 | AGND, BCLK, WS, ADC_DATA, DAC_DATA; short synchronous audio connection |
| J4 | V5_REG, AGND, V3V3_IO; internal regulated inputs |
| J5 | AGND, SCL, SDA, CODEC_RUN, PRE_ANALOG_OK, ANALOG_OK, CODEC_PGOOD, CHIP_EN |

Reference outputs on J2 may only feed a qualified high-impedance bias circuit.
The raw DAC/ADC headers describe board boundaries; they do not approve long
analog harnesses. DAC_DATA needs source termination on the MCU carrier.

## Qualification and firmware requirements

Three TPS3890 supervisors qualify IO 3.3 V, A3V3 and A4V5. Their open-drain
outputs form CODEC_PGOOD. Schmitt logic requires both that signal and the external
PRE_ANALOG_OK before CODEC_RUN can raise CHIP_EN. PRE_ANALOG_OK must come from
independent monitors of all ±19 V/±12 V rails. A missing connection is pulled low.

Firmware must configure GPIO3 as clock-valid and GPIO4 as both-channel
soft-ramp-done. Both pins are pulled low while unconfigured. Those flags and
CHIP_EN enable the qualification timer. A final AND removes ANALOG_OK when any
live qualifier falls, independently of the timer's output delay. ANALOG_OK feeds
E02 J3 pin 3; E02's watchdog and edge-armed permit latch remain in the path.

The 2.2 µF timer capacitor requires **1.5–2.8 µF effective capacitance**, with
total injected leakage bounded to ±100 nA. Using TPS3890 threshold/current
bounds gives 1.21 s minimum, 2.35 s nominal and about 4.52 s maximum. This exceeds
E08's one-second settling allocation, conditionally on those component limits.
The capacitor MPN/bias/temperature/aging qualification is not complete.

The verifier checks 256 powered logic combinations, 16 divider corners and five
event-level faults. These are not CT-discharge, sub-microsecond glitch,
power-ramp or transistor simulations. Normal recognized reset intervals and
actual clock-loss/ramp behavior still require bench tests. Voltage qualification
here detects undervoltage; it does not establish overvoltage or raw-pin fault
protection.

The [interface plan](interface-plan.json) allocates all 31 module GPIOs without
overlap. D25–D28 become SAI2. D29 carries the direct processing permit, D30 reads
latch Q, and D0 requests codec run while sharing the MCP reset line. An additional
MCP23017 at 0x22 reads connection mode, bypass sense and ANALOG_OK. Its control
PCB remains unfinished. The historical E09 JSON describes the proposal; F01 now
implements a separate matching firmware profile. The onboard build retains its
original wiring. F01 requires a receiving-end pull-down on the new status input.

**The new adapter must read ANALOG_OK high before attempting to arm E02.**
The existing prototype's startup/350 ms rearm behavior is not sufficient for
this circuit and can time out waiting for latch feedback during expected
qualification. On reconfiguration, first remove permit and hold CODEC_RUN low
for at least 20 ms. Complete muted codec setup, register readback, silent SAI
startup and qualification before audio is enabled. The JSON contains requirements,
not an executable register-write recipe.

## Geometry, checks and remaining work

The generic KiCad WSON-6 footprint enlarges pin 1; TI's TPS3890 example enlarges
pin 2. E09 supplies original [DSE copper geometry](RMX_Converter.pretty/TI_DSE0006A_TPS3890.kicad_mod)
and checks its six pads against that drawing. The oscillator's rotated land
geometry is also checked. Mask, paste, assembly process and actual fit remain
unqualified. All other assigned footprints remain candidates; the codec's is
deliberately blank.

    python3 -m hardware.electronics.converter.generate
    python3 -m hardware.electronics.converter.verify --kicad-cli /path/to/kicad-cli

The generators use Python's standard library and external KiCad libraries.
The pin-plan resource audit checks the pinned SDK when it is locally available;
the SDK is external to the review archive. Source/library and
[primary-document hashes](dependencies.json) are recorded. Persist edits in
spec.py/generate.py; regeneration replaces the schematic.

Complete the ADC/input circuit, raw-pin protection, external power converters
and rail monitors, physical validation of the F01 codec/SAI adapter, package drawing and
integrated PCB placement/routing. Then verify gain/calibration, noise/THD,
latency, clocking, startup/fault response, thermal behavior and real control fit.
E08/E09 parts are not covered by the current A03/E07 enclosure clearance report.

Primary sources: [ESS ES9292PRO](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf),
[TI TPS7A20](https://www.ti.com/lit/ds/symlink/tps7a20.pdf),
[TI TPS3890](https://www.ti.com/lit/ds/symlink/tps3890.pdf),
[ECS oscillator](https://ecsxtal.com/store/pdf/ECS-2520MVLC.pdf),
[TI HCS08](https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf),
[TI LVC1G08](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf).
