# AC01 shared audio core integration

This editable KiCad project combines the selected 94-part E12-R2 ADC driver,
60-part E09 codec circuit and 60-part E08 receiver into **one 210-part circuit**.
It removes four prototype raw-analog headers. Its three sheets are circuit
sections of a proposed shared PCB, not three PCBs or an approved analog harness.

Open [the KiCad project](audio_core.kicad_pro),
[the top sheet](audio_core.kicad_sch), [ADC sheet](adc.kicad_sch),
[codec sheet](codec.kicad_sch), [receiver sheet](dac.kicad_sch),
[native export](netlist.xml), [ERC report](erc.json), or
[independent integration handoff](integration-handoff.json).

## What changed and what was checked

The four removed headers are E12-R2 J2, E09 J1/J2 and E08 J1. All other
component values, assigned footprints, symbol graphics and electrical pin
types are preserved. References are offset into 100/200/300 ranges for
ADC/codec/receiver, with an explicit original-reference map in the handoff.
The 210 components expose 613 numbered physical terminals in the native export.

Fifteen explicitly named nets connect sheets. Other nets retain their sheet
scope; similar local names cannot silently join. Each ADC force/sense circuit
joins the correct codec polarity, both reference dividers connect to their
respective codec reference outputs, and all four raw DAC pins reach the
correct I/V inputs. The independent checker validates those physical pin
identities in addition to the complete generated pin/value/footprint manifest.

Pinned offline Linux KiCad 10.0.7 reports **zero ERC findings on all four pages**,
with every ERC category enabled. The used external footprints are captured
with source hashes and checked for conflicting same-name library definitions.
Seven portable tests replay the evidence and reject six intentionally broken
ADC, DAC, reference and driver-request connections.

The hierarchy/global-label construction follows
[KiCad's schematic format](https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/).
Original circuit projects remain unchanged.

## Physical routing requirements

There is **no PCB layout for AC01 yet**. U201 (ES9292QPRO) is the only part
without an assigned land pattern; its revisioned manufacturer drawing is still
required. No generic QFN land has been substituted.

The four ADC force and sense nodes share schematic nets, but that alone does
not establish a Kelvin connection. The actual codec input land must be the
first common copper between the force/filter branch and the independent FDA
and common-mode feedback branches. Removing that land from the actual copper
connectivity must disconnect the branches. The handoff lists every endpoint
for that later geometric check. The old E12 header stars do not satisfy it.

Keep codec/I/V connections local and reconsider their placement using the
actual package. The routed E08 region and E12-R2 board remain development
references; their outlines, mounting holes, copper, layer counts and local
clearance exceptions have not been transplanted or approved as an integrated
audio layout. Select the shared stack, outline and enclosure receiving before
releasing copper. Eight retained external/service headers also require final
power-entry, mating, pin-order and harness consolidation/review.

## Remaining electrical requirements

The original CHIP_EN → DRV_ENABLE interface is retained through E12-R2's
10 kΩ request resistor and its independent bias/V5 supervisor. This retains
the existing system interface; it does **not** qualify loaded gate levels,
codec-reference startup timing, shutdown transients or partial-power injection.
The original reference-health requirement must still be met before enabling
the driver. Supply qualification and clock/ramp flags are not a substitute
for missing ESS analog limits.

Actual ESS ADC loading, reference drive capability and partial-power limits,
raw DAC current/DC/impedance conventions and final analog gain remain open.
Preserving existing values does not resolve these questions. The effective
capacitance, leakage and settling requirements of the source circuits remain
in force, as do first-article inspection and isolated bring-up requirements.

No physical fit, extracted parasitics, stable coupled loops, audio performance,
thermal result or manufacturing-process acceptance is claimed. AC01 is an
integration source for the complete standalone design, not a fabrication release.

## Reproduction

Construction and the Linux-only native review are in
[`audio_core_integration.py`](../../audio_core_integration.py); the independent
audit is in [`audit_audio_core.py`](../../audit_audio_core.py).
The applied construction recipe is preserved in `source-recipes/`.

```sh
.venv/bin/python -m hardware.fabrication.audit_audio_core --check
.venv/bin/python -m unittest discover -s tests/tooling -p test_audio_core_integration.py -v
```

Build creates a fresh candidate directory and refuses to replace this one.
Native checks use the guarded offline Linux container. No Mac CAD application
was opened, no codec footprint was invented, and no order or supplier message
was sent.
