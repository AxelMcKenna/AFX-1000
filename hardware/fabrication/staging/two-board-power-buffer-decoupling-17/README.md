# Rail-disconnect logic buffer decoupling

E_C78, the 100 nF bypass capacitor for E_U35, moved 0.50 mm left and 0.75 mm up in board coordinates and rotated 180°. Its supply pad now connects directly to pin 8 with a 2.59 mm trace. Before the move the straight-line distance was 3.91 mm. A 2.00 mm trace connects its ground pad to a 0.60 mm stitching via with a 0.30 mm drill. Both 0.25 mm bottom-layer traces have full-width analog ground underneath on In6.Cu.

Native KiCad connectivity confirms both intended joins and 1,698 remaining opens. Independently refilling the parent and candidate preserves the geometry of all existing copper pours. KiCad reports zero geometry and schematic parity findings. ERC retains two isolated-reference warnings. The 2.5 V supply still requires distribution to the local bypass node.

The capacitor clears the nearest component envelope by 0.25 mm and the modeled cradle regions by more than 64 mm. The local envelope comparison covers the capacitor body, its two new connections and via as applicable. Full installed housing fit, startup behavior, thermal performance and manufacturing qualification remain open.

[Routes](routes.json) · [Native connectivity and refill](connectivity.json) · [Placement comparison](placement.json) · [Paired placement](paired-placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-monitor-dividers-16/README.md)
