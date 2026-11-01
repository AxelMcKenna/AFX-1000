# AX03 low-power RUN revision

The preferred E28 software layout now has **zero uncapped opens, zero hard DRC
errors, zero ERC and zero parity findings**, with every native rule category
enabled. Signal-stub cleanup reduces the remaining warnings from 153 to 52;
they remain unresolved and the board is not released for fabrication. Start with
the [closed-layout review](CLOSED_LAYOUT_REVIEW.md), which links the paired
project, actual PCB plot, explicit single-small-via manufacturing profile and
conservative captured-assembly clearance results.

The matching source transmitter is now integrated into a separate **264-part
P03 candidate**, with zero native errors, warnings, opens, ERC and parity
findings. The [P03 integration review](P03_INTEGRATION_REVIEW.md) links its checked
project, PCB plot, exact source conservation, local bypass paths and logical
source-to-receiver pin map. Manufacturing, harness and physical acceptance
remain open for both boards.

This candidate reduces the protection circuit's AUX demand while retaining the
existing 90 mA allocation, 100 mA regulator rating, supply voltage, active-HIGH
RUN interface and original P03 R113/PG loading. It is not released for fabrication.

Eight E28 SN74LVC3G17DCUR packages become pin-compatible SN74AUP3G17DCUR.
A source SN74AUP1G17DCKR drives the external RUN branch through 1 kΩ. The E28
receiver uses another SN74AUP1G17DCKR, a 200 kΩ pulldown and local bypassing.
Its output feeds the original U28 input. Open-wire and ground-short conditions
request OFF. The existing latch and inhibit topology is retained.

The [calculation](generated/analysis.json) puts all five modeled states below
90 mA, including the uncorrelated overlap at 89.357 mA after the joint 1.2 factor.
That narrow remaining allocation depends on **unverified receiving limits**:
100 µA extra current per active input, actual-band Schmitt thresholds, board
leakage, interconnect resistance and ground offsets. Doubling the input allowance
fails the budget; the regression suite preserves this counterexample.

TI's 50 µA ΔICC row is specified at 3.3 V with a particular input condition. It
does not guarantee the proposed allowance throughout the actual 2.52–2.70 V
range. Likewise VT+ ≤ 0.78 VCC and VT− ≥ 0.28 VCC are proposed receiving limits,
not manufacturer guarantees inferred between discrete datasheet rows. Absolute
output-current ratings are not logic-level drive guarantees during a short.

The separate source (10 parts) and receiver (5 parts) have actual Linux KiCad
netlist/value/pin comparisons and zero ERC findings in
[native.json](generated/native.json). Seven regression tests cover the pin map,
interface loading, current counterexample and qualification exclusions.

The full E28 successor lives in
[`low-power-run-work`](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/).
It contains 271 electrical parts and four mechanical footprints. The receiver
insertion changes the declared raw-RUN final branch; subsequent control routing,
the U38/C81 wing placement and signal-stub cleanup are recorded in the
closed-layout review. The source-side P03 change now exists in the separate
checked transmitter candidate linked above. The original P03 connection remains
in preserved parent projects; those parents are not the matching AX03 source.
Neither candidate has been manufactured or measured as a complete system.

The balanced eight-layer construction started at the same XY outline and
1.62 mm nominal CAD thickness as the six-layer parent. The later wing extension
is described below.
The [targeted eight-layer review](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-eight-layer-followup/review.json)
has ten uncapped opens, no hard DRC errors, zero ERC and zero schematic-parity
findings. It retains 147 warnings. The additional P19 link is a connectivity
trial; its 35 µm layer and finite barrel/spreading resistance have not been
qualified for current or fault energy. The new stackup has no accepted supplier
construction, and no older copper or power-integrity qualification is inherited.

