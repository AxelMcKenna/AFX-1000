# Rail control and analog ground routing

Sixteen surface traces close sixteen power-board connections. Eleven 0.30 mm traces connect analog ground pads to existing ground vias in the setpoint, soft-start, rail load and amplifier circuits. Five 0.25 mm traces connect the positive 12 V feedback divider, negative 19 V setpoint filter, 2.5 V monitor reference and the timing capacitor pairs for negative 12 V and negative 19 V startup.

The adjacent analog ground plane covers every new trace after refill. All filled plane areas match revision 38. KiCad confirms exactly the sixteen intended pad-group joins, leaving 1,577 open connections. Geometry and schematic parity checks pass. ERC retains two isolated-ground warnings. The board outline and footprints match the paired assembly capture. Fresh mask and paste plots give the same via clearances as revision 38.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
