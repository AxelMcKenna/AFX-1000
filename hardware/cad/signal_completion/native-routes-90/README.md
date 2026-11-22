# Input-ready interconnect

LINK_INPUT_READY runs 206.87 mm on In2 and In3. Each of its two layer changes has a ground via within 0.82 mm of the signal via. Native refill verifies continuous adjacent ground copper for every leg and both return vias.

The 5 V distribution gains two connections to existing supply vias. An 11.64 mm back-layer trace from D_J1001 pin 1 feeds the via at (217.945, 67.000) mm. A 14.38 mm In5 trace from D_J1014 pin 1 feeds the via at (222.250, 54.750) mm. The traces widen where clearance permits. At four simultaneous 96 mA header loads, the highest modeled drop across four mesh pitches changed from 6.60 to 6.26 mV. The model uses 18 µm copper, 20 µm via plating and a 20 °C reference temperature. Complete rail, cable and LED forward-voltage margins remain open.

KiCad verified 36 open connections, zero geometry violations and zero ERC findings. A_U201 still requires the ES9292QPRO footprint.

[Routing and ground checks](reference-review.json) · [Sheet model](power-sheet.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
