# Startup permission, remaining receiver and pull-up routing

Development candidate from TBP43; not a fabrication release. U42 and C85 move
together to (102, 146.5) and (97.2, 148.6) respectively. U31 and C76 remain in
their existing nearby placements. Values, footprints and schematic nets remain.

25 targeted interconnects include the complete ALL_RAILS_ALLOW net, buffered
AUX-valid fanout, ANA_PG2 and its Schmitt output, analog follower and pulldown
signal end, U31 high-input/bypass/supply, U42 supply, all seven PG pull-up AUX
ends, and both NF AUX-valid/global-master header connections. Four main-ground
joins and the U42/C85 local bypass supply join bring the expected reduction to
30 opens. U31/C76 ground escapes are explicitly checked against existing ground
ownership; analog eFuse pulldown returns are left for their local return design.

A conventional one-transition search could not connect U29.1. The final path
uses bounded multilayer A* with four new transition vias. It includes a local
In4 path, screened against both adjacent layers and protected In3 projections.
Every final path and via is rechecked by the original geometry screen; native
DRC, connectivity partition, references and copper ownership remain required.

Four existing main-ground outlines extend. In5 may overlap its same-owner
inlet field. Quiet fields, distinct same-net return groups, and mounting reserves
are excluded. One unconnected In6 outline fragment is discarded by construction.
plan.json is the construction input; archived searches retain scratch paths.
