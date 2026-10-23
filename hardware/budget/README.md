# B1: 5 V budget prototype

This is the active lower-cost standalone hardware variant. It keeps the Seed,
engine, 29 effect buttons, ten rotary controls, release sensor, touch strip,
SD sample/User loading and current LED/display scan. The earlier A0.2 high-voltage
carrier remains available under `hardware/electrical`; its BOM is not the B1
shopping list. Neither variant is a completed or reference-matched RMX-1000.

The [cost ledger](cost-report.json) currently targets **NZ$295.77**, including GST
and delivery allowances, free printing, DIY assembly and reused 5 V/1 A USB power
and cables. Only NZ$4.23 remains. This is **not a confirmed delivered supplier
basket**: many rows are allowances, the Seed's NZ listing is a pre-order, and no
PCB revision/replacement budget is secured. See [shopping-list.csv](shopping-list.csv)
and the editable [procurement inputs](procurement.json). All modeled components
are assigned a cost category; bought parts outside the circuit, including the
card, RCA jacks, fasteners, PCB and delivery, are listed separately.

## What changed electrically

Open [budget5v.kicad_pro](budget5v.kicad_pro) for eight circuit sheets and the root
page. [bom.csv](bom.csv) and [connections.csv](connections.csv) describe this variant.
The native schematic check verifies 423 physical components and 1,312 connected
pins, with zero ERC violations across nine pages.

- Regulated **5 V only**, from a captive USB-A power lead with strain relief.
  There is no 12 V input, bipolar converter, high-voltage LDO or MASTER/SEND switch.
  F1 is a 750 mA resettable fuse, followed by the latching SW34 power switch.
  A reused source must supply 1 A and remain within the board's operating limits.
  PTC hold current/temperature, actual load, supply ripple and surge behavior
  remain physical checks. A fuse is not an overvoltage regulator.
- U28 is **TLV9064IDR**, a 5 V quad amplifier. Two channels buffer AC-coupled input
  pads biased to a filtered 2.5 V midrail; two recover output gain, with strapped
  1k calibration trimmers. Input series resistance and rail clamps limit injection
  into the amplifier. They do not establish certified ESD or overload survival.
- RCA is the single unbalanced connector family. Grounds are shared. Recommended
  normal input/output is **-10 dBV (0.316 Vrms)** with programme peaks no higher
  than about **1 Vrms** until measured. This is about 10 dB of intended headroom,
  not the original's 20 dB or +24 dBu maximum-level capability. Maximum clean
  swing, bandwidth, noise, distortion and converter tolerances remain unmeasured.
- K1 alone switches stereo: COM 4/13 are outputs, NC 6/11 are dry inputs,
  NO 8/9 are processed outputs. Its standard 5 V coil is 100 mA nominal at 23 C.
  Q1/HCT drive, the local 3.3 V-loss clamp and drain TVS remain. The three-relay
  high-voltage mute design is not fitted. Pop/click and dropout ordering require
  real measurements; no maximum fault-to-dry time is qualified.
- The original two-stage heartbeat permission/watchdog circuit is retained.
  DSP-ready, digital power-good, manual bypass and reference health must all
  qualify. U32 now monitors the actual midrail with TPS3808G25. The nominal
  10k/10k/100uF reference RC reaches its nominal threshold after about 1.33 s;
  another nominal 300 ms reset delay follows. Divider resistors are 0.1% to avoid
  wasting the low-supply threshold margin. This calculation is not timing closure.
- LED resistors increase from 1k to **3.3k**. The conservative 79-segment current
  calculation is below 50 mA; MCU, SD, IC and touch currents are additional.
  Measure Seed pin-38 current/voltage/temperature and LED brightness before
  accepting the complete load. Do not parallel another regulator into pin 38.
- SD uses **Adafruit 4682**, the 3.3 V native SDIO breakout, not a 5 V SPI-only board.
  The drawing uses module silkscreen terminals: 3V/GND/CLK/CMD/D0/D1/DAT2/D3.
  DET is unused. Keep the Seed-to-module harness very short; the module's built-in
  pull-ups parallel the five external 47k resistors. Verify bus edges and card I/O.

