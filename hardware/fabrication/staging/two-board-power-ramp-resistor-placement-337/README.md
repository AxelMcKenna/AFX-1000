# Negative rail ramp resistors

N_R89 (39 Ω) now sits beside the −12 V capacitor bank, and N_R72 (27 Ω) sits beside the −19 V bank. Both use the same 0805 land pattern. They exchanged sites on the front layer, preserving the two modeled component envelopes. Before the move, their capacitor-side pads were 60.1 mm and 44.7 mm from the nearest pad of the same net. After placement, these distances are 3.5 mm and 6.1 mm. The 0.40 mm traces in the table connect those pads to the ramp capacitors. The opposite pads remain open.

KiCad verified both joins and 798 remaining open connections. [Placement and envelope comparison](component-placement.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N12_CR_TOP | N_R89:2, N_C49:1 | F.Cu | 8.28 |
| /N_negative_startup_protection/N19_CR_TOP | N_R72:2, N_C15:1 | F.Cu | 5.88 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
