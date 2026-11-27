# Armed status interconnect

LINK_ARMED has 232.73 mm of 0.20 mm copper. It runs on In2, crosses to In5, returns to In2 and finishes on the front. The first two transitions each have a ground stitch, 1.14 mm and 1.01 mm from the respective signal via. The last transition shares one continuous In1 ground island. Native checks cover all four legs and confirm that their required stitches contact the corresponding return islands.

The existing 5 V LED supply feeds remain connected. With four simultaneous 96 mA header loads, the largest modeled drop across four mesh pitches changed from 6.264 to 6.295 mV. The model includes copper and plated barrels at 20 °C. Cable drop, loaded hardware operation and full LED voltage margin still require qualification.

KiCad found 35 open connections, zero geometry violations and zero ERC findings. The ES9292QPRO footprint remains missing at A_U201.

[Routing and ground checks](reference-review.json) · [Sheet model](power-sheet.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
