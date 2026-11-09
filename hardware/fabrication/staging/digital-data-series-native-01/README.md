# Data-series placement comparison — 49 opens

R3015 moves from front (31, 11) mm to back (75, 21) mm. The trace from the
buffer to this 33 Ω resistor is shorter, but the complete data route is longer.
This is a development comparison, not an electrically accepted improvement.
Selected DC04/AP04 remain unchanged; the board and unit are not fabrication-ready.

| Planar copper | Previous 49-open checkpoint | This comparison |
| --- | --- | --- |
| Before R3015, DATA_5V_SRC | 52.091 mm / 2 vias | 16.753 mm / 2 vias |
| After R3015, DATA_5V | 36.749 mm / 0 vias | 103.539 mm / 2 vias |
| Combined | 88.840 mm / 2 vias | 120.292 mm / 4 vias |

The pre-series reduction is 35.338 mm; total copper increases by 31.452 mm.
Source damping, timing, reference transitions, actual stack and installed loads
remain unqualified. The 18 mm source-length search limit is an optimization
target, not an electrical acceptance criterion. A coordinated placement and
route revision may still be needed to shorten the complete path.

Native Linux KiCad 10.0.7 reports **49 opens across 48 nets**, zero geometry,
schematic-parity and ERC findings, with all categories enabled. There are
2,613 tracks and 468 vias; 35 LED output nets remain open. No rule was relaxed.
The candidate adds 23 segments and two conventional 0.60/0.30 mm vias, removes
one old source segment, and reassigns seventeen segments/one via from pre-series
to post-series. The reused copper geometry is exact. A front bridge connects
across the old resistor location. The original driver escape remains exact.

Independent checks preserve every previous connected pad group, all other
component poses and copper, outline, mounts and authored zones. All 201
power/ground pads, 39 local connections and 33 thermal branches remain connected.
LED_SCK remains 46.620 mm/two vias; SD carrier spread remains 5.999 mm with one
via per signal. Each of the four filled planes remains a single physical union.
The minimum non-exempt drill-edge-to-SMD-copper gap is 0.154984 mm; the 21 original
heat-spreader vias retain their mask/tenting/process hold. C3010's local bypass
placement and copper are unchanged.

Conditional AP04 context/floor receiving passes for 138 parts and five mounts;
purchased parts, supports, mates and harnesses remain unverified. All eight
copper plots and 1200 dpi front/back details were inspected. All 28 focused
tests pass, including rejection of changed transferred copper, unrelated copper
and swapped resistor nets. The independent audit replays the parent checkpoint
and checks the exact relocation/net transfer against native output.

Evidence: [native findings](review.json), [all-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[exact relocation and route tradeoff](data-series-review.json),
[visual review](visual-review.json), [conditional receiving](conditional-assembly-review.json),
and [construction recipe](../digital-data-series-repack-01/construction.json).

Next work is coordinated escape/placement review for the remaining LED/control
routes, the longer post-series data route, and long I2C paths. SCL still totals
202.814 mm of branched copper/five vias; SDA is 164.559 mm/fourteen vias. These
totals do not establish delay or bus performance.

For the unit, the current audio checkpoint has 219 opens and the missing ESS
land; negative protection has 138 opens and two explicit isolated-domain ground
warnings. Remaining routing, approved ESS land/interface data, accepted stack
and process, actual assembly receiving, electrical/thermal/fault qualification,
inspected manufacturing outputs and a current first-article package remain
open. See the [current unit inventory](../../README.md).
