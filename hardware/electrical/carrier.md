# Carrier A0.2

This is a pin-connected electrical design draft for the standalone clone. It is
not a PCB or fabrication release. The nine schematic files use embedded pin-block
symbols; eight are new carrier sheets and one is the existing bypass permission
sheet. Physical terminal identifiers are used where a manufacturer part is fixed.
Display, switch, jack and breakout **terminal labels** remain explicitly identified
where a numerical footprint has not been selected.

`tools/generate_carrier.py` is the source for the eight new circuits. It emits each
sheet's KiCad schematic, SVG, JSON and BOM, plus the consolidated
`carrier-bom.csv`, `carrier-connections.csv` and `carrier-inventory.json`. These
aggregate files include the bypass permission sheet. `hardware/bom.csv` mirrors
the consolidated component BOM, replacing the older high-level parts estimate.
The integrated [carrier.kicad_pro](carrier.kicad_pro) opens
[carrier.kicad_sch](carrier.kicad_sch) and nine generated child sheets under
`carrier/`. Harness nets use global labels; other nets stay local. The original
independent sheets remain available for bench inspection. Equal labels on
independently opened sheets do not connect them: use the integrated project for
system checks, and assemble the named harnesses below for a wired prototype.

KiCad 10.0.7 imported the integrated design and reported zero ERC violations
without exclusions. Its exported netlist was checked against all 470 physical
components and 1,486 connected pins, including cross-sheet connections. All 333
assigned footprints have matching pad-number sets; **137 physical components
still have no footprint**. Matching pad numbers does not establish dimensions,
orientation, manufacturer pin assignment or mechanical fit. Ten native pages
were plotted and inspected. The [native record](native-check.json) ties these
results to source hashes; `tools/check_carrier.py --check` rejects stale evidence.

## Circuit set

| Drawing | Circuit |
| --- | --- |
| [compute-storage-touch.svg](compute-storage-touch.svg) | 40 physical Seed pads, SDMMC socket contacts and pull-ups, MPR121 breakout, eight electrodes, USB extension and chassis bond |
| [button-inputs.svg](button-inputs.svg) | Four 74HC165, 32 pull-ups, 29 buttons and two selector switches |
| [analog-controls.svg](analog-controls.svg) | Two 74HC4051, eleven pots/lever channels, input RC filters and grounded spare channels |
| [led-drivers.svg](led-drivers.svg) | Twelve 74HC595, 96 current-limiting resistors, 55 LED positions, three common-cathode digits and reserved outputs |
| [line-audio.svg](line-audio.svg) | Passive ADC pads, RCA/TS connections, four-pole gain mode switch, LME49860 output recovery gain, trims and AC coupling |
| [carrier-power.svg](carrier-power.svg) | Fused/switched external 12 V DC, reverse-polarity diode, 5 V buck, isolated positive/negative 24 V modules and approximately ±20 V post-regulation |
| [analog-health.svg](analog-health.svg) | Both analog rail comparators, monitored 2.5 V reference and delayed health output |
| [bypass-permission.svg](bypass-permission.svg) | Watchdog, manual bypass, supply supervision and two fresh heartbeat edges before permission |
| [relay-audio.svg](relay-audio.svg) | Three DPDT relays, two coil drivers/clamps, input mute and delayed output reconnect |

## Wiring between sheets

Numbers in each connector follow the schematic's pin order. Use straight-through
harnesses, not visually mirrored pin numbering. GND pins are separate conductors
where repeated. The carrier tests check these pin-for-pin pairings against the
emitted CAD, including the four connections to the bypass sheet.

| From | To | Purpose |
| --- | --- | --- |
| J_CPU1 | J_BTN1 | Button chain |
| J_CPU2 | J_ADC1 | Pot muxes |
| J_CPU3 | J_LED1 | LED chain |
| J_CPU4 | J_BP2 | Heartbeat / DSP ready |
| J_CPU5 | J_PWR2 | Seed VIN, GND and **3.3 V output** |
| J_CPU6 | J_AUD1 | Codec I/O and audio ground |
| J_PWR3 | J_BP1 | Bypass power |
| J_PWR4 | J_RY1 | Coil/logic power |
| J_PWR5 | J_AUD2 | Analog rails |
| J_PWR6 | J_HL1 | Rail monitor power/sense |
| J_HL2 | J_BP3 | Analog health |
| J_BP4 | J_RY2 | Relay permission |
| J_AUD3 / J_AUD4 / J_AUD5 | J_RY3 / J_RY4 / J_RY5 | Dry / wet / output audio |
| J_AUD6 | J_RY6 | DAC and line-amplifier mute |

