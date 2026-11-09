# Complete front-control routing comparison — 38 opens

All 32 front button/selector input nets now connect their headers to the
expanders. CONTROL_26 is newly connected after jointly reserving three local
escapes and rebuilding CONTROL_22, CONTROL_25 and CONTROL_26. Every component
pose and all unrelated copper remain exact.

Native Linux KiCad reports **38 opens across 38 nets**, zero geometry,
schematic-parity or ERC findings, with every checking category enabled.
The change replaces 39 tracks and eight vias with 98 tracks and ten vias;
new tracks are 0.20 mm wide and new vias are 0.60/0.30 mm. Final totals are
2,832 tracks and 479 vias.

| Input | Previous copper | Current copper |
| --- | --- | --- |
| CONTROL_22 | 50.937 mm, three vias | 47.163 mm, three vias |
| CONTROL_25 | 39.008 mm, five vias | 37.415 mm, three vias |
| CONTROL_26 | Open; 0.038 mm stub | 113.644 mm, four vias; connected |

The long CONTROL_26 route is an explicit development tradeoff. These are slow
digital switch/selector inputs, as defined by the
[E18 input-hub contract](../../../electronics/control_inputs/README.md).
The earlier 75 mm global-route search target was a planning preference, not an
electrical acceptance limit. A separate comparison retains the complete longer
route without relaxing any native copper, drill, clearance or circuit rule.
Its input settling, noise immunity, harness loading, scan behaviour, EMC/ESD and
reference transitions remain unqualified. Connectivity does not establish that
this is the best physical implementation, and further shortening is desirable.

All 201 power/ground pads, 39 local connections, 33 thermal branches and four
physical plane unions survive. SD spread remains 5.999 mm with one via per
signal. Minimum non-exempt drill-edge-to-SMD gap remains 0.154984 mm; the
21 heat-spreader vias retain their process hold. Conditional AP04 receiving
passes for 138 parts/five mounts. All eight copper plots and two 1200 dpi
details were inspected. All 70 focused tests pass, including rejection of
hidden input pin-net changes, unrelated copper changes and altered via drills.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact delta and full parent replay](control26-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
[construction](../digital-control26-complete-comparison-01/construction.json),
[search record](routing-search-review.json), and
[parent checkpoint](../digital-led-control-native-01/README.md).

This remains an unselected eight-layer comparison. Selected DC04 and AP04
remain unchanged. Thirty-three LED outputs and five interface nets remain open:
SERIAL_0, SERIAL_1, BYPASS_SENSE, LED_BLANK and LED_XLAT. Full routing, approved
ESS land/interface data, accepted physical stack/process, installed assembly
receiving, electrical/thermal/fault qualification, inspected manufacturing
outputs and a current first-article plan remain unfinished. See the
[whole-unit inventory](../../README.md). No fabrication release or order is
authorized by this comparison.
