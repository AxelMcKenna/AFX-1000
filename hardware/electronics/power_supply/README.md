# E14 main rail generation

E14 adds a native candidate power schematic for standalone operation. It converts
an external protected 12 V input into regulated ±19 V, ±12 V, analog 5 V and
digital 5 V. With the E17 source trim, 157 physical components pass native ERC and independent exported
pin/value/net checks. This is a schematic prototype with conditional calculations;
it is not a fabrication or assembly release.

Input reverse-polarity/inrush/eFuse protection is now a separate
[E15 candidate schematic](../input_protection/README.md), connected at J1/J5.
Its current E16 adaptation adds separate fast-OV shutdown and auxiliary PG delay
without changing those power/enable interfaces.
Its transient, coordination and physical validation remain open.
[E17](../rail_disconnect/README.md) now adds the separate six-rail disconnect
candidate; its real timing/current, PCB and physical protection proof remain open.
E14 alone provides no input or final-rail protection.
E13 removes processing eligibility on rail
faults; it does not disconnect supply voltage from the ICs.

## Architecture and interfaces

```text
Protected12V ─┬─ TPS62933F FCCM buck ── 5V_DIG ── Seed3 VIN, LEDs and relay coils
              ├─ TPS62933F FCCM buck ── 5.8V pre ── LT3080 ── V5_REG
              ├─ LT3471 boost/Cuk ── +/-22V ── precision SET sources / +/-19V LDOs
              └─ LT3471 boost/Cuk ── +/-17V ── +/-12V LDOs

5V_DIG ── REF5025E ── positive target amplifiers
Raw negative22V ── LT1634A negative shunt ── negative target amplifiers
Final rails ── E13 independent monitors ── E09/E11 qualification and dry bypass
```

The ±12 V stages have their own pre-regulators. Their full-temperature amplifier
quiescent current is already 91 mA per rail, before signal current. Passing that
load through the ±19 V regulators would add unnecessary dissipation and exhaust
the initial current allocation. The lower raw pair is nominal ±17 V so its
positive boost stays above the LT3471's minimum-duty boundary at maximum input.

| Header | Pins in order |
| --- | --- |
| J1 | VIN_PROTECTED, AGND; normal boundary 10.5–13.2 V |
| J2 | P19_SRC, AGND, N19_SRC, P12_SRC, N12_SRC, V5_REG_SRC; goes to E17 J1 |
| J3 | 5V_DIG_SRC, AGND; goes to E17 J2 |
| J4 | RAW_P22, AGND, RAW_N22, RAW_P17, RAW_N17, V5_PRE; engineering test points |
| J5 | AGND, POWER_READY; required from E15 J3 |

Both bucks now share SUPPLY_ENABLE, driven by E15 power-good through parallel
10k/22k receiving dividers. The receiver pulldowns hold the enables low when
the guard cable is absent under E15's EN-current allocation. This changes the
earlier155-component E14 archive, which remains a historical snapshot. E15
records the earlier156-component adaptation. E17 appends R51=10ohm to trim
the digital source to5.004V and renames all six source rails with`_SRC`.
Protected load names remain unchanged. Feedback and raw-generator soft start
remain on the source side; the switch does not enter a regulator feedback loop.

J2 supplies E05/E07, E08, E09, E10 and E12 through E17 and the checked power-header
mapping. The older relay schematics call their coil rail `5V`: wire that net to
`5V_DIG`. Their `3V3` and E09/E13 `V3V3_IO` refer to the Seed3 digital 3.3 V
domain. Seed3's 3.3 V pins are outputs; do not feed an additional regulator into
them. The external 3.3 V load and partial-power interface budget must be checked
before the control/carrier PCB is released. Production connectors/harnesses are
unselected; the pin headers are engineering interfaces.

A 12 V, 3 A external low-voltage adapter is the working supply candidate. The
allocated input-power screen is about 21.83 W, or 2.08 A at the lowest protected
input. It includes conservative conversion/control-current allowances. It is not
a measured consumption figure or approval of an adapter, connector or input fuse.

## Regulation and loading

| Final rail | Normal target | Output current budget including own bleed |
| --- | --- | --- |
| P19, N19 | magnitude 18.81–19.19 V | 25 mA each |
| P12, N12 | magnitude 11.88–12.12 V | 150 mA each |
| V5_REG | 4.975–5.025 V DC | 250 mA |
| 5V_DIG | 4.90–5.10 V | 1.2 A |

The positive regulators are LT3080IMS8E for19V/5V and LT3080IQ in DD-PAK for
the higher-current12V stage; negative regulators are LT3090IDD.
OPA4192/OPA2192 target sources drive their SET pins through 6.8 kΩ resistors.
DC feedback senses after that resistance, avoiding SET-current voltage error.
Local 47 nF feedback bypasses the remote SET pole at high frequencies. Each
output has a minimum-load/discharge resistor. The positive 5 V regulator uses
separate 5.8 V IN and protected12V VCONTROL supplies, preserving both dropout
requirements without drawing its control current from the audio rails.

