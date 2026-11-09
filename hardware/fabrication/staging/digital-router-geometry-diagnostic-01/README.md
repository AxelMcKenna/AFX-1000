# Native/router geometry comparison

The pinned Freerouting image loads the native-clean 75-open comparison board
with 463 findings. A read-only Java diagnostic captures every distinct
item-pair/layer finding and its participant coordinates. It is compiled against
the exact image JAR; the [comparison record](comparison.json) binds the source,
compiled diagnostic, input files and outputs by hash.

| Interchange representation | Same-net findings | Cross-net findings |
| --- | ---: | ---: |
| Original DSN, 250 µm hole override | 190 | 273 |
| Original DSN, zero hole override | 190 | 273 |
| Circumscribed 64-sided circles, default 45° mode | 230 | 288 |
| Circumscribed 64-sided circles, arbitrary-angle mode | 224 | 3 |

Changing the hole override produces exactly the same findings. The major
cross-net discrepancy comes from the default angle mode:
[ShapeSearchTree](https://github.com/freerouting/freerouting/blob/b647a2f824cfbc54bc4dcaee71b03b7cd945eb76/src/main/java/app/freerouting/board/searchtree/ShapeSearchTree.java)
uses bounding octagons for drilled-item shapes in 45° mode. Finer polygon
definitions alone still receive that octagonal bound. Arbitrary-angle mode
uses their polygon shapes. The remaining largest cross-net shortfall falls
from 0.112100 mm to 0.002243 mm. These are router-model reports, not new native
PCB violations. Same-net via/pin and via/via modelling differences remain visible.

The v3 exchange applies this representation to a separate copy of the 71-open
board. Every edge of all 24 converted round padstack shapes is independently
verified outside the original circle. No native copper, minimum width,
clearance, drill or inspection rule is weakened. Power, local, matched SD and
the short buffer clock-source copper remain explicitly protected.

KiCad does not import the polygon via padstacks written in the resulting SES:
the first raw import reports 440 skipped items and is not used. A separate
normalizer restores only those session library definitions to their original
0.60/0.30 and 0.65/0.30 mm native circular vias. Wire and via positions remain
exact; native import then accounts for all 440/441 session vias in the two runs.

Both bounded routing results are rejected:

- [Fanout trial](../digital-selective-six-native-03/rejection.json): 74 opens,
  one dangling-track and one dangling-via warning; zero parity/ERC findings.
- [Direct-routing trial](../digital-selective-six-native-04/rejection.json):
  72 opens and one native finding; zero parity/ERC findings. The first routing
  pass consumes the bounded job time without reducing its unrouted count.

The [71-open six-layer candidate](../digital-native-spacing-native-01/README.md)
remains retained. The corrected exchange is useful evidence, but these trials
do not establish a better routed PCB. An eight-layer comparison adds a dedicated
signal layer between ground planes instead of cutting existing power/ground
planes for routing. That comparison requires its own native and physical checks.
