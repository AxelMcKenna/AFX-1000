# Pot-input filter checkpoint — 40 opens

POT_ADC_09 is now connected. R1040 moves from F(70,30) mm to B(40.5,35.5) mm at
90°, using a native KiCad orientation template with its value, land and pin-net
assignments preserved. The processor, filter capacitor C1020 and pull-down R1050
stay in their earlier positions with their existing connections intact.

Native Linux KiCad reports **40 opens across 40 nets**, zero geometry,
schematic-parity or ERC findings, with all checking categories enabled.
Twenty-five new 0.20 mm segments and four conventional 0.60/0.30 mm vias replace
one 3.480 mm raw-input spur. The board has 2,768 tracks and 480 vias. Every other
component pose and every unretired copper object is exact.

The new ADC branch is 29.221 mm/three vias; the replacement raw-input branch is
40.853 mm/one via. Total branched ADC copper increases from 24.563 mm/one via to
53.784 mm/four vias, now joining all four pads. Raw-input copper increases from
41.863 mm/three vias to 79.236 mm/four vias, preserving both pad connections.
This closes routing but is **not an electrical-performance acceptance**. Pot
settling, coupling/noise, off-board loading, reference transitions and installed
behaviour still require qualification. The 163 mm ADC detours considered near
the original position were not adopted.

All 201 power/ground pads, 39 local connections, 33 thermal branches and four
physical plane unions survive. SD spread remains 5.999 mm with one via per
signal. Minimum non-exempt drill-edge-to-SMD gap remains 0.154984 mm; the 21
heat-spreader vias retain their process hold. Every other net record is exact.
Conditional AP04 receiving passes for 138 parts/five mounts. All eight copper
plots and two 1200 dpi details were inspected. All 62 focused tests pass,
including rejection of hidden pin-net changes, unrelated copper changes and
undeclared removal of the raw-input path.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact relocation and full parent replay](pot-filter-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
[construction](../digital-pot-filter-repack-04/construction.json),
[native orientations](../digital-pot-filter-templates-01/templates.json), and
[parent checkpoint](../digital-exact-regions-native-01/README.md).

The [search record](routing-search-review.json) retains five completed placement
trials. Only trial 04 emitted an adopted candidate. The alternative that replaced
the entire raw-input net did not restore both connections and was not emitted.
A follow-up search on all six remaining control nets found no additional join;
their local escapes still need coordinated rework.

This remains an unselected eight-layer development comparison; selected DC04
and AP04 remain unchanged. Thirty-four LED output nets and six other nets remain
open: CONTROL_26, SERIAL_0, SERIAL_1, BYPASS_SENSE, LED_BLANK and LED_XLAT.
Full routing, the approved ESS land/interface, accepted physical stack/process,
installed assembly receiving, complete electrical/thermal/fault qualification,
inspected manufacturing outputs and a current first-article plan remain open.
See the [whole-unit inventory](../../README.md). No fabrication release or order
is authorized by this checkpoint.
