# MCU permit connection

LINK_MCU_PERMIT now connects the processor and bypass-control portions of the signal board. KiCad verified the join and every previously connected pad group. The 0.20 mm route uses seven signal vias. Three new ground vias and four existing ones provide return paths at the layer transitions. Every section runs over continuous grounded copper outside the terminal and via clearances. The longest spacing from a signal via to its verified ground connection is 1.33 mm.

Local ground pours support the trace on In1, In4 and In6. The [ground continuity check](ground-continuity.json) maps the previous ground regions to the new fill. The geometry review found no existing pad contact or trace reference lost to the changes. The digital 5 V plane remains one connected region. At four 96 mA header loads, the largest modeled header drop is 5.214 mV. The largest increase at an individual header is 0.031 mV relative to revision 95.

The permit trace is 287.09 mm long. The inner-layer detour keeps its centerline 1.38 mm from the codec supervisor sense copper. Checking the permit transition for disturbance at the supervisor sense input remains part of bench qualification.

KiCad reports 30 open connections, zero geometry violations and zero ERC findings. A_U201 remains absent pending the ES9292QPRO land and stencil dimensions.

[Routing changes](route.json) · [Ground coverage](reference-review.json) · [Return paths](return-islands.json) · [5 V distribution model](power-sheet.json) · [Adjacent copper](coupling.json) · [Connectivity](native-review.json) · [Enclosure comparison](placement.json) · [DRC](drc.json) · [ERC](erc.json)
