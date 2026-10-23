# E16 fast input overvoltage shutdown (E15 input stage)

The current 48-component input schematic extends E15 with a separate fast
overvoltage comparator, shutdown transistor and auxiliary startup qualification. It
uses an external 12 V, 3 A adapter, a center-positive PJ-102AH inlet, a backup
fuse/TVS, external reverse-blocking MOSFET and TPS26630 eFuse. An independent
auxiliary supply powers the rear shutdown switch and converter-enable pull-up.
This is a design prototype, not a fabrication or assembly release.

The native schematic passes all-severity ERC, independent exported pin/value
and critical footprint contracts, 80 eFuse and2,048 fast-OV threshold corners,
11 conditional settled states and a fresh E14 supply interface check.
Calculations include engineering allocations; they are not
semiconductor transient simulation or physical protection evidence.

## Power path and wiring

```text
12V inlet -> 4A backup fuse -> VIN_SYS -> reverse-blocking Q1 -> VIN_IC
                                                                |
                                      +-------------------------+
                                      |                         |
                                  TPS7A1601                 TPS26630
                                  ~2.5V AUX                 internal pass FET
                                      |                         |
                          power switch / PG pull-up        VIN_PROTECTED -> E14 J1
                                      |                         |
                                   SHDN                PGOOD / POWER_READY -> E14 J5
                                                                |
                                                    guarded digital/PRE buck enables

VIN_IC -> TLV7011 sense/hysteresis -> Q3 -> SHDN forced low on fast OV
AUX regulator PG + delay capacitor ------> SHDN held low during aux startup
```

| Interface | Pins in order | Connection |
| --- | --- | --- |
| J1 | center+, sleeve, unused switched sleeve | External adapter; center positive |
| J2 | VIN_PROTECTED, AGND | E14 J1, full input current |
| J3 | AGND, POWER_READY | E14 J5, required startup guard |
| J4 | SWITCH_SUPPLY, POWER_RUN, AGND | Panel switch: ON1, common2, OFF3 |
| J5 | V2V5_AUX, AGND | Auxiliary test/future protection boundary |
| J6 | V2V5_AUX, AGND, POWER_RUN | E17 J5 auxiliary/run interface |

The exact adapter remains unselected. Its required delivered voltage at the
inlet is 11.4–12.6 V, including cable drop. Engineering headers do not establish
production connector current ratings or keying. AUX must never be tied to the
Seed3 3.3 V output. S1 is the panel switch component; J4 describes its harness
boundary, not a second switch.

Q1 source pins1–3 face VIN_SYS; its drain pad5 faces VIN_IC. Its body diode
allows cold positive startup. The eFuse's internal body diode points from OUT
back to IN, opposing Q1 for reverse blocking. Q2 source also follows VIN_SYS;
connecting it to ground would defeat the manufacturer's reverse-input topology.
The auxiliary LDO starts through Q1's body diode before the internal pass FET
turns on, avoiding a startup dependency on the main digital supply.

PGOOD requires both the PGTH threshold and the internal pass FET to be enhanced.
E14 now has 157 components, including J5 and the E17 digital-source trim. Its two bucks share SUPPLY_ENABLE,
fed through parallel 10k top/22k bottom receiving dividers. A missing J3/J5
cable holds them below disable threshold under the stated EN-current allocation.
The converters' internal EN currents have typical-only datasheet entries; the
screen allocates 10uA per pin and requires measurement over temperature.

The switch carries shutdown current. Its receiving47k pulldown makes a missing
switch read OFF under the controller's10uA source-current bound plus1uA auxiliary
PG leakage. The3.3k feed
limits the auxiliary regulator's PG sink current below1mA, where its low level
is specified below the shutdown threshold. Cycling SHDN clears latched
overcurrent/thermal faults. MODE is open for latch-off while SHDN stays high;
the switch, fast-OV guard or loss of auxiliary PG can reset it. UV/OV faults
have their own hysteretic recovery. The selected
TPS26630 lacks the optional2x overload-pulse feature. Switch contact reliability,
actuator orientation, panel fit and mechanical startup behavior remain open.

