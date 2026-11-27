# Regulated 5 V overvoltage sense divider

M_R81 pin 2 joins the existing M_U4 pin 6 sense and M_C27 filter-capacitor group. M_R80 pin 2 connects to M_R81 pin 1 at the divider midpoint. The two bottom-side traces measure 2.58 mm and 1.11 mm and share the In6 ground reference. M_R80 pin 1 still needs the regulated 5 V feed.

KiCad verified both intended pad-group joins. The board has 851 open connections. [Resistor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
