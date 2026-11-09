# Analog-control native candidate 01 — rejected

Native checks report 2,212 opens, two redundant same-face U13 vias, and one
dangling enable track. The old R100 branch shared a via and trunk with the U31
output; removing that backbone disconnected the remaining control group.
Candidate 02 restores the three original shared objects and omits the two
unneeded vias. No rules were disabled. This candidate is not selected.
