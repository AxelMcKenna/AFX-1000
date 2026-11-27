# Reference amplifier supply

P_U24 pin 8 now connects to the module input feed at bulk capacitor P_C103 pin 1 through 15.71 mm of front-layer copper above In1 ground. The connection joins the existing P_C211 supply group without adding a drill. KiCad verified 844 remaining open connections.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_MODULE_FEED_IN | P_C211:1, P_U24:8 | F.Cu | 15.71 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
