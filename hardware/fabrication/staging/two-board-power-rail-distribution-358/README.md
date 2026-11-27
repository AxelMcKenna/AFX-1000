# Raw positive and negative controller rail distribution

KiCad verified 5 connections and 754 remaining opens. The 0.80 mm supply branches reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/RAW_P22 | P_C36:1, P_C59:1 | B.Cu | 9.60 |
| PWR_N12_POST_NF | N_J4:2, N_C46:2 | B.Cu | 12.22 |
| PWR_N12_SOURCE | P_J2:5, N_C51:2 | F.Cu | 9.73 |
| PWR_N12_SOURCE | N_C32:2, N_C38:2 | In3.Cu | 10.35 |
| PWR_N12_SOURCE | N_C51:2, N_C38:2 | In3.Cu | 21.98 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
