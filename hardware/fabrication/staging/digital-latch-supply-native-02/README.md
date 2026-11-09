# Latch source and pull-up supply checkpoint — 42 opens

The latch buffer now connects to its series resistor through **4.785 mm and one
via**. R3017 moves from B(75,23) to B(68,25) mm, preserving its value, footprint,
pins and orientation. Its output is reconnected through 13.896 mm of B.Cu.
The two LED_BLANK pull-ups retain their supply through a replacement 7.931 mm,
0.30 mm-wide route and one new via. Native Linux KiCad 10.0.7 reports **42 opens
across 42 nets**, zero geometry/parity/ERC findings and all categories enabled.

The board has 2,735 tracks and 475 vias. This remains an unselected eight-layer
development comparison; selected DC04/AP04 remain unchanged. The complete unit
is not ready for fabrication.

The old pull-up supply branch blocked R3017's output escape. Rebuilding that
branch frees a surface route around the retained nearby components. Native
connectivity confirms every V3V3_IO pad, including R1002 and R3010, remains joined
to the processor's source. The 0.30 mm supply width is retained. Clock and blank
buffer escape copper remains unchanged; trial removal of those paths was not
adopted.

The source escape uses a common physical via location reachable from both faces.
The earlier independent-escape search missed this small region, and an extra
0.005 mm search erosion discarded it. The accepted search uses the exact region
with the existing copper, drill and SMD spacing margins intact. Native DRC and an
independent actual-copper check validate the resulting via and tracks. This is
not acceptance of a fabrication process or its registration tolerances.

The first native trial had three dangling-track warnings. Cleanup removes six
obsolete tracks and one unused latch via; the clean review has no geometry
findings. Overall, 105 new segments/two vias replace fifteen old segments/one via.
The exact-delta audit reproduces the cleanup, checks the sole footprint move,
every new segment/via and all parent pad groups, and replays the full earlier
evidence chain. All unretired copper and other component poses remain exact.

Post-series latch copper changes from 197.637 mm/thirteen vias to **199.915 mm/
twelve vias**. Its source branch adds 4.785 mm/one via. V3V3_IO changes from
275.448 mm/two vias to 272.413 mm/three vias. These are branched copper totals,
not measured delay or impedance. Source damping, timing, reference transitions,
loading, supply/noise and installed behaviour remain unqualified.

All 201 power/ground pads, 39 local connections, 33 thermal branches and four
physical plane unions are preserved. SD spread remains 5.999 mm with one via per
signal. Minimum non-exempt drill-edge-to-SMD gap remains 0.154984 mm; 21
heat-spreader vias retain their process hold. Every other net record is exact.
Conditional AP04 receiving passes for 138 parts/five mounts. All eight copper
plots and three 1200 dpi details were inspected. All 56 focused tests pass.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact latch/supply audit](latch-supply-review.json), [visual review](visual-review.json),
[conditional receiving](conditional-assembly-review.json),
[construction](../digital-latch-supply-repack-01/construction.json),
[obsolete-tail cleanup](../digital-latch-supply-clean-01/construction.json), and
[search evidence](routing-search-review.json).

Thirty-five LED output nets and seven other nets remain open: CONTROL_26,
SERIAL_0, SERIAL_1, POT_ADC_09, BYPASS_SENSE, LED_BLANK and LED_XLAT. Next work is
coordinated local escape repair and routing, using actual common via regions
where useful. The long LED_BLANK detours remain unadopted. Audio remains at the
validated 216-open watchdog checkpoint with the approved ESS land missing; negative
protection has 138 opens and two explicit isolated-domain ground warnings.
Accepted stack/process, actual assembly receiving, full electrical/thermal/fault
qualification, inspected manufacturing outputs and a current first-article
package remain unfinished. See the [unit inventory](../../README.md).
