# Permission routing candidate 01 — not selected

Native checks report 2,237 opens, zero geometry/parity errors and two retained
ERC warnings. The independent audit verified the declared 30 joins and other
connectivity, ground ownership and source-plane changes, then rejected the
candidate for lost prior adjacent references. The diagnostic finds 18 retained
track/reference regressions and 12 new projection gaps. These are not waived.
TBP43 remains selected. See [reference diagnosis](reference-regressions.json).

The subsequent cleanup reroutes crossing In6 paths, repairs bottom pull-up
escapes and stitches a disconnected ground region. Four new projection gaps
are at signal through-hole header pads, where a same-net plated-pad antipad
exclusion must be explicitly modeled and reported, just as for signal vias.
[Pin-role review](permission-pin-role-review.json) clarifies three historical
routing labels: U31.3 drives native AUX_VALID into U42.6; U42.2 drives NF AUX_VALID.
The routing follows the correct nets; those labels do not indicate net changes.
