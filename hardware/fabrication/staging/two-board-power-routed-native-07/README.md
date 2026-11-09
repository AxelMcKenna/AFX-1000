# Power board — two-via control detours

This intermediate checkpoint closes **18 control connections on 14 nets**, using
85 tracks and 36 conventional 0.60/0.30 mm through vias. Native opens fall from
2,572 to **2,554**. The new tracks total 307.510 mm; the longest route is 26.441 mm.
No component placement, schematic partition or previous copper geometry changes.

The [native review](review.json) reports zero geometry/parity/ERC errors and the
two retained isolated-reference warnings. The [independent audit](additive-audit.json)
preserves all 1,105 footprints and 3,308 earlier native connection groups, checks
all 18 physical endpoint joins and measures the new copper against 15 provisional
mount reserves. The [successor receiving check](retained-via-clearance.json)
rechecks both generations of new control vias, 56 total, against every layer,
SMD land and drill. Nine bounded local group-pair attempts remain deferred.

A wider screen then found ten inherited source vias with drill holes touching
SMD lands. They were already present before this detour pass. Same-net electrical
DRC does not reject that assembly arrangement. The [next checkpoint](../two-board-power-routed-native-08/README.md)
moves those ten vias locally, reconnects their old contacts and measures all
124 vias. Use that successor for the current development layout.

The [rejected-source reconciliation](rejected-source-net-status.json) also finds
that eight of the 52 originally rejected source nets are now fully connected;
44 still have gaps, totaling 82 opens. This records current connectivity, not
restoration of the rejected original copper or electrical qualification.

The board remains unreleased. Loaded timing/noise, returns, critical placement,
module protection/startup, remaining routing, ESS inputs, manufacturing stack,
exact BOM/assembly process and installed housing fit remain unfinished.
