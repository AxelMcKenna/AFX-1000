# LED_35 with DAC and pot restoration: 33 opens

This eight-layer development comparison closes LED_35 and restores DAC_DATA
and the displaced POT_ADC_05 branch. Native Linux KiCad reports 33 opens and
zero geometry, schematic-parity or ERC findings, with all rule categories
enabled. The selected four-layer DC04 remains unchanged and unreleased.

| Net | Previous total copper / vias | Current total copper / vias |
| --- | ---: | ---: |
| LED_35 | Open, no routed copper | 165.781026 mm / 6 |
| DAC_DATA | 13.961704 mm / 1 | 14.109765 mm / 1 |
| POT_ADC_05 | 60.259712 mm / 3 | 59.958042 mm / 4 |

The repair retires ten tracks and one via: all three DAC_DATA tracks and its
via, plus seven contiguous POT_ADC_05 tracks between retained vias. It adds
71 tracks at 0.20 mm and eight conventional 0.60/0.30 mm vias. The replacement
pot branch is 15.987316 mm. The board now contains 3,117 tracks and 508 vias.
Every component pose, pad assignment, unretired copper object, outline, mount
and authored zone remains exact. R1014 stays at its original position; the
processor supply feed retains its original 1.0 mm width.

The independent checkpoint replay verifies every prior pad group and every
unaffected net record. All 201 power/ground pads, 39 local connections,
33 thermal branches and 32 front switch/selector inputs remain connected.
All four physical plane unions remain connected. SD carrier spread stays
5.999239 mm with one via per signal. Minimum non-exempt drill-to-SMD gap stays
0.154984 mm, and the 21 mask-covered heat-spreader vias retain their process
hold. The minimum screened foreign-net copper gap among the 71 new tracks is
0.210066 mm against the unchanged 0.20 mm rule.

Conditional receiving passes for 138 components and five mounts. All eight
complete copper plots and four 1200 dpi corridor details were inspected.
The focused suite passes 106 tests, including mutations that alter the supply
feed, reassign a pad or new LED track, reduce a via drill or omit pot-repair
evidence.

The long LED route remains unqualified for current/headroom, PWM coupling,
return transitions, harness loading and EMC. DAC timing/source damping and
pot filtering, settling and noise also require electrical review. The route
length bounds are planning limits, not electrical acceptance criteria.

The diagnostic sequence is recorded in the [routing review](routing-search-review.json).
Continuous geometry isolated the conflict to the LED's In3 branch. A proposed
R1014 move was rejected; none of 78 screened positions had output access with
the tested LED route retained. Rebuilding the pot branch instead permits all
three signals to connect without a component move.

A [remaining-LED survey](../digital-open-led-regions-33-01/diagnosis.json)
finds no connected free-space path for any of the remaining 29 LED outputs
under the declared retained-copper planning geometry, including existing
same-net vias. This directs the next work toward coordinated copper/placement
comparisons or separately verified tighter planning margins. It is not proof
of infeasibility at every legal native geometry.

Evidence: [native review](review.json), [connectivity](stage-connectivity-review.json),
[independent replay](led35-dac-pot-review.json), [physical review](corridor-audit.json),
[conditional receiving](conditional-assembly-review.json), [visual review](visual-review.json),
[construction](../digital-led35-dac-pot-repair-01/construction.json),
and [native project](digital_core.kicad_pro).

Remaining digital connections are 29 LED output nets plus LED_BLANK,
BYPASS_SENSE, SERIAL_0 and SERIAL_1. Audio and negative-protection routing,
approved ESS package/interface data, actual stack/process, installed assembly,
electrical/thermal/fault qualification and the current first-article package
remain unfinished. No physical measurement, supplier message, order, commit
or fabrication release is claimed.