The switch controls the external power feed. The service USB extension must
**disconnect VBUS** while retaining the factory twisted data pair, ground and
shield. Check continuity before use. A direct powered USB cable plugged into the
Seed bypasses SW34; that is a service configuration, not a working power-off test.
DFU through the VBUS-blocked lead still needs board testing. USB audio and USB MIDI
are not supplied by the new power input or by this hardware change.

## Carrier PCB and wiring

[pcb/carrier.kicad_pcb](pcb/carrier.kicad_pcb) contains the audio/power, single relay,
reference health and bypass permission circuits, with 106 circuit footprints plus
four M3 mounting holes. It is **100 x 100 mm, four copper layers**. Inner 1 is the
GND plane; inner 2 carries a 5 V pour and occasional signal escapes. Front/back
carry signals. Ground/power pads have explicit stitching where needed. The
layout checker verifies every saved pad/net/value/footprint against the circuit
subset and runs native DRC without custom exclusions. The current-source record
is [pcb/native-check.json](pcb/native-check.json). Clean DRC does not qualify
analogue stability, EMI, return-current behavior or manufacturer dimensions.

The Seed, button/pot/LED assemblies, SD breakout and touch breakout are offboard
wired assemblies. SW32 and SW34 are panel switches. Intersheet power/audio headers
on the carrier can be used as test points or solder-wire interfaces rather than
buying a connector pair for every drawing boundary. Use the named pin order:

| Carrier / interface | Connect to |
| --- | --- |
| J_PWR1 | Captive USB supply 5 V / GND |
| J_SW1 | SW34 latching power switch |
| J_BYP1 | SW32 manual bypass; closed connects MANUAL_N to GND |
| J_PWR2 | Seed physical 39 VIN / 40 GND / 38 3.3 V output |
| J_AUD1 | Seed physical 16 ADC-L / 17 ADC-R / 18 DAC-L / 19 DAC-R / 20 AGND |
| J_BP2 | Seed D28 heartbeat / D17 DSP-ready / GND |
| J_IN1 / J_IN2 | Left / right RCA input tips and sleeves |
| J_OUT1 / J_OUT2 | Left / right RCA output tips and sleeves |
| J_CPU1 / J_BTN1 | Four-HC165 button assembly, unchanged GPIO/scan order |
| J_CPU2 / J_ADC1 | Two-HC4051 pot assembly, unchanged GPIO/scan order |
| J_CPU3 / J_LED1 | Twelve-HC595 LED assembly, 3.3k resistors |

The native board check covers the carrier subset. It is not an automatic whole-
assembly schematic-parity or physical harness test. Source/pad checks reject
changes to the PCB, layout generator or checked circuit inputs. No PCB has been
ordered, assembled or flashed. Review component orientation/dimensions and the
assembly drawing before prototype fabrication; no production release is implied.

Gerbers, plated/non-plated drill files and drill maps are available in
[fabrication-draft](pcb/fabrication-draft/README.txt) for engineering review.
`tools/export_budget_pcb.py --cli /path/to/kicad-cli` recreates them only after
the current PCB evidence passes. Its export record hashes the board and outputs.
These files still require stackup, component and assembly review before ordering.

## Printing and fit

[mechanics.json](mechanics.json) defines B1 rear ports and carrier mounts while
retaining all front controls. [cad/enclosure.scad](cad/enclosure.scad) includes
split panel/tray exports, seam joiners, printable knobs/buttons and a lever handle.
The two approximately 167 x 157 mm halves fit a 220 mm bed. Four joiner plates
connect the panel and floor seams with M3 fasteners. Carrier posts match the PCB's
4 mm-inset mounting holes at an enclosure origin of [194,8] mm.

The independently generated flat fit parts are ready for *fit inspection*:

- [Left panel](generated/panel_left.stl), [right panel](generated/panel_right.stl)
- [Seam joiner](generated/joiner.stl), print four
- [Shaft coupon](generated/shaft_coupon.stl), test 6.0/6.1/6.2 mm bores first
- [Panel drawing](generated/panel.svg) and [DXF](generated/panel.dxf)

Their planar constraints, enclosed volume and two-faces-per-edge mesh checks pass;
source/output hashes are in [flat-mesh-check.json](generated/flat-mesh-check.json).
They were meshed using Shapely plus the system GLU tessellator. The full tray,
knobs/buttons and lever SCAD solids have **not** been rendered/validated: the
pre-existing OpenSCAD bundle fails code-signature verification and was not run.
No download warning or signature check was bypassed.

