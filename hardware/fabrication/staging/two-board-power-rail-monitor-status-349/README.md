# Rail protection status

KiCad verified 3 rail-protection status connections. The board has 775 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/P12_OV_OK | E_U36:6, E_R68:1 | B.Cu, In5.Cu | 44.06 |
| /N_negative_startup_protection/N12_OUTPUT_UV_GOOD | N_U44:1, N_R54:2 | F.Cu, B.Cu | 41.73 |
| /N_negative_startup_protection/N19_OUTPUT_OV_GOOD | N_U15:1, N_R39:2 | F.Cu, In5.Cu, B.Cu | 53.25 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
