# Panel LED channel 21

D_U3001 pin 26 now reaches D_J3002 pin 3. The 61.80 mm route uses 0.20 mm traces and one 0.30 mm through-drill. Both the front and In2 traces reference the same connected In1 ground island. KiCad verifies 42 remaining opens, zero geometry violations, zero ERC findings and the outstanding A_U201 footprint mismatch. The new via clears the plotted mask and paste openings.

The In2 route displaces part of the digital 5 V pour. The refilled pour retains its connected island. Two mesh resolutions compared the candidate D_J1001 feed with each of the four LED anode headers. The largest modeled resistance increase was 6.3%. At the documented typical single-header loads, the largest modeled drop increase was 0.014 mV assuming 18 µm copper at 20 °C. Simultaneous loading, copper thickness, operating temperature and final feed selection remain unqualified.

[Route and reference copper](reference-review.json) · [5 V plane comparison](power-sheet.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
