# TBP73 short AUX join

Two new 0.3 mm F.Cu segments join N_U35:14 to N_U15:3 over3.38871 mm. Native opens decrease1937→1936. All original objects, footprint poses and47 plane fills remain unchanged; no vias or zone edits are introduced. Exact native group comparison proves only this pair merges.

Geometry and schematic parity have zero findings. ERC retains the same two ground-name warnings. Native copper outside original same-net pads/tracks has zero uncovered area over In1.Cu main ground; direct unbuffered ground-contact evidence independently anchors that reference. Native front/reference details in `plots/` were visually inspected.

This joins two local AUX terminals; it does not connect them to the regulator or qualify decoupling/current behavior. The refreshed survey07 still has72 of81 IC supply pins without source connectivity. The held-rail schematic and additional parts remain separate unplaced candidates.

Planning preserved the strict reference and clearance requirements. A pad-aware check excludes only already-existing same-net copper from the newly-added area; four regression tests reject new escape gaps while allowing an empty added area. The latter fixed an empty-geometry predicate error in the initial grid precheck. A bounded grid search then found this single path. No broad unreferenced escape waiver was used.

The generic capture tool rejected the capped499-record DRC list; its failure log is retained. The correct power capture independently establishes1936 opens from native connectivity and pad-cluster gaps. This is a routing checkpoint, not fabrication release.
