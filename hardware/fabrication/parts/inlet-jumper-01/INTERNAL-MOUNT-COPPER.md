# Internal inlet-plane clearance at mounting holes

The first inlet corridor applies the provisional surface fastener radius
(`max(3.6 mm, drill radius + 0.5 mm) + 0.31 mm`) to internal copper too.
At H_NEW2, a 2.4 mm NPTH in the 10 mm board arm, this leaves two 0.58 mm
filled strips on each of four internal layers. The independent native
review confirms that geometry; it does not establish a current rating.

The next candidate keeps the existing surface fastener/component/via
reserves and all hole positions. Only the four new internal corridor zones
use drill radius + 0.51 mm as their circular exclusion. The nominal board
edge clearance remains 0.51 mm. Copper below the fastener is inside the
laminate; no surface lands or exposed copper are introduced beneath it.
These are non-plated holes, and the copper exclusion is measured from
their nominal drilled edge. The footprint holes remain unchanged.

[Epec's published board specifications](https://www.epectec.com/pcb/board-specifications.html),
read 2026-11-06, specify a standard PTH/NPTH-to-plane opening 0.030 inches
larger than the finished hole (0.381 mm radial clearance), and 0.015 inches
(0.381 mm) from the hole to an inner trace. The candidate's 0.51 mm nominal
clearance exceeds those dimensions. This comparison is a design reference,
not a fabrication agreement with Epec or another supplier.

[Eurocircuits' copper guidelines](https://www.eurocircuits.com/technical-guidelines/pcb-design-guidelines/copper-layers/)
give 0.40 mm internal copper-to-routed-edge clearance and advise avoiding
narrow webs and removing unused NPTH copper pads. The candidate retains
0.51 mm board-edge clearance and adds no NPTH pads.

Native refill, hole interpretation, exact geometry and connectivity must
be checked again. Finished drill/registration tolerances, laminate stack,
fastener installation limits, current sharing, temperature rise and the
whole installed assembly remain unqualified. This change does not approve
a manufacturer, assign a current rating, or authorize fabrication.
