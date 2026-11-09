# Router/native clearance mismatch

The pinned router's `hole_clearance_um` setting inflates drilled-item obstacles
to enforce hole-to-copper spacing. Its implementation explicitly describes
that calculation in [ShapeSearchTree](https://github.com/freerouting/freerouting/blob/b647a2f824cfbc54bc4dcaee71b03b7cd945eb76/src/main/java/app/freerouting/board/searchtree/ShapeSearchTree.java)
and [ForcedViaInserter](https://github.com/freerouting/freerouting/blob/b647a2f824cfbc54bc4dcaee71b03b7cd945eb76/src/main/java/app/freerouting/board/actions/ForcedViaInserter.java).
The prior 250 µm override must not be described as equivalent to native
drill-to-drill clearance.

There is a separate same-net via mismatch:
[Via.isObstacle](https://github.com/freerouting/freerouting/blob/b647a2f824cfbc54bc4dcaee71b03b7cd945eb76/src/main/java/app/freerouting/board/model/items/Via.java)
treats another same-net via as an obstacle, and
[Item.clearanceViolations](https://github.com/freerouting/freerouting/blob/b647a2f824cfbc54bc4dcaee71b03b7cd945eb76/src/main/java/app/freerouting/board/model/items/Item.java)
applies the copper-clearance matrix to the pair. The earlier native-clean
board produces 463 router findings, including 184 fixed-item findings; the
first five logged fixed pairs are AGND vias. Changing the hole override alone
therefore cannot make the interchange equivalent to native KiCad.

The [source-bound review](review.json) preserves the pinned revision, upstream
source copies and prior log/native evidence. The rejected global trial remains
rejected. No native rule is weakened and no new global-router result is adopted.

A separate [additive routing checkpoint](../digital-native-spacing-native-01/README.md)
uses captured copper sizes, PCB drill sizes and independent native checks.
It reaches 71 opens, while retaining explicit signal-integrity and fabrication
holds. Its corrected v2 screen requires source-bound drill geometry rather
than assuming that the capture includes via drill fields.