The positive targets use REF5025E; negative targets use industrial A-grade
LT1634AIS8-2.5 as a negative shunt. These are independent of E13's monitor
reference. Precision ratios specify 0.01%, 5 ppm/°C parts with a total 0.1%
resistor-error allocation. Exact resistor and capacitor MPNs, leakage and
temperature/aging derating remain open.

The allocated DC bounds are approximately +19 V ±70 mV, negative19V magnitude
18.889–19.112 V, +12 V ±50 mV, negative12V magnitude 11.929–12.071 V, and
analog5V 4.979–5.021 V. These are conditional calculations. Analog5V retains
only about 3.8 mV to its tight normal DC envelope; rail ripple and load steps
must be measured and may require more decoupling or regulator refinement.
They must also remain inside E13's trip boundaries during healthy operation.

The ±12 V budget counts the actual five OPA1612 duals, three OPA1656 duals and
one OPA4192 quad. It combines full-temperature IQ maxima, an E08 hypothetical
DAC/receiver DC-plus-AC peak current bound, own bleed and an additional 10 mA
non-E08 signal reserve. The resulting conservative screen is about 132.6 mA
against 150 mA per rail. Actual converter scale, load waveforms, overload and
short-circuit currents remain unverified.

The digital budget allocates 600 mA to the Seed/module domain, 288 mA to 96 LED
sinks at 3 mA, 120 mA to four coils and 90 mA to panel/sensor/other reserve.
Those are design allocations. Actual firmware load, LED current-setting parts,
brightness, external 3.3 V load and coil currents require validation.

## Switching, startup and thermal limits

Each LT3471 provides one boost and one Cuk inverter. The Cuk switch carries the
sum of input/output inductor currents; the screen includes both ripple terms,
minimum effective inductance/frequency and a 75% efficiency allocation. Transfer
capacitors see input plus negative-output magnitude and therefore specify 63 V,
with at least 2.2 µF effective capacitance. Exact shielded inductors must meet
the BOM's saturation, RMS-current and DCR requirements. Their footprints are
candidates, not completed manufacturer land-pattern audits.

Raw envelopes allocate ±4% around 22 V and 17 V. The voltage screen reserves
3 V of switch ringing; real ringing must be measured. The selected 0.9 A switch
limit is a conditional 25°C screen, not a guaranteed full-temperature bound.
Initial 68 pF feedforward compensation is provided, but the actual switcher
loop/inductor/capacitor combination still needs manufacturer-model and bench
load-step/startup validation. The LT3471 E grade also has temperature conditions
described in its datasheet; it is not a blanket industrial qualification.

Both raw generators start from 5V_DIG. Positive reference power comes from
5V_DIG and the negative shunt from its raw rail. Nothing waits for CHIP_EN, so
there is no intentional codec-enable dependency loop. F03's bounded chip-ID
probe handles delayed rail qualification before configuration. Actual timing
must fit the five-second startup deadline; no startup-time guarantee is claimed.

The digital buck's ±1.5% reference screen applies at 0–85°C junction. Outside
that range its wider reference bounds can exceed the stated normal 5 V budget.
The unit ambient target is 0–40°C; local board ambient, copper spreading,
enclosure heating and IC junction temperatures remain unverified. In particular,
55°C local ambient and a 0.65 W buck allocation require at most about 46°C/W
effective thermal resistance to retain that junction limit. The native
schematic does not establish this. The linear thermal screen uses declared
board assumptions; it does not prove that the housing can dissipate all heat.

Important package connections are checked explicitly: LT3080 exposed pad is
OUT; LT3090 exposed pad is negative IN; LT3471 exposed pad is AGND. The negative
LT1634's pin4 is negative2.5V and its cathode/pin6 is AGND. Grounding the wrong
pad would short a rail. SET-current limiting is screened, but complete clamp,
unpowered, reverse-power and output-short behavior remains open.

## Verification

```sh
python3 -m hardware.electronics.power_supply.generate
python3 -m hardware.electronics.power_supply.verify --kicad-cli /path/to/kicad-cli
```

The [native record](generated/verification.json) covers 157 exported component
contracts, zero all-severity ERC, 1,280 allocated linear accuracy corners,
32 buck corners, 128 raw setpoint corners, dropout/current/load screens and
fresh exported power interfaces. The 192 hypothetical SET-source loop cases
have at least about 59° phase margin in the declared two-pole amplifier model.
That model excludes internal LDO/switcher loops and PCB parasitics and does not
establish real stability. [Electrical screens](generated/electrical-screens.json)
retain the allocations, temperature limits and incomplete protection/thermal
flags. Sources and unresolved part selections are in [dependencies.json](dependencies.json).

No E14 PCB, enclosure placement, physical supply/startup/audio evidence or
complete weighted system-noise closure exists yet. The earlier 170-reserve CAD
fit does not include E08–E17. E17's voltage-drop screen applies to the integrated
board star and excludes production contact/harness drop. Digital and analog5V
have tight remaining ripple/voltage margins; actual integration must preserve
their existing targets.
