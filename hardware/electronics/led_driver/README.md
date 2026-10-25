# E20 LED and BPM driver

E20 implements the 96-output feedback interface used by the standalone firmware:
four TLC5947DAPR constant-current drivers, a 3.3-to-5 V translator, and independent
3.3 V/5 V supervisors. It covers the driver core. The front-panel emitter boards,
display wiring, ring optics and production harnesses are unfinished.

The independent [verification record](generated/verification.json), when present,
states whether the native PCB is placed or routed. An explicitly requested
`--placed-only` result permits open connections and is not a routing approval.
The normal verifier requires zero native ERC, DRC, schematic-parity and open
connections, and a saved ground-plane fill. No physical qualification is claimed.

## Power and startup

The four TLC5947s use `5V_DIG`. Their 16.5 kΩ IREF resistors set approximately
2.98 mA per output by TI's nominal formula. The drivers' guaranteed accuracy and
ICC test conditions are at other reference currents; 2.98 mA is not an established
maximum. The provisional engineering allocation is 4 mA per sink, 90 mA ICC per
driver and 20 mA miscellaneous load: **764 mA total**, including the emitters.
That allocation requires physical verification at the selected IREF value.

U5 is an SN74LVC8T245PWR. VCCA and its input controls use `V3V3_IO` from the
processor; VCCB uses `5V_DIG`. DIR is held high. Four channels translate the
firmware's MOSI, clock, latch and BLANK signals. Four unused A inputs are grounded,
with the corresponding B outputs unconnected. Each active output has a 33 Ω
series resistor. Receiving BLANK is pulled high to keep the drivers off while
the translator is disabled; the other three receiving signals have pulldowns.

TPS3808G33/G50 supervisors monitor both domains. Their settled PG outputs drive
two series NMOS switches: both must be high to pull translator `/OE` low. Missing
or unsettled power leaves `/OE` pulled high. The independent checker follows the
actual MOSFET body-diode directions in eight ideal PG/BLANK combinations. This
does not establish real brownout, back-power or restore-frame behavior.

Firmware holds BLANK high at startup and on SPI failure, shifts each new frame
into the separate shift registers, and explicitly provides 1 µs guards
before/after the latch pulse and before clearing BLANK. Host wire tests model
four cascaded 288-bit shift registers and walk all 1,152 PWM bits. Physical SPI
edge timing, cable integrity and recovery still need measurement.

## Connections

| Connector | Assignment |
| --- | --- |
| J1, 2×4, 1.27 mm | 1 AGND; 2 5V_DIG; 3 V3V3_IO; 4 LED_MOSI; 5 LED_SCK; 6 LED_XLAT; 7 LED_BLANK; 8 AGND |
| J2, 2×13, 2.54 mm | Pins 1–12: LED_23…12; 13–24: LED_47…36; 25/26: common anode 5V_DIG |
| J3, 2×13, 2.54 mm | Pins 1–12: LED_00…11; 13–24: LED_24…35; 25/26: common anode 5V_DIG |
| J4, 2×13, 2.54 mm | Pins 1–12: LED_71…60; 13–24: LED_95…84; 25/26: common anode 5V_DIG |
| J5, 2×13, 2.54 mm | Pins 1–12: LED_48…59; 13–24: LED_72…83; 25/26: common anode 5V_DIG |

J1 matches E19 J11 by pin number. The two connectors have different pitches and
require a correctly mapped adapter harness. The [channel map](generated/channel-map.csv)
lists every logical lamp, meter, display segment and RGB output by IC and pin.
Output order follows each driver's physical banks; it does not change firmware
channel order. Emitter cathodes connect to driver outputs, with common anodes at
5 V. Exact emitters, brightness, colour balance and forward-voltage headroom are
unqualified.

## PCB and mechanical proposal

The six-layer board is 91×27×1.6 mm, proposed at housing coordinates
(197,77,6.5). Its M2 clearance holes are (3,7), (87,7), (3,22), (87,22), relative
to the PCB corner. Routing uses 0.15 mm minimum traces/clearance, 0.6/0.3 mm
through vias, In1/In4 ground planes and four mounting copper keepouts across all
six layers. The extra signal layer retains routing space in this small footprint
at increased board cost. The input,
bulk capacitor and common-anode headers have 0.8 mm power routes; IC supply
branches use 0.25 mm. Copper thickness, voltage drop, current rise and thermal
behavior require a final stackup and qualification.

The local TLC5947 footprint follows TI's DAP0032C drawing: 32 signal lands,
grounded EP33 and four paste windows. Thermal vias sit outside the paste/mask
opening. A local footprint audit checks those dimensions; stencil fabrication,
package variant, soldering and actual thermal resistance remain unqualified.
The placement packet reserves top connector/harness height of at most 11 mm,
bottom bulk-capacitor height of at most 3 mm, and trimmed/soldered header tails
of at most 3 mm. These are assembly limits, not selected production parts.

## Integration limits

The [power reconciliation](generated/power-reconciliation.json) refreshes and
fingerprints the E21 adaptations of E14/E16/E17. The 764 mA LED allocation is
counted once in the 1.574 A system ledger, against 1.8 A provision. E16's slower
input ramp and higher current setting retain about 101 mA under a conditional
2.773 A combined steady/input/digital-capacitor ramp. E17's two parallel devices
on each digital leg retain a 4.9028–5.0992 V protected-star range under the
declared hot-resistance and ripple allocations.

These passing screens assume the protected digital bulk is connected before
the source ramps. Other rails' charging, late switch closure, actual 6.5 mF
capacitance bound, large-capacitor loop stability, increased gate charge, thermal
limits, LED ICC at 16.5 kΩ IREF and distribution/contact drops remain unqualified.
The very small 5 V margins require measurement. Full-unit power closure and
assembly release remain open. The immutable A06/E20 review ZIP retains the
earlier failed 1.2 A, 2.693 A startup and 4.8982 V screens as historical evidence.

## Reproduce

From the repository root, with Python, NumPy and native KiCad 10:

```sh
python3 -m hardware.electronics.led_driver.generate
python3 -m hardware.electronics.led_driver.place --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.led_driver.route
python3 -m hardware.electronics.led_driver.cleanup --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.led_driver.verify --kicad-cli /path/to/kicad-cli
```

Refresh upstream verifiers in order `power_supply`, `input_protection`,
`rail_disconnect` before E20 verification if their source fingerprints differ.
`route --fanout-only` and failed-routing intermediates go to the ignored
`build/artifacts/research/e20-routing/` directory. Routing and cleanup are
generation aids; independent native verification is
required. Manufacturer links and downloaded-source hashes are in
[dependencies.json](dependencies.json).
