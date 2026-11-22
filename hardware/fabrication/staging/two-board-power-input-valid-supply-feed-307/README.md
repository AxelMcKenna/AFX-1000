# Negative 19 V input-valid divider feed

The N19_VIN group at N_U18 pin 21 now reaches N_R64 pin 1 over 56.17 mm of 0.30 mm copper. The route changes from the bottom side to In5 at one via. Both layers reference In6 ground. The closest checked ground stitching via is 1.12 mm away. N_R64, N_R65 and N_U21 now form a connected input-valid divider. The trip threshold still requires a powered measurement.

KiCad verified the intended pad-group join. The board has 855 open connections.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
