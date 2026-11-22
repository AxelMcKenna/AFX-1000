# Floating negative-rail controller reference

The N19 supervisor pull-up N_R66 sits on the back of the board beneath N_U20. Its supply and reset contacts use 1.96 mm of new 0.20 mm traces in total. The reset signal retains the via beside N_U20 pin 6. The former 10 mm inner-layer reset run and its remote via have been removed. A local trace connects the floating reference pins of N_U20 and N_U21.

Front and back PWR_N19_SOURCE copper connects the LTC4261 controller N_U18 reference pins to its local capacitors and resistors through four 0.60 mm vias with 0.30 mm drills. KiCad verified all six intended pad-group joins, with 985 remaining opens. The minimum modeled body clearance at N_R66 is 8.56 mm. The 5 V and inlet pours retain their previous copper. At the board edge, the adjacent supervisor vias trim 0.0035 mm² or less beyond their local clearance envelope on each ground layer. This area clears every earlier trace and land. Installed isolation and loaded rail performance remain open.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
