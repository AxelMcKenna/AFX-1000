# Negative rail disconnect modulator capacitors

The 0.20 mm front-layer traces join the Si8751 modulator pins to their external capacitors. The branches use no vias and have continuous In1 ground reference. KiCad verified 2 new connections and 792 remaining opens.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/N12_MCAP2 | E_U4:6, E_C15:2 | F.Cu | 6.63 |
| /E_rail_disconnect/N12_MCAP1 | E_C14:2, E_U4:7 | F.Cu | 8.36 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
