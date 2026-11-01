# FH02 native fan-health interlock draft

This private 68-part schematic implements the FH01 firmware pin contract, two
remote SEMITEC 203AT-2 sensors, the external 4 MHz crystal, protected tach inputs,
an independent watchdog, a separate hardware fault latch and a normally open
POWER_RUN contact. It is not a routed PCB or physically qualified controller.
The existing firmware, NF03C, FP01 and all earlier hardware seals are unchanged.

`fan_health.kicad_sch` is the native design. `generated/native.json`, the raw ERC
report and exported XML netlist record zero ERC findings and zero pin-map
differences. The tests compare the actual exported MCU pins and part values with
a separate firmware/interface contract. The captured firmware receipt records
12,647 host assertions, 1,760 bytes of code and 90 bytes of static RAM; no target
execution, complete stack or interrupt timing qualification is inherited.

The 3.3 V regulator is TPS7A1633DGNR, with explicit minimum-load bleed and local
input/output/delay capacitors specified for the same PCB face. Each sensor uses
a 20 kΩ pull-up, a 1 kΩ ADC series resistor and a 10 nF filter. The buffers accept
switched 5 V fan tach signals; the fan-side pull-ups remain in FP01. The separate
FP01 FAULT wires are intentionally unused by this firmware.

The ABLS-4.000MHZ-12-D4Y-T crystal uses Abracon's published 5.6 × 2.1 mm lands at
9.5 mm centres. Two 15 pF capacitors require approximately 4.5 pF effective stray
capacitance to obtain its nominal 12 pF load. Actual drive, oscillator startup,
loading, aging and the complete ±0.1% clock error remain receiving tests. The
firmware's ±20 engine-tick period error is also an unverified receiving target.

TPS3431 ENOUT and WDO share WD_OK, together with the regulator's open-drain PG.
A Schmitt buffer conditions that slow node. A dual-supply translator and RAW5
Schmitt inverter turn its falling level into a rising clock for a RAW5-powered
SN74LVC1G74 fault latch. Its D input is HIGH; its clear comes only from a separate
RAW5 supervisor. Once a timeout is captured, watchdog automatic retries cannot
reclose the ideal-state permission path, including with MCU HEALTH stuck HIGH.
Three-volt-only recovery cannot intentionally clear this latch.

The watchdog **does not drive MCU RESET**. Startup-low ENOUT on RESET would set
EXTRF and conflict with the firmware's clean-POR requirement. MCU RESET has its
own pull-up and ISP connection. The MCU's internal watchdog and reset policy
remain independent. The external watchdog has a 2.7 nF C0G timing capacitor:
219.989–311.941 ms under the declared complete ±10% capacitance requirement and
TI's equation/table factors. This exceeds 1.2 × the 160 ms first-heartbeat
receiving target; the target includes supply rise, POR/BOD and crystal startup
from the watchdog's valid-supply boundary. That interval has not been measured.

The latch prevents reclosure **after a captured timeout**. It is not a hardware
RPM qualifier. HEALTH physically stuck HIGH before the first timeout can permit
an initial startup window. Intermediate supply levels, clock/clear sequencing,
false trips, source collapse and arbitrary single faults require characterization;
this draft does not claim coverage of every failure mode.

Two actual LVC AND gates combine MCU HEALTH, conditioned WD_OK and the latched
no-fault state. A 5 V-tolerant Ioff open-drain inverter sinks the TLP175A LED.
Its LED uses a 1 kΩ RAW5 feed and a 10 kΩ bypass directly across the LED. The
permission input has a 10 kΩ default-OFF pull-down. Conditional minimum LED
current is 2.4079 mA, meeting 1.2 × the 2 mA recommended drive, with the stated
RAW5/VF/VOL/resistor requirements. Those hot voltage/current conditions are not
manufacturer guarantees. Toshiba's recommended ambient range ends at 65°C;
its VF, RON, return-current and switching-time rows are specified at 25°C.
The custom 11-4M1S land correctly uses LED pins 1/3 and contact pins 4/6, but is
an unapproved receiving land pattern derived from the package drawing.

The isolated contact connects **only P03 J106.3 to E28 J5.3 POWER_RUN**. It does
not interrupt P03's own RUN branch or raw fan power, and never drives the
internally driven E28_MASTER_ENABLE signal. With a 250 Ω complete-loop receiving
limit, 22 µA receiver/board leakage and the retained R93 envelope, conditional
HIGH is 2.4651 V. With 10 µA contact OFF leakage, conditional LOW is 0.3264 V.
The loaded source, actual wire/joints/contact, ground offsets, discharge and
hot turn-off timing remain unverified. ISP must sense target voltage only;
external programmer power injection is not approved.

The deliberately enclosing current requirement is **16.279144 mA**, or
**19.534973 mA with 20% headroom**. It retains a 3 mA complete MCU receiving
provision and explicitly includes conservative non-rail logic-input current
requirements and mutually exclusive pull-up maxima. The primary MCU 2 mA row
uses a different 3 V external-clock/PRR condition. Neither it nor logic
delta-ICC test points proves the full operating current of this circuit.

This exceeds the old 9.622979 mA health allowance. The new, explicit proposal is
**DIG 2.42 A**: known load/fan/NF/FP partitions plus the guarded FH requirement
total 2.409912 A, leaving 10.088006 mA of that proposal unused. It is not an
adopted source or PDN limit. At planning 5.1 V and retained 85% conversion, the
20 mA capacity increase is 0.120000 W, taking NF03C's provisional whole-inside
capacity screen to **37.405706 W**. The separate 11.4 V/0.36 Ω/90 mA AUX normal
constant-power comparison becomes 2.853273 A at the plug and 10.372822 V at the
board. Its 0.026215 W extra feed loss is not added again to the separate capacity
screen. All voltage, current, guard, connector, return, startup and thermal
acceptance remains false.

`generated/package-review.json` binds actual library bytes and all 68 footprint
pin sets. Their enclosing courtyard areas sum to 1,065.214 mm²; multiplying by
1.2 gives 1,278.257 mm². This is not packing or routing proof for the unallocated
58 × 25 mm proposal. Mated connectors, crystal height, sensor mounting,
mechanics, airflow and a complete physical placement are still required.

Reproduce within this repository:

```sh
PYTHONPATH=. python3 hardware/qualification/boards/fan_health/circuit/design.py
PYTHONPATH=. python3 hardware/qualification/boards/fan_health/circuit/analyze.py
PYTHONPATH=. python3 hardware/qualification/boards/fan_health/circuit/package_review.py
PYTHONPATH=. python3 hardware/qualification/boards/fan_health/circuit/test_circuit.py
```

Native generation requires the captured KiCad 10 environment. Portable tests use
immutable captured parent data, and do not require current parent files to remain
unchanged. The capture is historical provenance, not automatic applicability to a
later board or firmware revision. Primary PDFs, package drawings and exact source
hashes are retained in `sources/` and `handoff.json`.
