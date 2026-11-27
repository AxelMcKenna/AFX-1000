# Positive 12 V gate-drive isolation clearance

The existing positive 12 V gate-drive trace on In2.Cu now passes around isolator E_U3. Its endpoints, 0.25 mm width and connected pads are preserved. The new copper passes 1.42 mm from the projected package midline and has adjacent ground coverage. KiCad verifies 0 pad-group joins and 1,025 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.25 | E_U3:8 to E_R17:1 | In2.Cu | 9.22 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.327%. [Mesh calculations](inlet-sheet-comparison.json)

The eight-layer survey records 18 package-midline intersections, one fewer than the previous board. [Whole-board survey](isolation-midlines.json)
