# Control pull-down checkpoint — 45 opens

R1003, R2002 and R2003 now connect to MCU_PERMIT, ANALOG_OK and INPUT_READY.
Native Linux KiCad 10.0.7 reports **45 opens across 44 nets**, down from 48,
with zero geometry, schematic-parity and ERC findings and all categories enabled.
The board has 2,623 tracks and 472 vias. Selected DC04/AP04 remain unchanged;
this is a development comparison, and the complete unit is not fabrication-ready.

| Pull-down | Back-side move, mm | Added signal copper | Added ground copper | New vias |
| --- | --- | --- | --- | --- |
| R1003 / MCU_PERMIT | (43,16) → (41.5,16) | 3.378 mm | 6.913 mm | 1 signal |
| R2002 / ANALOG_OK | (68,25) → (101.5,41.5) | 12.480 mm | 2.629 mm | 1 signal |
| R2003 / INPUT_READY | (77,27) → (101.5,34.5) | 5.112 mm | 1.756 mm | 0 |

Each footprint translates with its orientation, value and pin assignments exact.
Six explicitly identified old ground-spur segments are retired. Thirteen new
0.20 mm segments and two conventional 0.60/0.30 mm vias reconnect the resistors;
all other existing copper, all other component poses, mounts, outline and authored
zones remain exact. The retained old ground vias still connect the ground planes.
No native rule was relaxed. The 30 mm added-route search target is an optimization
limit, not an electrical acceptance criterion.

Independent native witnesses preserve every previous pad-group connection. All
201 power/ground pads, 39 local connections and 33 thermal branches remain intact.
Each of the four planes retains a single physical copper union. Minimum
non-exempt drill-edge-to-SMD gap is 0.154984 mm; the 21 heat-spreader vias retain
their mask/tenting/process hold. SD spread is 5.999 mm with one via per signal,
and LED_SCK remains 46.620 mm/two vias. ARMED and both data-series nets remain exact.
The earlier R3015 tradeoff—16.753 mm before and 103.539 mm after the resistor—
still requires electrical review, together with long I2C copper and installed loads.

Conditional AP04 context/floor receiving passes for 138 parts and five mounts.
All eight copper plots and two 1200 dpi placement details were visually inspected.
All 38 focused tests pass, including rejection of an unapproved ground-junction
removal, changed resistor nets, moved unrelated components and false connections
across disconnected surface regions. The complete independent audit replays the
parent checkpoint, exact native additions, actual copper/via clearance and all
preserved pad groups.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact relocation and connectivity audit](pulldowns-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
[construction recipe](../digital-control-pulldowns-repack-05/construction.json),
and [bounded search outcomes](routing-search-review.json).

Thirty-five LED output nets remain open. The other nine open nets are CONTROL_26,
LATCH_5V, LATCH_5V_SRC, SERIAL_0, SERIAL_1, POT_ADC_09, BYPASS_SENSE, LED_BLANK
(three groups), and LED_XLAT. The next work is their blocked escapes and local
placement/copper access. The selected audio checkpoint remains at 219 opens with
the ESS land missing; negative protection has 138 opens and two explicit
isolated-domain ground warnings. Accepted stack/process, actual assembly receiving,
full electrical/thermal/fault qualification, inspected manufacturing outputs and
a current first-article package remain incomplete. See the [unit inventory](../../README.md).