The earlier [eight-open control-wing candidate](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/control-wing-return-smoothed/rail_disconnect.kicad_pcb)
adds a 70 × 5.5 mm extension inside the existing housing. PCB depth becomes
60 mm, a 10.1% increase; mounting holes and enclosure dimensions remain exact.
U38 and C81 move into this space. All existing copper and rule areas remain
exact, and the other 273 footprint poses are unchanged. New fanouts give all
eight U38 pins access to through vias under the existing C50 filled/capped
receiving proposal. The reference HIGH and LOW connections now close.

Its [fresh native review](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-control-wing-return/review.json)
reports **eight uncapped opens, no hard DRC errors, zero ERC and zero parity
findings**, with 153 warnings. The new local In4 ground pour has one native
filled polygon covering 423.116 mm²; the U38 ground barrel, C81 ground barrel
and an existing AGND barrel lie in that same filled polygon. This is a
[planar continuity screen](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-control-wing-return/local-return-screen.json),
not impedance, temperature or fault-current acceptance.

The [placement drawing](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/control-wing-placement/control-wing-plan.svg)
and [mechanical screen](../../../electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/control-wing-placement/mechanical-review.json)
show 1.05 mm minimum clearance to the front-connector boxes after their
0.45 mm XY allowance. The whole wing and a 2 mm upper component envelope
clear eleven captured CP01 meshes and the current NF265/FPC91 receiving boxes.
These captured-model screens do not replace full new native assembly,
board-deflection, airflow, harness or physical receiving checks.

That historical candidate's eight open connections were REF_LOW_POSITIVE (two), V5_REG_OV_REF,
ANA_PG1, E28_OUT_READY, REF_LOW_OK_SCHMITT, REF_HIGH_OK_SCHMITT and
DIG_SOURCE_OK_SCHMITT. All now close in the preferred paired project. Additional
access and inner-layer repairs retain the intended ground, AUX and P19 logic
connections after moving the local control traces.
The checked ten-open parent is preserved; the intermediate moved-but-unrouted
floorplan has sixteen opens and is not the preferred candidate.

A separate control-routing restart freezes all 6,764 original power/return
objects and every footprint pose while rebuilding control connections. Its
first three native checks report 164, 130 and 101 opens. It remains an alternate
trial, not a replacement for the closed-layout candidate. Every import checks actual
protected copper geometry; all routing results still require native refill and
full DRC rather than the autorouter's own connectivity score.

The new receiver and bypass also pass a
[captured-mesh placement precheck](generated/mechanical-precheck.json) against
eleven named CP01 meshes, including a deliberate inside-floor control. This
precheck does not replace a new complete assembly receiving run. Mac CAD
applications remain disabled.

Required physical acceptance work:

| Measurement | Required evidence |
| --- | --- |
| Input thresholds and extra supply current | Sweep each active input over the actual supply/temperature envelope; verify the receiving ratios and 100 µA allowance, including simultaneous intermediate inputs |
| Joint source demand | Capture normal, startup, latched fault, line short before settling and uncorrelated overlap; account for instrument uncertainty and the existing 1.2 factor |
| RUN HIGH/LOW | Include actual connector/wire resistance, ±13.4786 mV ground offset, leakage and resistor receiving limits; verify the modeled margins |
| Wire open and ground short | Verify OFF request and measure the complete loaded-system cutoff; the local RC estimate is not the system cutoff |
| Partial power and collapse | Exercise independent source/receiver power order, slow ramps, brownout and recovery; check backfeed and false enable |
| Fault protection and power integrity | Measure fault energy, limiter behavior, device temperatures, rail/ground transients and actual populated-board current paths |

These measurements have not been performed. Fresh filled-copper power/return
extraction, full mechanical receiving checks and prototype qualification remain
separate release gates. Use the pinned isolated Linux CAD runtime; Mac CAD
launches remain disabled by the repository's stop marker.

Primary references: [SN74AUP1G17](https://www.ti.com/lit/ds/symlink/sn74aup1g17.pdf),
[SN74AUP3G17](https://www.ti.com/lit/gpn/sn74aup3g17),
[Panasonic ERA6AEB204V](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA6AEB204V).
The captured component metadata's older Panasonic URL is superseded by this
exact manufacturer model page; sealed parent records are unchanged.