The header-based circuit split is for engineering inspection and bench assembly.
It does not prescribe eight separate PCBs. Partition the finished layout into a
rear audio/power carrier and a panel control assembly after actual component
dimensions and return-current paths have been reviewed.

## Bypass and mute sequence

K1/K2 are standard **G5V-2 DC5**, not the H1 high-sensitivity variant. They select
dry on NC and processed on NO. K3, also G5V-2 DC5, grounds both line-amplifier
inputs while de-energized. It connects AC-coupled DAC audio when permission rises.
U33 then releases the output-relay enable after its nominal 20 ms reset delay.
This is intended to let K3 operate before the output contacts connect; the delay
tolerance, contact bounce, amplifier settling and audible clicks still need
measurement. Fault assertion is immediate in the supervisor model; mechanical
release and coil discharge add their own delay.

U35 is **74HCT14**, powered at 5 V. Two Schmitt inverters buffer each control
without inversion, accepting the slowly rising 3.3 V supervisor output and giving
the coil MOSFETs more gate margin. HC is not a valid substitution here. Each
DMN3023L has a local 100k gate pull-down and 10k series drive resistor. Separate
5 V-powered TPS3808G33 outputs clamp the two gates if 3.3 V falls. Sharing one
clamp drain between the gates would short their controls and defeat the delay.

At the initial 23°C coil-resistance limit, three coils draw up to 350 mA at 5.25 V.
This is **not** a cold-temperature maximum. Copper resistance and coil self-heating
must be included in the final power budget. Q1 drives two coils; Q2 drives one.
The initial gate calculation uses a conservative 3.7 V buffered high, 1% resistor
limits and a 2 µA leakage budget, giving more than 3.3 V on-state gate drive. The
clamp sink remains below the supervisor's 1 mA test condition. These are static
calculations, not a full brownout or transistor-temperature qualification.

D1/D2 are Littelfuse SMAJ12A unidirectional TVS parts, cathode at the MOSFET drain
and anode at ground. Their specified 25°C clamp is below the MOSFET's 30 V rating.
Inductive energy, temperature derating and wiring overshoot remain unmeasured.
Do not infer installed relay release time from the unsuppressed relay datasheet,
or infer a maximum complete fault-to-dry latency from nominal watchdog timing.

## Audio and gain modes

The RCA/TS interface is unbalanced. The relay sheet preserves two switched
conductors per channel, but this line sheet explicitly bonds its N conductors to
ground through six 0-ohm straps. It is **not a balanced line receiver/driver**.
Use one input connector family at a time; the circuit does not mix two sources.
Automatic L(MONO)-to-R jack normalling remains unimplemented.

The pad uses the manufacturer's **typical** Rev7 Seed input impedance of 13.6k,
not an assumed infinite ADC load. In MASTER, 680k and 2.87k shunts are in parallel;
SEND/RETURN disconnects the 2.87k shunt. With 22.1k series resistance, both modes
present more than 22k to the source. Assuming 3.6 Vpp ADC full scale, their intended
20 dB headroom points stay below 1.8 V peak at a typical codec impedance, including
initial 1% pad-resistor limits. Codec impedance/level tolerances, transient clamps,
connector ESD and input overload survival are **not qualified** by that calculation.

The output uses the active tape-and-reel **LME49860MAX/NOPB** orderable variant;
the MA tube variant is listed obsolete by DigiKey. Its supply must be the
post-regulated rails, never raw ±24 V. The base feedback path remains connected
during mode switching; SEND adds a parallel feedback branch. Each trim has its
wiper strapped to an end. The 100-ohm series output resistor isolates the cable,
and a 22 µF bipolar capacitor blocks DC. The exact capacitor and its dimensions,
frequency response, leakage and pop behavior still need selection/testing.

