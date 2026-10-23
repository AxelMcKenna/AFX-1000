# E17 rail disconnects and independent OV interlock

E17 adds a162-component candidate circuit between the E14 rail generators and
the existing audio/control loads. Six pairs of common-source NFETs disconnect
both directions on ±19V, ±12V, analog5V and digital5V. An auxiliary-powered
reference, negative-rail sense amplifier and eight comparators control all six
switches together. No MCU or protected rail is needed to start the interlock.
This is a schematic prototype, not a fabrication or assembly release.

The verifier independently checks every exported component/net/value contract,
critical pin roles, standard MOSFET pad grouping,16,384 allocated rail-threshold
corners,512 powered interlock combinations and768 ideal body-diode direction
cases. Fresh exports check the E14 sources, E16 auxiliary/run interface and
existing protected-load connectors. Conditional voltage-drop and charge screens
are separate from physical fault protection, which remains unverified.

## Connections and startup

| Header | Pins in order | Connection |
| --- | --- | --- |
| J1 | P19_SRC, AGND, N19_SRC, P12_SRC, N12_SRC, V5_REG_SRC | E14 J2 |
| J2 | 5V_DIG_SRC, AGND | E14 J3 |
| J3 | P19, AGND, N19, P12, N12, V5_REG | Protected analog loads / E13 J2 |
| J4 | 5V_DIG, AGND | Protected Seed3/LED/relay domain; historical E11 calls this5V |
| J5 | V2V5_AUX, AGND, POWER_RUN | New E16 J6 |
| J6 | AGND, ALL_RAILS_ALLOW, PROTECT_REF | Engineering test points |

These headers document boundaries. Production current ratings, keying and
wiring remain unselected. In the integrated carrier, the switch-to-generator
power paths must use the copper allocations below; prototype header/contact
resistance is not included in those allocations. Never connect AUX to Seed3's
3.3V output.

```text
E16 independent AUX --> REF35125 / OPA2333 / OV comparators / AND logic / Si8751
E16 POWER_RUN --------> common run input

Unprotected E14 source rails --> OV sensing (remains live after a disconnect)
                         |
                         +--> NFET pair --> protected rail --> existing loads/E13
                                  ^
                           floating Si8751 gate drive

Six OV_OK + two reference-window OK + POWER_RUN --> ALL_RAILS_ALLOW --> all six
```

The interlock checks overvoltage only. Zero source voltage is permitted while
the main converters start, avoiding a dependency on the very rails being
switched. REF_LOW/REF_HIGH provide broad startup/open/short qualification, not a
second precision reference. A10k reference bleeder defeats feedback-resistor
phantom bias after a reference-source open in the settled model.

Any monitored source OV, reference-window fault or run-low opens all channels.
The measurement stays on the source side, so opening the FETs cannot itself
clear a sustained OV. This is a level-controlled interlock; it does not add a
separate fault latch. E13/E11/F03 still qualify processed-audio recovery.
Protected output capacitors can hold voltage after opening; this circuit does
not establish rapid discharge or isolation of all signal-pin backfeed paths.

E14 now has157 components. Appended R51=10ohm raises the digital source nominal
to5.004V with feedback still before the switch. All six source nets now end in
`_SRC`; protected load names remain unchanged. Raw-generator soft start and SET
references use unprotected5V_DIG_SRC, preserving their independent startup path.
E16 now has48 components with J6, a65mA E17 auxiliary allocation, and checks for
the100k receiving run pulldown plus5uA logic-input leakage.

## Switches and packages

Each Si8751 generates floating gate power internally. Its SOURCE pin connects
to the shared FET source node, which can follow either rail polarity. The two
body diodes point from this common node toward opposite drain terminals. The
input and protected output are separate nets; no rail is bypassed by a body diode.

CSD18540Q5B60V FETs serve the four bipolar rails. CSD18510Q5B40V FETs serve5V.
The higher bipolar rating allows for opposite-rail lift during partial power;
actual coupled-rail/signal-pin faults still require validation. The standard
KiCad VSONP footprint groups physical source pins1–3 into logical pad1, gate
pin4 into pad2 and drain pins5–8/exposed drain into pad3. Grouping and pad
positions are checked, but complete manufacturer land-pattern/stencil approval
is unfinished. Do not substitute a conventional G/S/D pin-order symbol.

Each gate has22ohm damping and a20Mohm gate-source bleed. The loaded-drive
screen includes2uA total hot gate leakage and the driver's370kohm maximum
on impedance at nominal10k TT. It leaves more than8V gate drive under those
allocations. The high impedance makes a low-value gate-source resistor unsuitable.
TT10k balances drive and auxiliary current; all six drivers have local bypasses.
Each control input has a10k receiving pulldown. Under a10uA input-leakage
allocation, a missing interlock trace stays below0.101V; that leakage allocation
must be qualified because it is not an explicit Si8751 input-current maximum.

