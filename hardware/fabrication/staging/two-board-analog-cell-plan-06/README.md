# Analog reference correction candidate

Plan 06 repositions R100 at (51.75, 114.5) mm with its enable pad below
the retained PG0/AUX crossings. Its 2.200 mm enable connection replaces the
previous crossing path. The local ground escape is 3.097 mm; other local
passive return escapes retain their plan-05 positions.

The PG0 reconstruction retires two additional old In6 segments and uses
two reference-aware branches to retain the old pull-up via and monitor
backbone. The router protects the retained B.Cu reference projections and
new back-layer signal projections. The other shared enable backbone is retained.

Eight owned ground regions cover the three analog cells. The U13 In6
reference area for R96 joins through the existing R97 quiet via and U13
In1 field. Only each controller pin-8 star is allowed to contact main ground.
All new surface control routes and the retained U32 enable escape participate
in required plane coverage. Unanchored new outline fragments with no required
area are omitted; native fill and independent coverage still determine acceptance.

The native footprint fixture and independent geometry screen pass. Native fill
produced 47 total zones and preserved 31 existing zone fills exactly.
Native candidate 03 passes geometry/parity/ERC-error checks, all 26 declared
joins, all other connection groups, 1,567 retained references and all 26 new
non-ground paths. It is selected as TBP45 in status 45. This remains a partially
routed development checkpoint, not fabrication approval.