The nominal gain calculation includes 100-ohm DAC source impedance, the 47k/100k
input loading, 100-ohm output isolation and a 10k external load. The trim ranges
cover unity at the manufacturer's typical converter levels. This establishes a
calibration starting point; it does not demonstrate the original's SNR, THD,
maximum output swing or frequency response. Change SW33 in manual dry bypass,
because its input/output poles are not guaranteed to change at the same instant.

## Power and analog health

This prototype uses an external regulated 12 V, current-limited 2 A DC source.
There is no mains circuit in the enclosure. F1, SW34 and D3 provide a draft fused,
switched reverse-polarity path. Surge protection/fuse coordination and the exact
DC jack/adapter are still to be finalized. The old 5 V rear-panel supply placeholder
must not be used as the finished power specification.

PS1 is TSR 2-2450. PS2/PS3 are **single-output** isolated TMR 6-1215 modules.
PS2's negative output and PS3's positive output bond to GND, making raw ±24 V.
U29 LT3012 and U30 LT3015 set approximately +19.964 V and -20.008 V before bias,
reference, resistor and load errors. Effective output capacitance and ESR must
meet each regulator's stability requirements. The LT3015 tab is at its negative
raw input; do not bolt it directly to a grounded chassis.

Seed pin 38 supplies the common 3.3 V control rail. This keeps ADC reference and
control levels related and avoids paralleling regulators into the module's
3.3 V output. Its available current with SD, all lights, touch and the processor
has **not been established**. Measure this before populating the full LED load;
an external LED rail with proper interface/power-sequence design may be required.

U31 compares the positive-rail divider and translated negative rail with an
approximately 0.409 V threshold. Their ideal trip points are near ±19 V; actual
bounds must include comparator offset, bias current, reference drift and resistor
limits. U36 monitors the 2.5 V reference itself; otherwise a failed reference can
make a comparator result invalid. U32 delays EXT_RAILS_OK by nominal 300 ms after
the wired health signal recovers. This is undervoltage/settling supervision,
not an analog-rail overvoltage protection circuit.

## Reproduction and release work

```sh
python3 tools/generate_bypass.py --check
python3 tools/generate_carrier.py --check
python3 tests/bypass_tests.py
python3 tests/carrier_tests.py
python3 tools/check_carrier.py --cli /path/to/kicad-cli --footprints /path/to/KiCad/footprints
python3 tools/check_carrier.py --check
```

The carrier suite reads actual generated schematic pins/wires/labels. It checks
all button and LED scan positions, mux inputs, NC/NO paths, driver polarity,
separate clamp/delay wiring, module physical pads, SD reservations, harness order,
power polarity and ideal gain/rail calculations. Its fault mutations detect
incorrect dry wiring; none of these tests constitute native KiCad ERC or a
transient/analog simulation.

Native checks use the integrated project, its generated RMX symbol library and
project library tables. The standalone bypass sheet's external 3.3 V/GND power
flags are omitted from that project: the Seed is the real 3.3 V source, and PS1
supplies 5 V. Only the external protected DC input and its return have source
declarations. PS2/PS3 output returns and U29's second internally parallel output
pad are modeled as passive contacts, with one ERC source per generated rail.
This avoids representing one regulator as competing power supplies. Fuse,
switch and diode continuity is separately checked in the host circuit suite;
an ERC power declaration does not prove their ratings or fault behavior.

Native reports/netlist/SVG exports are written to `build/hardware/native`.
`native-check.json` stores their hashes and the exact checked source hashes;
it does not turn missing footprints, default ignored ERC rules or unmeasured
electrical behavior into a passing fabrication gate. KiCad's default ignored
rules are listed in the record. No custom error suppression was added.

Remaining work before fabrication is substantive: select the remaining physical
parts and footprints; add overload/ESD protection and mono detection; reconcile
all rear-panel openings with the selected RCA/TS/USB/SD/power/mode parts; verify
3.3 V current; complete manufacturer-symbol/footprint and circuit review; place and
route the PCB with controlled return paths; run DRC; render/check the enclosure
and component interference; then assemble and run [commissioning](commissioning.md).
USB MIDI, calibration persistence and the full reference DSP behavior also remain
separate firmware requirements in the main clone roadmap.
