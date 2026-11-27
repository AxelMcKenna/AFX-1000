# Analog-ready interconnect

LINK_ANALOG_OK now connects the analog-side A_J402 pin 6 to digital-side D_J1006 pin 6. The 0.20 mm trace runs 107.69 mm on In5 and In2. A ground via 0.83 mm from the signal via joins the In6 and In1 reference copper at the layer change. KiCad verified both pad groups, the ground contact on each layer, and 38 remaining opens. Geometry DRC and ERC are clear. A_U201 still requires the ES9292QPRO footprint.

A second 5 V feed at D_J1014 pin 1 runs 4.68 mm on In5.Cu using 0.80 mm copper and a new 0.30 mm through drill. It shares current with the existing 1.00 mm front feed. The highest modeled drop across four LED headers and two mesh pitches is 1.944 mV at the documented typical single-header loads, assuming 18 µm copper at 20 °C and 20 µm barrel plating. [Added feed](added-feed.json) · [Sheet model](power-sheet.json)

[Route and return via](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
