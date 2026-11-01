# FV01: 5 V fan supply proposal

Two Noctua NF-A4x10 **5V three-pin** fans are a candidate for the existing
digital supply. This does not substitute them into FA01/FI01 or implement a
new circuit, connector, harness or cooling pass.

The current product downloads link the same external CAD ZIP used for the
12 V tray proposal. Fresh downloads are byte-identical. The detailed drawing's
40 ±0.5 mm square, 12 ±0.5 mm padded thickness, Ø4.3 ±0.1 mm holes and
32 ±0.3 mm pitch match the tray's receiving class. The model is for external
mechanical fit; its modified impeller is not an airflow simulation model.
Manufacturer documents remain external; `source.json` records URLs and hashes.

| Fan-motor planning term | Value |
| --- | --- |
| Two rated currents including the PDF's ±10% | 0.110 A |
| Provision including a further 20% | 0.132 A |
| Existing unassigned digital reserve | 0.416 A |
| Reserve after the motor provision | 0.284 A |
| Known input allocations plus motor provision | 2.116 A |
| Motor power provision at nominal 5 V | 0.660 W |

These are catalogue-based steady planning terms, **not startup, stall, short
circuit or hot-life current bounds**. Fan-health logic and tach pull-up currents
are not yet included. The PDF lists 50 mA ±10%; the web page lists 50 mA maximum.
The broader PDF interval is retained. Existing loads and the Seed 1 A provision
are not reduced to make room for fans.

The actual P03 `db83` netlist connects J3.1 to `5V_DIG_SRC` and J3.2 to AGND,
before the E28 disconnect. Captured native pad centres are (216,112) and
(218.54,112) mm, with 1 mm drills. This makes J3 a possible source to assess;
its exact mating/header selection, copper/return capacity and use in a complete
protected branch remain unqualified. No new load was silently connected.

The source-voltage scenario leaves about 170 mV for additional downward drops
before reaching 4.8 V, which is 20% above the fan's 4 V starting figure.
That arithmetic includes the retained dynamic/spread allocations but excludes
unresolved signed ground/contact/network and actual motor transient terms.
`complete_source_to_fan_voltage_interval_v` therefore remains null.

The RPM interface is open collector and supplies two pulses per revolution:
4500 rpm corresponds to 150 Hz. A locked rotor can leave the signal high **or**
low, so a logic level cannot establish that a fan is turning. A 3.3 V/2.2 kΩ
pull-up is an illustrative 1.5 mA interface only; the actual receiver, voltage
levels, partial-power isolation, filtering, ESD and wiring are not selected.
The PDF also contradicts itself about reverse-polarity protection; no indefinite
reverse connection protection is credited.

Next work is a real protected branch, complete harness and tach/thermal
interlock, followed by source-copper/transient and installed cooling checks.
The existing thermal model idealizes heat into base projections and does not
solve internal air or package/PCB heat paths. Underside base airflow alone is
not proof that the Seed and +50 °C potentiometer bodies stay cool. Actual
internal cooling paths and temperature measurements remain required. Allocate
motor/controller heat from any existing thermal reserve before adding it again;
no whole-unit heat number is changed by this proposal.

Recompute the planning evidence with `python3 -S analyze.py` from this directory.
It verifies the external source hashes, native source pin map and unchanged
mechanical receiving dimensions. All electrical, thermal, physical and
fabrication approval flags remain false.
