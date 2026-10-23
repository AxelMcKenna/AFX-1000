# E02 independent watchdog and relay drivers

E02 turns the earlier watchdog contract into a native, editable KiCad schematic:
33 components, local 3.3 V/5 V supervision, Schmitt-input qualification, an
edge-armed fault latch, two coil drivers and drain clamps. **It is an unrouted
schematic prototype. No circuit has been assembled or bench tested.**

Open [the KiCad project](bypass.kicad_pro), [schematic SVG](generated/bypass.svg),
[BOM](bom.csv) or [pin schedule](components.json). The standard footprint names
are candidates: their pad numbers exist, but manufacturer land-pattern dimensions,
placement, copper and assembled fit are still review gates.

The [native verification record](generated/verification.json) has zero ERC
violations and matches the manufacturer's package-pin contract against the
actual exported netlist. The [25 fault sequences](generated/fault-sequences.json)
exercise that netlist's ideal gate/latch behavior. They do not simulate analog
levels, timer/propagation/recovery delays, unpowered ICs, coils, contacts or audio.

## Current circuit

U1 is TPS3431 with a 150 pF C0G timing capacitor, EN/SET1 permanently high and
heartbeat from the audio callback. U4/U5 are TPS3808G33/G50, powered from 3.3 V
and sensing the 3.3 V/5 V rails. Their nominal thresholds are 3.07/4.65 V; CT is
intentionally open for the nominal 20 ms release delay. Their open-drain outputs
and watchdog WDO/ENOUT share LOCAL_OK, pulled up by 10 kΩ. This satisfies both
devices' recommended pull-up ranges.

U2, SN74HCS08, supplies four Schmitt-input AND functions:

1. LOCAL_OK AND ANALOG_OK → HEALTH_A.
2. HEALTH_A AND PROCESS_OK → CLEAR_N.
3. Latch Q AND PERMIT_CLEAN → COIL_ENABLE.
4. MCU_PERMIT AND MCU_PERMIT → PERMIT_CLEAN, conditioning the latch clock.

U3, SN74LVC1G74DCTR, has D/PRE_N high, CLK at PERMIT_CLEAN and CLR_N at CLEAR_N.
A fault clears Q asynchronously. Watchdog recovery with the MCU permit frozen
high leaves Q low; a fresh permit rising edge is required. Dropping permit
removes coil enable even while Q remains armed. Missing manual-loop or analog-good
wires pull low through 47 kΩ instead of looking like a healthy open-drain output.

Q1/Q2, AO3400A, drive the paired bypass/gain coils separately. Each uses 4.7 kΩ
gate series resistance and a 270 kΩ gate-to-ground resistor. At a 3.0 V logic
supply and a guaranteed 2.9 V static output, the 1% resistor extremes give about
2.85 V at the gate. The static load is below 20 μA, including the specified
MOSFET gate leakage. This is a DC screening calculation; switching and unpowered
gate discharge still need measurement.

D1/D2 are unidirectional SMF9.0A, cathode to drain and anode to ground. They
clamp the drain rather than adding a plain diode across the coil, allowing a
larger reverse coil voltage during release. The manufacturer's 15.4 V maximum
clamp figure is specified at its particular 13 A, 10/1000 μs pulse condition.
It is not a measured clamp voltage for our relays. Coil inductance, pulse energy,
overshoot, repetition and release time remain open bench gates. Keep the clamp
and return loop close to each driver; do not infer the result from the 200 W
headline rating.

C2–C6 are local 100 nF bypasses for U1–U5 respectively. C7 is logic bulk storage;
C8 is 5 V bulk storage. Select the C8 part so effective capacitance remains at
least 10 μF at 5 V, accounting for DC bias. None of these capacitors replaces
regulation, input protection or the final power/ground layout.

## Harness

| Connector | Pins in order |
| --- | --- |
| J1 regulated power | 1:5 V, 2:GND, 3:3.3 V |
| J2 Seed logic | 1:GND, 2:D13 heartbeat, 3:D26 permit, 4:D9 gain request, 5:D28 latch-Q feedback, 6:D0 bypass sense |
| J3 external qualifications | 1:3.3 V, 2:PROCESS_OK, 3:ANALOG_OK, 4:GND, 5:BYPASS_SENSE |
| J4 bypass coils | 1:5 V, 2:switched low side for two parallel bypass relays |
| J5 gain coils | 1:5 V, 2:switched low side for two parallel gain relays |

Seed3 physical pins for these logic signals are D13=14, D26=33, D9=10,
D28=35 and D0=1. Confirm the module orientation against the
[Seed3 manufacturer pin table](https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed3/Daisy_Seed3_datasheet.pdf)
before wiring. Use the digital supply/ground domain for this logic and coil
return circuitry; keep coil currents off the analog return.

All logic is 3.3 V with a common ground. The five headers are prototype
2.54 mm interfaces, not selected production locking connectors.

