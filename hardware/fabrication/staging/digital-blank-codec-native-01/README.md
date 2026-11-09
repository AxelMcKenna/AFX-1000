# LED_BLANK with CODEC_RUN restoration: 32 opens

This eight-layer development comparison connects LED_BLANK and restores the
displaced CODEC_RUN section. Native Linux KiCad reports 32 opens and zero
geometry, schematic-parity or ERC findings, with all categories enabled.
The selected four-layer DC04 remains unchanged and unreleased.

| Net | Previous total copper / vias | Current total copper / vias |
| --- | ---: | ---: |
| LED_BLANK | 11.230293 mm / 1, open | 106.202922 mm / 5, connected |
| CODEC_RUN | 194.142539 mm / 6 | 227.955205 mm / 12 |

The repair retires one 43.038200 mm back-side CODEC_RUN segment. Its replacement
is 76.850866 mm with six new vias, an increase of 33.812666 mm. LED_BLANK gains
94.972629 mm and four vias. In total, 65 tracks at 0.20 mm and ten conventional
0.60/0.30 mm vias are added. The board contains 3,181 tracks and 518 vias.

Every component pose, pad assignment, unretired copper object, outline, mount
and authored zone remains exact. R1013 stays in place and its processor-side
trace remains 2.587500 mm with no via. The full-width processor supply feed is
unchanged. Independent replay verifies every prior pad group and every
unaffected net record.

All 201 power/ground pads, 39 local connections, 33 thermal branches and
32 front switch/selector inputs remain connected. All four physical plane
unions remain connected. SD carrier spread stays 5.999239 mm with one via per
signal. Minimum non-exempt drill-to-SMD gap remains 0.154984 mm; the 21
mask-covered heat-spreader vias retain their process hold. The minimum measured
foreign-net copper gap among the new tracks is 0.210000 mm against the
unchanged 0.200000 mm rule.

Conditional receiving passes for 138 components and five mounts. All eight
copper-layer plots and three 1200 dpi processor-corridor details were inspected.
The focused suite passes 127 tests, including mutations of the supply feed,
pad assignment, routed copper, via drill and restoration evidence.

The additional CODEC_RUN length and six transitions require timing, loading,
coupling, return-path and EMC qualification. The original 65 mm replacement
search target was expanded to 80 mm to evaluate this complete route pair;
neither value is an electrical acceptance limit. No native design rule changed.
This remains an unselected routing comparison, not evidence of installed
performance or readiness to manufacture.

The [search review](routing-search-review.json) records the rejected R1013
placement and POT_ADC_02 trials. No resistor move or analog-net reconstruction
from those trials is adopted. A fresh [interface survey](../digital-interface-regions-32-01/diagnosis.json)
finds no retained-copper region path for SERIAL_0, SERIAL_1 or BYPASS_SENSE
under either compared planning margin. This is bounded geometric evidence,
not proof that all legal routing arrangements are infeasible.

Evidence: [native review](review.json), [connectivity](stage-connectivity-review.json),
[independent replay](blank-codec-review.json), [physical review](corridor-audit.json),
[conditional receiving](conditional-assembly-review.json), [visual review](visual-review.json),
[construction](../digital-blank-codec-repair-02/construction.json),
and [native project](digital_core.kicad_pro).

Remaining digital connections are 29 LED outputs, SERIAL_0, SERIAL_1 and
BYPASS_SENSE. Audio and negative-protection routing, approved ESS package and
interface data, physical stack/process, installed assembly, electrical/thermal/
fault qualification and the current first-article package remain unfinished.