## Conditional electrical results

| Quantity | Calculated range / allocation |
| --- | --- |
| UVLO rising | 10.115–10.736 V at VIN_SYS |
| OV rising | 14.005–14.885 V at VIN_SYS |
| OV falling | 12.976–13.989 V |
| PGTH rising | 9.722–10.249 V at VIN_PROTECTED |
| AUX | Allocated 2.4–2.6 V, including reference/ratio/bias bounds |
| Main buck EN high / low | 1.464–1.772 V / at most0.277 V |
| Main buck EN, guard cable absent | At most0.223 V under current allocation |
| Switch ON with E17 / missing switch | At least2.123 V / at most0.523 V |
| Current limit | Nominal2.773 A; allocated2.489–3.061 A |
| Steady input plus direct-bus ramp current | About2.421 A, including10mA input-stage overhead and65mA E17 allowance |
| Minimum protected input at steady load | About11.027 V under resistance allocations |

The current-limit error allocation is10%, not a manufacturer guarantee at the
unlisted6.49k setting. The input path uses the eFuse's53mOhm full-temperature
maximum, jack30mOhm maximum, and hot blocking-FET40mOhm/fuse30mOhm/wiring20mOhm
allocations. Q1's datasheet resistance conditions use10V gate drive; the eFuse
driver can supply only8.3V at its minimum. Qualify the hot40mOhm allocation.
Q2 gate discharge at the minimum3V drive also needs qualification.

The220uF bulk capacitor is EEUFR1V221: body8x11.5mm, pitch3.5mm. Its950mArms
and56mOhm impedance specifications are at100kHz; actual switching waveform,
temperature, lifetime and PCB fit remain unchecked. The direct E14 capacitors
have a35uF minimum effective allocation. Including bulk tolerance and E15 C4
gives211.1uF minimum bus capacitance. The nominal-tolerance maximum is392.88uF;
the startup calculation allocates400uF and uses the nominal ramp-gain equation
with dVdT-current extremes and80–120nF timing capacitance. It does not prove
load-step response, full-temperature ramp timing or MOSFET safe operating area.

## Separate fast overvoltage path

U3 TLV7011 is powered from the independent auxiliary rail. R15/R16 sense VIN_IC,
after the reverse-blocking FET. R18/R19 derive a half-auxiliary reference, and
R17 adds positive feedback. U3 high turns Q3 on and pulls POWER_RUN/SHDN low;
S1's series resistor limits the current even with the switch held ON. This path
needs no firmware, digital5V or main converter output. Its output can only pull
shutdown low; it cannot override the eFuse's own UV/OV/current/thermal protection.

The new threshold corners include auxiliary2.4–2.6V,0.3% total resistor error,
22mV comparator offset/hysteresis allowance and10nA input-current allocations.
Rising trip is12.942–14.799V at VIN_IC; falling recovery is12.724–14.569V.
The entire declared normal adapter range remains below even the minimum
falling threshold. These are allocation bounds, not measured thresholds.

At24V misplug the maximum calculated sense input is2.198V, inside the common-mode
range at minimum auxiliary voltage. At60V it is5.459V, below the comparator's
5.5V fail-safe input tolerance independently of its supply. **Fail-safe tolerance
does not establish the same timing or functional performance outside the normal
common-mode range.** Fast functional qualification is targeted at24V; higher
surges still require validation of both protection paths. Sensing before the
reverse blocker would introduce a separate negative-input/clamp problem.

Q3 DMN2056U is characterized at low gate voltage. The screen allocates250mOhm
hot resistance,10uA off-state drain leakage and comparator high output at least
AUX minus0.3V. The resulting gate high exceeds2.09V; shutdown is pulled far below
0.8V while sinking at most0.812mA, including E17 logic-input leakage. Comparator output specifications use a5V
test supply, so its drive at2.4–2.6V and Q3's hot leakage remain qualification
requirements. Gate damping and Q3 must be local to SHDN.

