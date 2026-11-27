# Negative-startup supervisor supply and return

N_U54 monitors negative-rail startup. A 4.18 mm front trace now runs from P_C106 pin 1 on the 2.5 V regulator output to the supervisor's VDD pin 4. A 1.15 mm strap ties its manual-reset input to VDD as specified by the schematic. Its ground pin reaches an existing grounded via over a 3.45 mm trace. All three traces are 0.25 mm wide.

KiCad 10.0.7 reports 1,714 open connections, down from 1,717. The three pad-group joins agree with the schematic. The receiving-envelope comparison confirms both boards keep their reviewed placement. The supervisor's sense, timing and output circuitry and loaded startup behavior still require verification.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Reference-plane coverage](reference-review.json) · [Retained copper](retention.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-bypass-13/README.md)

The saved and refilled boards pass geometry and schematic parity checks. All 47 zone-layer fields match the independently refilled parent. [Regulator output and ground continuity](supervisor-review.json) · [Refill comparison](refill-comparison.json)
