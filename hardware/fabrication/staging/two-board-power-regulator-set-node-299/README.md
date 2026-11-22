# Positive 12 V regulator SET resistors

P_R25 (200 kΩ) and P_R28 (6.8 kΩ) connect to the existing via for the LT3080 SET node at P_U8 pin 2. Both bottom traces use 0.30 mm copper and reference In6 ground outside the existing via clearance. The other resistor terminals still require routing to P12_RMID and P12_DRIVE.

KiCad verified two pad-group joins. The board has 868 open connections. [Resistor placements](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
