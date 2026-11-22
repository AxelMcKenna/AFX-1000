# Rail monitor and interlock connections

The rail monitor connector reaches the 5 V supply pin on M_U1. The fan interlock headers share the run signal, and E_J6 reaches the protection reference group at E_U7 and E_C26. KiCad verified three pad-group joins and 845 remaining open connections. Each route uses 0.30 mm traces without additional drills.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_V5_REG | M_J2:6, M_U1:3 | F.Cu | 8.85 |
| PWR_RUN_AFTER_FAN | E_J5:3, F_J4:2 | In2.Cu | 25.32 |
| PWR_PROTECT_REF | E_J6:3, E_U7:6 | In5.Cu | 24.56 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
