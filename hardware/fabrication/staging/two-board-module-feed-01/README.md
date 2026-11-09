# Module feed calculation basis

[design.json](design.json) records the first protected-input proposal, its
13 components, source endpoints and numerical screens. Its assumptions are
explicit receiving requirements, not measured module performance.

The circuit is captured in [TBP08](../two-board-power-native-08/README.md).
Independent fault review found that its TPS259474 can enter current limit after
fast trip without a guaranteed thermal cutoff in every undervoltage load state.
**Do not release this proposal unchanged.** See the
[timer-cutoff follow-up](../two-board-module-cutoff-review-01/README.md).

The official TI and Vishay PDFs are archived in `sources/` and bound by SHA-256.
The TRACO input and model tables were read from the official search-indexed
August 7, 2024 datasheet. Direct retrieval returned HTTP 403; no local TRACO PDF
or complete original package/thermal review is claimed.