The DPDT manual switch wiring supersedes the E01 fault-pull-down proposal:

- Pole A common to J3.1; PROCESS contact to J3.2; BYPASS contact unconnected.
  A disconnected process-loop cable therefore inhibits the hardware latch.
- Pole B common to J3.4; BYPASS contact to J3.5; PROCESS contact unconnected.
  J3.5 is pulled up by 10 kΩ and routes to Seed D0 for the existing active-low
  manual-bypass sense.

ANALOG_OK must be driven high only by independent hardware monitoring of **both**
analog rails. Exact analog supervisors/thresholds remain unselected until the
audio topology and supply are settled. Do not use the MCU to manufacture that
power-good signal or treat an omitted monitor as healthy.

The audio carrier still needs the two bypass relays, two gain relays and all
contacts/audio paths. J4 drives input isolation and dry/processed output
selection together. J5 selects the gain-feedback shunts. This sheet does not
contain the audio contacts and does not complete the full bypass/audio schematic.

The two bypass relays' contacts now have their own
[E03 native schematic](../audio_bypass/README.md), with coil polarity and the
J4 harness checked against a fresh export of this E02 sheet. E03 includes dry
output selection and processing-input isolation. The gain relay contacts,
analog stages, power circuits and integrated PCB remain unfinished.

## Firmware and first verification

The current firmware senses ARMED on D28. A new request permits an initial enable
edge and expects latch-Q feedback within 20 ms. Loss of Q removes the request
immediately; a persistent loss becomes a latched fault after 20 ms. That allowance
lets the two manual-switch poles agree without a false fault. Deliberate bypass,
gain changes and calibration reset the monitor. Feedback proves only the latch
state, not coil current or contact position.

Before emitting that first permit edge, all eligibility conditions must remain
valid for 350 ms, including manual bypass being released, calibration being
ready, completed gain settling and more than 128 audio blocks. Any interruption
restarts that interval. This avoids clocking the latch while the manual switch's
PROCESS pole is still changing state. Startup consequently includes both the
audio warm-up and a fresh stability interval.

An absent E02 feedback connection reads low. The firmware consequently stays
bypassed and reports a fault after an unsuccessful arm attempt. The independent
hardware remains responsible for actual coil enable if software stalls.

Before accepting the design:

1. Review all active-device pinouts and candidate land patterns, then place the
   circuit with local decoupling, short clamp loops and suitable coil returns.
2. Complete analog-rail supervision, external connectors, relay contacts and
   the full audio/power schematic. Run native PCB DRC/parity after routing.
3. Bench check 3.3 V/5 V ramp and brownout, rail-monitor faults, cable removal,
   manual switching, MCU halt and loss of audio heartbeat. Scope latch Q, permit,
   coil voltage, drain overshoot and contact timing.
4. Verify watchdog recovery cannot re-energize a frozen-high request and that
   normal manual-switch pole timing fits the 20 ms diagnostic allowance.
5. Check real relay release against the firmware's 20 ms dry wait, gain settling,
   power-loss dry continuity, processing-input isolation, audio transients and
   coil/TVS temperatures. No measured results are claimed yet.

## Regenerate

    python3 -m hardware.electronics.bypass.generate
    python3 -m hardware.electronics.bypass.verify --kicad-cli /path/to/kicad-cli

Those commands start at the repository root. In the standalone review archive,
run generate.py and verify.py directly from the extracted directory. The archive
contains the circuit sources; firmware remains in the repository.

The verifier uses isolated settings and the installed standard KiCad footprint
libraries. Pass its optional --footprint-dir when they are elsewhere. Library
pad numbers are checked without copying third-party footprints into this project.
KiCad 10.0.7 was used; source and library-file hashes are in the record.

The [E05 output stage](../output_stage/README.md) now requires ±19 V and ±12 V.
Its four analog rails must all qualify ANALOG_OK, independently of firmware.
The original references to both audio rails are not sufficient for that domain
split. Their monitors/thresholds and power-down timing remain external and
unselected. E05 connects its output gain relay to J5 and its processed output
to E03; the stereo input-range relay remains unfinished.

## Manufacturer sources

- [TPS3431 pin functions and watchdog timing](https://www.ti.com/lit/ds/symlink/tps3431.pdf)
- [TPS3808 package pins, thresholds and reset delay](https://www.ti.com/lit/ds/symlink/tps3808.pdf)
- [SN74HCS08 Schmitt AND gates and DC limits](https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf)
- [SN74LVC1G74 DCT pinout and asynchronous clear](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf)
- [AO3400A gate drive, leakage and ratings](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf)
- [Littelfuse SMF manufacturer datasheet, distributor mirror](https://www.mouser.com/datasheet/2/240/Littelfuse_TVS_Diode_SMF_Datasheet.pdf-1698977.pdf)