U2 PG now also holds SHDN low until auxiliary startup qualification completes.
C10=10nF sets its delay; C9=1nF filters only the reference. Using a1V minimum
delay-threshold allocation and the regulator's2uA maximum delay current gives
4.75ms minimum, compared with126.4us allocated comparator/reference readiness.
The delay threshold is described approximately by the manufacturer; the1V bound
and100us comparator startup maximum are engineering allocations requiring
measurement. PG function is guaranteed only when VIN_IC is at least3V; the
declared normal input range exceeds this. No timing claim is made for arbitrary
partial-power/replug waveforms.

The conditional fault budget is3us:1us comparison at10mV overdrive,0.1us sensing
RC,0.4us gate drive and1.5us eFuse shutdown. The first three are allocations;
the comparator's310ns typical entry uses5V and100mV overdrive. The report includes
the extra input voltage needed to develop10mV sense overdrive and a0.1V reserve.
With211.1uF effective bus capacitance, hypothetical currents up to45A within
that3us budget give at most15.651V. Longer-delay stress cases still fail. Neither
45A nor3us is an established system bound; this reduces the modeled risk without
claiming physical transient protection has been proved.

Eleven settled cases solve the exported resistor feedback nodes and check aux
off/ramping/delay, normal enable, sustained24V fault, recovery to12.6V, manual
OFF, missing switch and auxiliary PG fault. They use declared comparator/sink
limits and exclude propagation, startup waveforms and semiconductor parasitics.

## Fault limits still requiring resolution

The bidirectional33V TVS avoids continuous avalanche on a24V adapter misplug.
Its rated-pulse clamp is53.3V; actual wiring overshoot, pulse energy and surge
class are unverified. The4A0451004.MRL is backup protection. Its nominal cold
resistance and melting I2t do not prove clearing with a current-limited adapter.
Fuse/adapter/TVS coordination and temperature derating remain open.

A BAS116 clamp and auxiliary bleeder bound positive OVP-pin voltage under a
1.3V forward-drop allocation. The bleeder exceeds calculated injection through
309k at60V. Negative/reverse-input and partial-power pin behavior, clamp
temperature limits and output undershoot still require bench validation.

**The static OV trip and the conditional fast path do not prove that E14 stays
below its16V input limit during a fast fault.** The report retains the original
internal-OV-only screen and includes hypothetical current/delay cases that exceed
the available charge budget. A3A adapter rating
cannot be treated as an instantaneous current bound. The datasheet's8.5–14us
OVP-to-FLT timing applies to the internal path after20mV comparator overdrive;
it does not bound all wiring, gate and load-current interruption behavior. Measure transferred
charge and revise capacitance, thresholds or protection architecture if needed.

[E17](../rail_disconnect/README.md) now draws the analog/digital rail
disconnects. Its added gate-driver/sense load is allocated65mA on AUX; normal
auxiliary current/dissipation screen is about71mA/0.73W. The input current screen
retains about68mA to the allocated minimum eFuse limit after normal load and the
direct-input ramp. Added downstream rail-capacitor charging is separate; startup
current, fault timers, regulation and thermal behavior still need qualification.
E17's100k run receiver and5uA logic leakage are included in the connected switch
high/low checks. A missing run harness reads at most0.505V in that receiving model.
Complete PCB layout, enclosure placement, real protection timing/current,
startup/shutdown and reverse/charged-output tests remain unfinished.

## Regeneration

```sh
python3 -m hardware.electronics.input_protection.generate
python3 -m hardware.electronics.power_supply.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.verify --kicad-cli /path/to/kicad-cli
```

The E14 verifier must run first. The input verifier checks its captured source hashes and freshly
exports the current supply schematic. See `dependencies.json`, `integration.json`
and `generated/verification.json` for sources, boundaries and evidence.

The E15 and E16 review ZIPs remain immutable earlier snapshots. E17 retains the same
project filenames and symbol-library IDs for the input stage, adds J6, and checks
the downstream load/receiver. No full PCB or enclosure-fit claim follows.
