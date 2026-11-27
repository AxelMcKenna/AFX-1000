# Precision reference and bypass ground returns

Both REF5025 output capacitors now have ground returns. On the supply board section, a dedicated 0.35 mm trace connects P_C31 pin 2 to the ground pin of P_U4. A 1.75 mm trace and plated via tie that point to ground. In the monitor section, M_U6 and M_C49 each use a short trace to the adjacent ground plane. M_C45 now also returns to that plane, completing the local bypass connection for M_U11.

Three of the four ground vias pass through the DC input copper on In2.Cu and In3.Cu. Each clearance opening is surrounded by at least 1.485 mm of continuous input copper on both layers. The openings remove 2.3745 mm² of DC input copper per layer. Independent refills preserve all other zone-layer geometries. The local copper measurements leave full-load voltage drop and thermal rise to be verified.

KiCad verifies five intended connections and 1,687 remaining opens. Geometry and schematic parity checks pass. ERC retains the two existing isolated-reference warnings. Both board placements match the assembly capture. Reference noise, stability and supply distribution still require verification.

[Routes](routes.json) · [Input-plane clearance measurements](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-supervisor-reference-18/README.md)
