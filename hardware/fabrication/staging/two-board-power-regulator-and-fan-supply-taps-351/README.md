# Regulator input and fan-control supply branches

KiCad verified 4 connections and 770 remaining opens. The 0.80 mm supply branches reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_5V_DIG_SRC | F_C11:1, F_C1:1 | F.Cu, In2.Cu, F.Cu | 10.02 |
| /P_power_supply/RAW_P17 | P_U8:5, P_C65:1 | F.Cu, In2.Cu, B.Cu | 11.39 |
| /P_power_supply/RAW_P22 | P_C60:1, P_C59:1 | B.Cu, F.Cu, B.Cu | 16.45 |
| PWR_5V_DIG | E_C24:1, M_R88:1 | F.Cu, B.Cu, F.Cu | 24.19 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
