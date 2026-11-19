# Power reference filter and monitor dividers

Seven 0.20 mm surface connections join the reference filter, its 5 V input branch and two resistor dividers. Each trace has continuous adjacent ground along its full width after a zone refill. The routes use no vias.

| Net | Pads joined by the route | Length | Layer |
| --- | --- | ---: | --- |
| P03_REF_FILTER | P_C249.1 to P_C246.1 | 3.50 mm | B.Cu |
| N19_OV_REF_BASE | M_R20.2 to M_R22.1 | 4.96 mm | F.Cu |
| P03_REF5 | P_R240.1 to P_C252.1 | 5.84 mm | B.Cu |
| P03_REF_FILTER | P_C248.1 to P_C251.1 | 7.72 mm | F.Cu |
| P19_RMID | P_R20.2 to P_R21.1 | 7.40 mm | B.Cu |
| P03_REF_FILTER | P_C245.1 to P_C250.1 | 7.43 mm | B.Cu |
| P03_REF_FILTER | P_C245.1 to P_C247.1 | 9.57 mm | B.Cu |

KiCad 10.0.7 verifies all seven intended pad-group joins and 1,663 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Full filter connectivity, noise performance and loaded rail behavior remain open.

[Trace geometry](routes.json) · [Connectivity](connectivity.json) · [Plane changes](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-validity-returns-25/README.md)
