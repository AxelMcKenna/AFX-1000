# E21 power-load integration

E21 includes the E20 LED/display driver in the digital power ledger and revises
three candidate schematics. Native ERC and independent exported contracts pass
for all three. The routed E20 board also passes its native checks. These are
design/allocation results; power PCB routing and physical qualification remain open.

| Change | Previous value | E21 |
| --- | --- | --- |
| E14 digital provision | 1.2 A; LED driver logic omitted | 1.8 A against 1.574 A allocated load |
| E14 C17, digital soft start | 33 nF | 1 µF; effective 0.8–1.2 µF allocation |
| E16 R7, input current programming | 6.49 kΩ | 5.62 kΩ; nominal 3.203 A |
| E16 C5, input ramp | 100 nF | 330 nF; effective 264–396 nF allocation |
| E17 digital switch | Q11/Q12 | Q11∥Q13 and Q12∥Q14; opposing common-source banks |

The ledger counts 600 mA for Seed/its 3.3 V domain, 764 mA for E20 and emitters,
120 mA for four coils, and 90 mA for panel/sensor/other reserve. The E20 entry
contains 384 mA sink allocation, 360 mA driver logic and 20 mA miscellaneous.
It is counted once. Actual ICC/sink bounds at the selected 16.5 kΩ IREF, external
3.3 V loads and measured firmware/coil current remain unqualified.

## Conditional screens

The digital soft-start calculation assumes the protected bulk is connected before
the buck ramps and allocates at most 6.5 mF total connected capacitance. The
datasheet charge-current extremes and capacitor allocations give 97–217 ms,
342 mA additional digital charging current and 195 mA referred to the input. The
conditional peak-inductor estimate is 2.58 A against the 4.2 A minimum high-side
limit. The capacitance inventory, late switch closure, large-capacitor loop and
other-rail charging are outside this bound.

The revised input screen combines 2.497 A steady allocation, 81 mA direct-bus
ramp and 195 mA conditional digital charging: 2.773 A against a 2.874 A minimum
current-limit allocation. The resistor/error allocation gives an upper limit of
3.534 A. The 10% programming-error assumption at 5.62 kΩ is not a manufacturer
guarantee. Adapter/fuse coordination, actual fault current, SOA and thermal
behavior still need qualification.

At the 1.801 A protected digital allocation, the two parallel devices per side
give 3.5 mΩ allocated switch-plus-star resistance, including 0.5 mΩ copper.
The resulting 4.9028–5.0992 V range preserves the 4.9–5.1 V target. Its small
2.79 mV/0.82 mV margins exclude production contact/harness drop and rely on the
declared hot-resistance and 10 mV ripple allocations.
The source accuracy allocation requires 0–85°C junction temperature. At the
55°C local-board assumption, the 0.90 W dissipation allocation requires at most
about 33°C/W effective thermal resistance. That thermal target is unqualified.

Four digital FETs double that driver's gate load. The loaded gate screen uses
4 µA total hot leakage and retains 7.38–14.22 V under its Thevenin allocations.
The manufacturer's 100 pF timing conditions do not bound this bank. Sixteen
independent digital gate combinations check body-diode directions; the parallel
parts do not provide redundant single-FET-fault isolation.

## Evidence and open work

- [E14 native record](power_supply/generated/verification.json):157 contracts,
  zero ERC, 1,280 linear/32 buck/128 raw-setpoint corners and the E20 ledger.
- [E16 native record](input_protection/generated/verification.json):48 contracts,
  zero ERC, 80 eFuse/2,048 fast-OV corners and revised conditional input current.
- [E17 native record](rail_disconnect/generated/verification.json):164 contracts,
  zero ERC, 16,384 thresholds, 512 interlock combinations, 768 common-gate diode
  cases and 16 independent digital gate states.
- [Reconciliation](led_driver/generated/power-reconciliation.json):fresh upstream
  source fingerprints and independently recomputed current/drop totals.
- Two regressions reject a miswired parallel leg and the old fast digital
  soft-start value with the protected bulk. The full tooling suite has 21 tests.

All-rail startup/late closure, connected capacitance/ESR, regulator stability,
increased gate charge, physical fault interruption, thermal design and
distribution/contact drops remain open. These power circuits have no routed
PCB or completed housing placement. The E20 PCB's bytes and A06 mechanical
packet are unchanged. No new ARM build, flashing, physical audio or soak claim
is made for this update. The unit is not build-ready.

TI's [TPS62933F datasheet](https://www.ti.com/lit/ds/symlink/tps62933f.pdf) provides
the soft-start and switching limits used here; large output capacitance needs
startup and loop study. A [TPS62913 candidate](https://www.ti.com/lit/ds/symlink/tps62913.pdf)
was rejected because its 200 µF total-capacitance recommendation does not cover
the existing 4,700 µF protected digital bulk. That protection bulk was retained.
Other datasheet references, allocations and unselected parts are recorded in
the three boards' dependency files.
