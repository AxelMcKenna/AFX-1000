# Negative rail load branches

KiCad verified 3 connections and 784 remaining opens. The 0.80 mm supply branches reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The In5 ground edge rounded locally at the −12 V capacitor branch via. All previous adjacent-layer returns and ground regions passed the native comparison. The input power plane retained its island and hole counts, with at most 0.000006 mm of boundary rounding. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N19_SOURCE | N_C30:2, N_C10:2 | F.Cu, In5.Cu, B.Cu | 13.70 |
| PWR_N12_POST_NF | N_C43:2, N_C46:2 | F.Cu, In2.Cu, F.Cu | 14.81 |
| PWR_N19_POST_NF | E_J1:3, E_R14:1 | B.Cu, In2.Cu, B.Cu | 24.43 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
