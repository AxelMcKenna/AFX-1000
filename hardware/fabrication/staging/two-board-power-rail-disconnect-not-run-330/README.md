# Rail disconnect interlock logic

The E28_NOT_RUN connection joins pins 9 and 2 of E_U28. All three sections use the In6 ground plane as their reference. Two 0.30 mm drills connect the back and In5 signal sections.

KiCad verified the intended join and 818 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/E28_NOT_RUN | E_U28:9, E_U28:2 | B.Cu, In5.Cu | 21.47 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
