# Digital 5 V undervoltage threshold reference

M_R91 now sits by M_C30 and the M_U4 pin 8 comparator input. Its threshold terminal connects to M_C30 through 3.92 mm of bottom copper. The other terminal joins the reference distribution at M_R33 through 4.29 mm. Both traces run over In6 ground. The upstream 2.5 V reference distribution and powered threshold verification remain open.

KiCad verified both intended pad-group joins and 841 remaining open connections. [Resistor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
