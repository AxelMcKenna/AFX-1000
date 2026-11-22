# Panel LED channel 46

D_U3002 pin 27 now reaches D_J3002 pin 14 over 69.12 mm of 0.20 mm copper on F.Cu and In2. Both segments reference the same connected In1 ground island. The CONTROL_20 via moved 0.31 mm. Its In3 and In5 traces still reach their original endpoints. KiCad verifies 39 remaining opens, zero geometry violations, zero ERC findings and the missing A_U201 codec footprint.

The ground pad at D_J1009 pin 1 uses a 45° thermal relief. All three original ground layers retain three connections to the main ground island. Five sections through each relief check the spoke widths. Across two mesh pitches and three perimeter distances, modeled local land-to-plane resistance fell by 5.5% to 21.8%. The connector position and drill are unchanged. [Thermal relief measurements](thermal-review.json)

The LED route narrows the In2 digital 5 V feed. A 2.34 mm long, 1.00 mm wide F.Cu trace connects D_J1014 pin 1 to the downstream pour through a new 0.30 mm drill with a 0.60 mm land. The via clears the plotted mask and paste openings. The separate series-path model excludes the narrow In2 path. Its largest calculated drop from the candidate D_J1001 feed is 2.116 mV at the documented single-header loads, assuming 18 µm copper at 20 °C, 20 µm barrel plating and two full 1.6 mm barrels. Simultaneous loads, final feed assignment and fabricator stackup remain open. [Feed strap](feed-strap.json) · [Supply calculations](power-sheet.json)

[Route and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
