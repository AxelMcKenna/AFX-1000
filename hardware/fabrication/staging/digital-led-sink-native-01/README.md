# Three additive LED closures: 34 opens

This eight-layer development comparison completes LED_49, LED_39 and LED_33,
reducing the preceding 37-open checkpoint to 34 opens. Selected four-layer DC04
is unchanged. The unit is not ready for fabrication.

| Completed net | New copper | Conventional vias |
| --- | ---: | ---: |
| LED_49 | 80.052736 mm | 5 |
| LED_39 | 133.676339 mm | 5 |
| LED_33 | 150.675614 mm | 4 |

The additions are 170 tracks at 0.20 mm and fourteen 0.60/0.30 mm vias. The board
now contains 3,056 tracks and 501 vias. Every parent copper object, component
pose, pad/net assignment, outline, mount and authored zone remains exact. The
processor 5 V feed retains its original 1.0 mm width and 1.2 mm branch.

The first 33-net sweep completed LED_49 and rejected ten other legal routes at
its 100 mm planning target. A separate LED-only comparison used a 180 mm bound
and completed LED_39 and LED_33. These targets are search guards, not verified
electrical limits. The latter two paths have long board-edge detours. Output
current/headroom, PWM coupling, ringing, harness effects and EMC remain
unqualified. Shorter coordinated routing remains desirable, particularly where
these additions constrain adjacent open nets.

The LED_49 intermediate has native zero geometry/parity/ERC findings and 36
opens. Its captured native copper feeds the second search. The combined
construction independently verifies exact intermediate geometry and both
additive deltas. The final native review has 34 opens with zero geometry,
schematic-parity and ERC findings, with every native rule category enabled.

All 201 power/ground pads, 39 local connections, 33 thermal branches and all
32 front switch/selector inputs remain connected. Independent checks preserve
every parent pad group and every unaffected net record. All four physical plane
unions remain connected. SD carrier spread stays 5.999239 mm with one via per
signal. The minimum non-exempt drill-to-SMD gap is 0.154984 mm; 21 mask-covered
heat-spreader vias retain their process hold. Conditional receiving passes for
138 components and five mounts. Actual installed fit and electrical/thermal
performance remain unqualified.

All eight copper plots and three 1200 dpi details were inspected. The focused
suite passes 81 tests, including rejection of hidden power-feed narrowing,
new LED copper reassignment and reduced via drills.

Evidence: [native review](review.json), [connectivity](stage-connectivity-review.json),
[additive delta](additive-route-review.json), [physical review](corridor-audit.json),
[complete checkpoint replay](led-sinks-review.json), [visual review](visual-review.json),
[combined construction](../digital-led-sink-checkpoint-01/construction.json),
[search outcomes](routing-search-review.json), and [native project](digital_core.kicad_pro).

The [follow-up routing review](routing-search-followup-review.json) retains this
34-open board. Polygon-region checks find no LED_35 connection through the
retained copper under either declared planning margin. This is a result for
the planning geometry, not a proof that every native-minimum layout is
impossible. A read-only rework survey finds potential access when any one of
six nearby signal routes is omitted; every omitted connection would need
restoration before adoption.

The smallest surveyed route is DAC_DATA: three tracks and one via. A new
triangulated-polygon path finder resolves a corridor missed by the raster
search. With DAC_DATA removed, it finds a 248.934 mm LED_35 path, rejected at
the 180 mm search bound. Combining that continuous escape with multilayer
routing reduces the trial to 165.781 mm, but the subsequent DAC_DATA restoration
fails. Reversing the order restores DAC_DATA but blocks the tested LED escape.
Neither trial emits a board. Joint reservation of the two routes or coordinated
local placement changes remain necessary next comparisons; sequential routing
has not established a complete repair.

The follow-up checks pass 96 focused tests across two recorded test batches.
An independent [actual-copper clearance check](copper-clearance-review.json)
finds a minimum 0.210039 mm foreign-net gap among the 170 tracks added at this
checkpoint, above the unchanged 0.20 mm rule. No PCB geometry or native rule
changed in this follow-up, and no additional native qualification is claimed.

Remaining digital connections are 30 LED output nets plus LED_BLANK,
BYPASS_SENSE, SERIAL_0 and SERIAL_1. Audio and negative-protection routing,
approved ESS package/interface data, actual stack/process, installed assembly,
electrical/thermal/fault qualification and the current first-article package
remain unfinished. No physical measurement, supplier message, order, commit or
fabrication release is claimed.
