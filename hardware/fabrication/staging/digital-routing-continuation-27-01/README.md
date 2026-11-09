# Routing continuation: no new accepted checkpoint

The [verified LED16 checkpoint](../digital-led16-closed-native-01/README.md)
remains the current eight-layer comparison: **27 opens, zero other native
layout/parity/ERC findings**. No completed route from this continuation was
adopted. The complete unit is not ready for fabrication.

## Results

- Removing the whole LED02 net did not permit joint completion with LED13.
  For LED01/LED02, routing either first blocked the second. A finite 0.05 mm
  local escape search found no compatible pair or three-output packing when
  LED03 was also removed. These results do not prove global infeasibility.
- Removing the complete LATCH and MCU_PERMIT trunks allowed LED30 to route,
  but neither tested restoration order completed every displaced connection.
- The first LED30 path was 244.130 mm after simplification and conflicted
  with fourteen LATCH objects. Its minimal-cut restoration failed.
- Restricting the global LED30 route to In3, In5 and B reduced the combined
  path to 210.681 mm and its conflicts to five LATCH tracks and one via.
  The upper F.Cu boundary could be restored through 6.548 mm. The other
  LATCH boundary could not be restored by the tested searches, including
  one using retained native vias as layer crossings.
- A deliberately provisional [native connectivity trial](../digital-led30-connectivity-probe-native-01/README.md)
  confirmed that LED30 connected but U3002.30 lost its LATCH connection.
  It therefore still has **27 opens and two dangling-track warnings**.
  This trial is rejected; no native category was disabled or waived.
- Native capture identified a five-pad LATCH group and the isolated U3002.30
  group. Further searches first rebuilt that leaf, then retained its original
  vias and searched between both complete native groups. Neither emitted a
  completed candidate. Three native-confirmed loose tracks were trimmed only
  in the latter planning copy; the verified board was not edited.

The [recursive evidence review](review.json) checks the twelve unsuccessful
search records, the rejected native candidate, the unchanged verified board
and all 213 current unit-source bindings. The same two historical NF test-hash
mismatches remain disclosed. The prior eleven focused tests are inherited
from the unchanged board; no new passing-board test result is claimed.

## Remaining work

Continue from the LED16 checkpoint, not from the rejected LED30 trial. A
further LED30 proposal must preserve U3002.30's connection to every other
LATCH pad and pass native dangling-copper checks. The recorded results also
show why a route to old stub endpoints is insufficient as a general repair
strategy: both actual native groups and new-via placement limits matter.

Selected DC04 still has 143 opens; the latest audio partial has 208, and NF
has 138 with its two retained isolated-ground warnings. The ESS package,
land-pattern and stencil inputs remain unavailable after the 2026-11-04
repo/connected-Drive/public-listing check. The official listing still links
[the v0.1 datasheet](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf).
The [manufacturer handoff](../../manufacturer-inputs.md) now cites the verified
27-open digital comparison instead of the stale 31-open comparison.

A complete reviewed design, accepted manufacturing inputs and a defined
first-article inspection/bring-up package are required before prototype
release. Subsequent measured qualification requires built hardware. No
order, release, vendor message, commit or push occurred.
