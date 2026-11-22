# Left fan output and bypass placement

F_C203 rotates 180°. Its body center moves to (38.5, 162.5) mm and its pin 1 datum moves to (36.0, 162.5) mm. Its positive lead faces the fan connector. A 1.00 mm inner trace connects the capacitor to F_J202, and a 1.20 mm front trace connects F_J202 to the F_U201 load switch. Both branches have connected ground copper on the adjacent In1 layer. The original 5.28 mm ground trace at the capacitor's previous negative lead has been removed.

KiCad verified both supply joins and all prior pad groups, leaving 971 opens. The closest modeled body clears F_C203 by 0.48 mm. Supplier-approved component heights, installed isolation and fan performance remain open.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
