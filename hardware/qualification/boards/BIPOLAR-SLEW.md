# Retained bipolar startup: normal-ramp candidate

This is an **unimplemented circuit study**, not a replacement native board or a startup qualification. Existing E28 Si8751 banks still turn on together without a bounded charging current. The retained protected bulk stays downstream of the switching/protection elements.

`bipolar_slew.py` reads the actual E28 native capacitor values/nets/rail bleed resistors and the matching P03 source-value model. It freezes the inputs in a versioned directory under `hardware/validation/board-qualification/generated/bipolar-slew/`. It does not edit either circuit. The captured source revision is separate from later live routing changes.

## Circuit direction

Keep a supported small shunt for fault protection and control the **normal output-voltage ramp** separately. The earlier 0.28/1.2 Ω LM5067/69 shunt proposal remains rejected. A 91 mΩ nominal comparison with a project ±2% total allocation reaches 92.72 mΩ, below the stated 100 mΩ maximum. Its approximately 14 mV drop at the declared 12 V load is materially smaller than the 0.287 Ω alternative. No exact shunt or all-in tolerance is selected yet.

The [LM5069 Rev G](https://www.ti.com/lit/ds/symlink/lm5069.pdf) front-page circuit provides an explicit transistor/diode/capacitor startup-ramp option. A corresponding negative-rail circuit still needs design and verification using the [LM5067 Rev D](https://www.ti.com/lit/ds/symlink/lm5067.pdf). A slow gate waveform alone does not establish a bounded load-voltage ramp. Gate-current test conditions, external-capacitor effective value, leakage, MOSFET behavior, feedback stability and additional current paths remain unresolved. The source documents' exact hashes and table conditions are recorded with the calculation.

The later [TI TIDA-010070 design guide](https://www.ti.com/lit/ug/tidues3/tidues3.pdf), section 2.4.1.4, uses 40 µA to size the startup capacitor. The component table's 22 µA upper value applies at GATE−OUT=5 V and is not established across the full startup trajectory. The current positive planning envelope therefore uses 40 µA plus the separate unverified 2 µA injection allowance; it does not turn that application example into a component guarantee at 12/19 V. Earlier 24 µA planning outputs remain archived and are superseded for current circuit planning. The larger positive ramp-C scenarios below replace the earlier 2.2/0.33 µF comparisons.

The provisional stage order should put the retained hard-off bank **before** the ramp controller, followed by all protected bulk. An upstream limiter could complete its ramp while a hard-off bank remains open; closing that bank later would bypass the intended soft start. Keeping an upstream limiter instead requires independently proving the bank's ON state before allowing the ramp. Moving the limiter downstream requires explicit charged-load, reverse-current and partial-power analysis, plus isolated negative-domain enable/status interfaces. Neither ordering has been implemented or accepted.

## Conditional planning results

These rows use only native local bulk plus its initial ±20% tolerance, the existing external-load allocations and native ground bleeds. They assume the stated output slew can actually be enforced. Extra downstream capacitance, capacitor temperature/aging, controller supply current, full load behavior and source transients remain open.

| Rail | Effective ramp-C scenario, nominal ±10% | Local bulk plus live-load peak | Provisional phase ceiling | Additional downstream capacitance room |
| --- | ---: | ---: | ---: | ---: |
| +19 V | 4.7 µF | 44.29 mA | 50 mA | 575 µF |
| −19 V | 1.5 µF | 125.09 mA | 150 mA | 455 µF |
| +12 V | 0.68 µF | 169.38 mA | 210 mA | 592 µF |
| −12 V | 1.0 µF | 172.97 mA | 220 mA | 572 µF |

The −19 V ceiling increases the earlier 50 mA scenario. P03's raw negative source, simultaneous positive-source load, transient heat, complete input feed and source-good waveform must be recomputed before adopting it. LT3471's 25°C minimum current limit is not a hot-source guarantee. Fault current can exceed these normal-ramp ceilings; fault-induced shutdown must be safe, rather than assuming precision regulation is maintained during a short.

The constant live load makes pass-device energy significant. For example, the +19 V local capacitor alone accounts for approximately 0.327 J, while its live-load contribution at the slowest ideal ramp adds approximately 3.10 J. The −12 V example is approximately 0.019 J plus 0.404 J. These are ideal-ramp calculations, not MOSFET SOA acceptance. The slowest +19 V output-only scenario is approximately 12.3 seconds; acceptable complete-unit boot behavior is still unspecified. Gate charging before/after the output ramp is excluded; the complete startup-time bound is explicitly null.

The [LTC4218](https://www.analog.com/media/en/technical-documentation/data-sheets/4218fh.pdf) alternative folds back its current threshold with output-derived FB, so a fully active downstream load cannot be omitted from its startup calculation. A different FB arrangement would require an explicit circuit and independent voltage-completion detection. The [LTC4252A](https://www.analog.com/media/en/technical-documentation/data-sheets/425212fe.pdf) timing/acceleration entries reviewed here are typical-only; this study derives no guaranteed fault window or startup delay from them. These observations leave both alternatives unselected.

## Reproduction and next design work

```sh
python -m hardware.qualification.boards.bipolar_slew
python3 -S -m unittest tests.tooling.test_bipolar_slew
```

Generation needs the numerical dependencies of the existing P03 source model. Three portable checks independently cover integrated live-load pass energy, added downstream capacitance exhausting the current margin, and rejection of a shunt whose upper corner exceeds the controller limit.

Next work is a real ramp/feedback schematic with selected pass device, shunt, ramp capacitor, protection and isolation parts; full source/load/capacitance corners; pulse SOA and timeout coordination; sequencing and late-bank closure/reverse/partial-power cases; native fit/routing; then powered measurements. No controller, MOSFET, startup-time, thermal, physical or fabrication gate is passed by this document.
