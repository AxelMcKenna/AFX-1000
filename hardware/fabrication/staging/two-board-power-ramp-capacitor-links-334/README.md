# Negative rail ramp capacitor banks

KiCad verified 3 connections between ramp capacitor groups. Each branch uses 0.40 mm copper. The new vias use 0.30 mm drills with 0.60 mm lands. The power board has 806 remaining open connections.

After refill, the In5 ground boundary rounded beside the N12_RAMP trace. The additional loss beyond the nominal clearance was 0.00254 mm². It stayed within 0.461 mm of the trace edge and preserved the existing ground island and the return copper beneath adjacent signals.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N19_POST_NF | N_C14:2, N_C15:2 | F.Cu, In5.Cu, F.Cu | 17.13 |
| /N_negative_startup_protection/N12_CR_TOP | N_C46:1, N_C43:1 | F.Cu, In5.Cu, F.Cu | 21.48 |
| /N_negative_startup_protection/N12_RAMP | N_C50:1, N_C51:1 | In5.Cu | 17.52 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
