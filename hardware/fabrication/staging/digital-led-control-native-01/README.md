# LED/control routing checkpoint — 39 opens

LED_22 now connects U3001.27 to J3002.2 through 53.882 mm of copper and one
conventional via. Rebuilding CONTROL_02 and CONTROL_12 frees the escape while
preserving both control connections. Every component pose and all unrelated
copper remain exact.

Native Linux KiCad reports **39 opens across 39 nets**, zero geometry,
schematic-parity or ERC findings, with every checking category enabled.
The change replaces 19 tracks and six vias with 24 tracks and three vias;
all new tracks are 0.20 mm wide and all new vias are 0.60/0.30 mm. Final totals
are 2,773 tracks and 477 vias. CONTROL_02 changes from 17.692 mm/two vias to
17.621 mm/one via; CONTROL_12 changes from 29.912 mm/four vias to
24.616 mm/one via. These are routing improvements; electrical performance
under installed loading remains unqualified.

All 201 power/ground pads, 39 local connections, 33 thermal branches and four
physical plane unions survive. SD spread remains 5.999 mm with one via per
signal. Minimum non-exempt drill-edge-to-SMD gap remains 0.154984 mm; the
21 heat-spreader vias retain their process hold. Conditional AP04 receiving
passes for 138 parts/five mounts. All eight copper plots and two 1200 dpi
details were inspected. All 66 focused tests pass, including rejection of
unrelated copper changes, hidden pin-net changes and altered new-via drills.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact delta and full parent replay](led-control-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
[construction](../digital-led-control-escape-repair-01/construction.json),
and [parent checkpoint](../digital-pot-filter-native-01/README.md).

The [search record](routing-search-review.json) retains the obstruction
diagnoses, two unsuccessful paired-LED trials, the successful control repair
and a neighbouring-LED follow-up with zero joins. A separate bounded router
trial reached its internal time limit after one pass and wrote a session, but
its own exchange-model incomplete count remained 58. It was not imported or
adopted. Its 252 pre-existing exchange-model clearance findings are not native
KiCad findings. These bounded searches do not prove that other routes are
impossible.

This remains an unselected eight-layer development comparison. Selected DC04
and AP04 remain unchanged. Thirty-three LED output nets and six other nets
remain open: CONTROL_26, SERIAL_0, SERIAL_1, BYPASS_SENSE, LED_BLANK and LED_XLAT.
Full routing, approved ESS land/interface data, accepted physical stack/process,
installed assembly receiving, electrical/thermal/fault qualification, inspected
manufacturing outputs and a current first-article plan remain unfinished.
See the [whole-unit inventory](../../README.md). No fabrication release or order
is authorized by this checkpoint.
