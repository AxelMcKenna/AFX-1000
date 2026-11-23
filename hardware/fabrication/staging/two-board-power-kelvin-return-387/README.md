# 12 V disconnect driver source return

A 13.47 mm front-layer trace connects the common source of E_Q5 and E_Q6 to the isolated gate driver's output reference and the gate pulldown. All eight pads on P12_COMMON now share one copper connection. The branch is 0.30 mm wide and uses no vias. All existing zone fills reproduce without a change in area. [Routing](layout.json) · [Connectivity](connectivity.json) · [Copper review](plane-review.json)

KiCad counts 710 open connections. Geometry and schematic parity checks pass. The placement still matches the enclosure capture and copper clears the surveyed isolation-package midlines. Two isolated-reference ERC warnings remain. [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