Both drain terminals feed MCAP inputs through10pF/100V capacitors and15k series
resistors. A60V step through the minimum resistor remains below the6mA pin-current
limit. That current screen does not prove clamp sensitivity, negative-pulse
behavior, slew-rate immunity or prevention of false turn-on in the finished PCB.

## Normal voltage and bulk capacitors

Switch-drop calculations preserve the earlier protected-star targets. Hot FET
resistance is allocated6mohm each on bipolar rails and3mohm each on5V. The copper
allocation is1mohm for bipolar paths and0.5mohm for5V, excluding external contacts
and harnesses. These are layout/temperature requirements, not manufacturer hot
RDS guarantees or measured resistances.

The digital protected-star screen, including10mV ripple allowance, is about
4.9013–5.0992V. Analog5V has about4.9772–5.0213V before additional analog ripple
or load steps. Both have little remaining margin. Actual copper, connectors,
consumer voltages, switching noise and transients must be checked. Do not relax
the targets to accommodate an unsuitable board or harness.

| Rail | Selected bulk candidate | Nominal body / pitch |
| --- | --- | --- |
| P19, N19 | EEUFR1V152S,1500uF35V | D16x20mm /7.5mm |
| P12, N12 | EEUFR1V221,220uF35V | D8x11.5mm /3.5mm |
| V5_REG | EEUFR1C152,1500uF16V | D10x20mm /5mm |
| 5V_DIG | EEUFR1C472,4700uF16V | D16x25mm /7.5mm |

Negative-rail electrolytics have their positive lead at AGND. Dimensions are
manufacturer nominal values; sleeve/case tolerance, clearance, leads and full
assembly fit are not verified. The charge screen uses initial−20% capacitance
at the table's20°C condition. Cold capacitance/ESR, endurance loss, ripple current
and regulator stability with these added capacitors remain open.

## Protection timing is still a qualification target

The source trip ranges are approximately:

| Rail | Rising magnitude | Falling magnitude |
| --- | --- | --- |
| P19 |19.369–19.726V |19.351–19.708V |
| N19 |19.353–19.716V |19.335–19.699V |
| P12 |12.504–12.733V |12.493–12.722V |
| N12 |12.390–12.623V |12.378–12.611V |
| Both5V rails |5.1569–5.2481V |5.1523–5.2435V |

These corners include0.3% reference error,0.1% precision-resistor total error,
5mV comparator offset allocation, input-current allocations, hysteresis and
negative-amplifier error. The reference's initial accuracy alone is not the
complete error budget. The comparator bounds at the auxiliary voltage and actual
startup/brownout behavior still require qualification.

**The Si8751's35us maximum turn-off entry is measured with100pF. It does not
bound these MOSFETs.** E17 uses a125us end-to-end interruption *allocation*,
including comparator overdrive, gate discharge, wiring and load-current cessation.
Actual gate charge is much larger than the timing test load. This must be measured
or supported by an applicable manufacturer model; if it fails, change the driver
or add a suitably qualified fast gate-discharge path.

The conditional charge screen allocates1A per analog rail and3A digital,1mV
comparator overdrive and0.1V additional overshoot. It screens5V against5.5V and
the combined19V rails against40V;12V uses a conservative18V magnitude screen.
Longer-delay/higher-current stress cases are retained, including failures.
These currents are not established bounds for a regulator pass failure or raw
capacitor dump. No physical absolute-maximum protection claim follows.

The E17 auxiliary allocation is65mA. Together with E16's conservative overhead,
the regulator screen is about71mA and0.73W at normal maximum input. Six driver
RF loads and their startup steps need real decoupling and thermal design. Normal
load plus the direct-input ramp retains only about68mA to the allocated minimum
eFuse limit. Charging the added rail capacitors uses additional energy; the
reported ideal minimum charging time is not a startup upper bound or proof that
current limiting, fault timers, firmware startup and load steps cooperate.

Full PCB/enclosure placement, semiconductor SOA, real fault currents and timing,
partial power/backfeed, supply stability/noise and physical tests remain open.
The interlock isolates loads while E14 remains powered; unprotected generator
fault dissipation must be tested. Added bulk changes rail collapse order and
relay hold-up, so E11/E13 power-failure bypass behavior must be requalified.
The existing170-reserve enclosure check does not include this stage.

## Regeneration

```sh
python3 -m hardware.electronics.power_supply.generate
python3 -m hardware.electronics.input_protection.generate
python3 -m hardware.electronics.rail_disconnect.generate
python3 -m hardware.electronics.power_supply.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.rail_disconnect.verify --kicad-cli /path/to/kicad-cli
```

See `dependencies.json`, `integration.json`, `switch-map.json` and the generated
reports for sources, boundaries, numeric allocations and unresolved evidence.
