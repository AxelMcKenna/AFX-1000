# Run permit and clamp LED

KiCad verified 2 startup control connections. The board has 750 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_POWER_RUN | P_U201:1, P_U102:3 | In5.Cu | 28.38 |
| /N_negative_startup_protection/N19_CLAMP_LED_MID | N_R98:1, N_U5:2 | In5.Cu | 30.00 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
