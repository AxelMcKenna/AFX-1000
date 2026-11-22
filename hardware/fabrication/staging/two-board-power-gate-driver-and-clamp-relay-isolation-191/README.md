# Gate-driver and clamp-relay copper separation

All eight copper layers exclude pads, vias, traces and fills between the contact banks of N_U5 and E_U4. Both keepouts extend beyond the ends of the contact-bank midlines.

- N_U5 has a 1.50 mm wide, 7.10 mm long keepout.
- E_U4 has a 2.00 mm wide, 4.83 mm long keepout.

The whole-board isolation survey found 38 layer intersections, down from 46. Native connectivity retains the same named pad groups and 1,073 opens. Refilling the saved layout reproduces its copper geometry. The changed ground layers retain their island counts and existing traces retain their reference copper. Voltage withstand and fabrication qualification remain open.

[Keepout](isolation-rule.json) · [Filled copper](plane-review.json) · [Isolation survey](isolation-midlines.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json)
