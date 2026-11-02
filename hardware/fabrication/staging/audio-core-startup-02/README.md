# AC02 buffered startup and ADC-bias qualification

This 216-part successor preserves AC01's 210 parts and analog values while
repairing its startup request/settling interface. It adds three logic ICs and
three local bypass capacitors. It remains an **unrouted integration candidate**.

Open [the KiCad project](audio_core.kicad_pro),
[native ERC](erc.json), [native export](netlist.xml),
[exact circuit and electrical audit](integration-handoff.json), or
[primary-document identities](primary-documents.json).
The preserved [AC01 project](../audio-core-integration-01/README.md) documents
the original three-section circuit and ADC force/sense routing requirements.

## Repairs

The HCS gate's near-rail output specification applies at 20 µA. AC01's 100 kΩ
CHIP_EN pull-down alone needs at least 26.2 µA at the ADC request's former
2.7 V minimum, before other loads. This is a missing guarantee, rather than
evidence the gate cannot drive the circuit.

U210, SN74LVC2G17DCKR, now buffers CHIP_EN and separately drives ADC_DRV_ENABLE
after codec clock/ramp flags qualify. The HCS outputs feed only logic inputs.
U211, SN74LVC1G17DCKR, receives the ADC's 5 V bias-window signal on a 5.5 V
tolerant input. U212, SN74LVC1G08DCKR, combines the translated bias qualification
with the live codec qualifier to control both the settling timer and final
ANALOG_OK gate. A bias fault therefore inhibits processing with TIMER_OK high.
The ADC's own V5/bias supervisor retains its independent PD clamp.

Primary sources:
[HCS08 Rev. D](https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf),
[LVC2G17 Rev. N](https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf),
[LVC1G17 Rev. Y](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf),
[LVC1G08 Rev. AA](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf).
The 100 µA output condition and exact pin assignments were checked against
these documents; captured stock footprints still need package/process review.

## Conditional electrical and timing results

Native Linux KiCad 10.0.7 reports zero ERC findings with every category enabled.
The audit checks all 635 exported terminals, the exact declared changes to
AC01, all four ADC stars and all four DAC polarities. It exercises 128 powered
logic combinations and six faults with the timer held high.

The 4,096-corner powered DC screen uses IO rail bounds 3.04–3.55 V, resistor
allocation ±3%, two independent negative rails, ±100 nA FDA input currents
and ±300 nA supervisor output leakage. It gives:

| Quantity | Conditional bound |
| --- | ---: |
| Normal ADC request current | ≤83.05 µA |
| Enabled FDA PD relative to its negative rail | ≥1.3915 V; required >1.15 V |
| Disabled FDA PD relative to its negative rail | ≤0.4183 V; required <0.55 V |
| Request current upper bound against reset clamp | <0.367 mA; reset low specification uses 1 mA |

The near-rail buffer output condition covers that normal ADC request load.
The remaining codec CHIP_EN input allowance is 62.4 µA after its pull-down and
logic-input budget; confirm actual ESS loading. The timer MR load must fit
its recorded 95 µA output allowance. Schmitt thresholds at the actual IO rails,
edges, reset load and power ramps remain review/measurement conditions.

The ADC supervisor's CT-open release can take 28 ms. The old 1.5 µF minimum
effective timer capacitance leaves only about 1.182 s after that delay, below
the retained 1.2 s ADC settling allocation. **C227 must now retain 1.6–2.8 µF
effective capacitance**, with total CT injection within ±100 nA. Its nominal
2.2 µF value is unchanged. The resulting minimum timer is 1.2910 s; deducting
28 ms and a 1 µs logic allowance leaves 1.2630 s after driver enable.
These calculations use the
[TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf) and
[TPS3890](https://www.ti.com/lit/ds/symlink/tps3890.pdf) bounds and require stable
qualified supplies, bounded reset loading and initially fully discharged CT.
The actual capacitor and rapid fault/rearm discharge behavior are unqualified.

## Interface and release limits

**Do not reuse the old external CHIP_EN → ADC DRV_ENABLE wire.** AC02 J104.2
is the independently driven ADC_DRV_ENABLE observation point; J205.8 is the
buffered codec CHIP_EN point. Joining them defeats sequencing and can connect
two push-pull outputs. The baseline `hardware/wiring/system.py` describes the
older separate-board interface and is not an AC02 harness prescription.
Final power/service connectors and wiring remain to be consolidated.

The ESS package land, ADC loading and partial-power limits, reference-health
timing, DAC scale/gain, physical force/sense stars, integrated routing,
housing/thermal receiving and manufacturing inputs remain open. The new bias
gate and powered DC screen do not establish analog-pin isolation or fault
safety. No PCB DRC, extracted stability or physical performance is claimed.

## Reproduction

The source recipe and native runner are
[`audio_core_startup.py`](../../audio_core_startup.py); the independent audit
is [`audit_audio_startup.py`](../../audit_audio_startup.py). Applied recipe bytes
are retained in `source-recipes/`. Original AC01 and source-board projects
remain unchanged. No Mac CAD application, supplier message or order was used.

```sh
.venv/bin/python -m hardware.fabrication.audit_audio_startup --check
.venv/bin/python -m unittest discover -s tests/tooling -p test_audio_core_startup.py -v
```

This is a development repair for the complete standalone design. Fabrication
release remains false.