The 24 mm pot bodies are accounted for in panel clearance checks. Shaft lengths,
anti-rotation features, exact selector/tactile/display bodies, touch lens, spring
geometry, wire strain relief, print tolerances and underside interference still
need purchased-part checks and a physical fit print. The lever handle is only one
part: it needs a shaft coupling, return spring and stops that avoid loading the
pot's internal stops. Adjust the cap stem length to the actual button board.

## Calibration and boot behavior

Firmware now reads optional `RMX/CALIB.TXT` before audio. It is separate from User
settings and does not restore pressed buttons or engage effects. Example:

```text
RMX_CAL 1
pot 2 1500 31000 62500
pot 9 64000 36000 2000
```

Rows contain `pot CHANNEL END0 CENTER END1`, as unsigned 16-bit ADC readings.
Channels follow `hardware/prototype.json` / `BoardConfig.h`: 0 input, 1 output,
2 low, 3 mid, 4 high, 5 Scene, 6 Sub1, 7 Sub2, 8 X-level, 9 pitch, 10 release.
END0/END1 can be reversed. Low/mid/high/pitch map the measured center to exactly
half travel; other controls use a linear endpoint map. Supply a center between
the endpoints even for linear controls. A minimum 1024-count span and 256-count
center margins reject broken/noisy calibration entries. Omitted channels retain
nominal full travel. These examples are format examples, not measured values.

The parser is bounded to 1024 bytes and allocates no dynamic storage. File/read/
format failures leave the prior candidate unchanged; the FatFS adapter commits
only after successful close. Calibration errors contribute to the existing card
error indication. `USER.TXT`, calibration and sample loading remain independent;
live card insertion and saving changed calibration from the panel are unfinished.
Measure endpoints using a debugger/ADC instrumentation before installing real
values. The digital calibration does not replace analogue unity adjustment.

The stereo output now fades up over 2400 frames at 48 kHz (50 ms). DSP-ready is
withheld until 38 complete 64-frame callbacks have elapsed. This soft fade and
the midrail health delay reduce startup risk but do not prove pop-free operation.
The foreground still withdraws ready on stalled audio and stops heartbeat when
callbacks stop. Original watchdog pulse/startup/tolerance limitations still apply.

With input/output software gains at unity, all effects neutral and a 10k-or-greater
load, feed a measured 1 kHz 0.316 Vrms signal. Verify dry continuity first, then
measure processed output after reference/DSP-ready qualification and adjust
RV20/RV21 for unity. Compare both channels over frequency and level. Check the
actual ADC/DAC scale/impedance before changing resistor values. Never connect
speaker-level outputs or a +24 dBu test signal to this consumer-level prototype.

## Reproduce and check

```sh
python3 tools/generate_budget.py --check
python3 tools/generate_budget_mechanics.py --check
python3 tools/budget_cost.py --check
python3 tests/budget_tests.py
python3 tools/check_budget.py --check
python3 tools/check_budget_pcb.py --check
cmake -S . -B build
cmake --build build -j4
ctest --test-dir build --output-on-failure
make -C firmware/daisy -j4
python3 tools/check_firmware.py --check
```

To regenerate evidence, run `check_budget.py --cli /path/to/kicad-cli`; run
`layout_budget.py --footprints /path/to/KiCad/footprints` with KiCad's Python,
then `check_budget_pcb.py --cli /path/to/kicad-cli --python /path/to/KiCad/python`.
`generate_budget_mechanics.py --stl --preview` needs Shapely and macOS GLU (or
libGLU elsewhere). It generates only the four flat fit meshes, not full SCAD solids.
The earlier A0.2 checks remain separate and must continue to pass.

Before any claim of a completed clone, perform powered/unpowered audio and clamp
measurements; 3.3 V/current/thermal/ADC/SD/USB checks; real boot, ISR/foreground
stall and power-loss bypass injection; actual callback/stack/SDRAM tests; a two-
hour live soak and reference-unit DSP/interaction comparisons. USB MIDI, original
SD/RSD compatibility, full lighting feedback and original effect behavior remain
tracked in the main clone roadmap. No physical test is claimed by a host/DRC pass.
