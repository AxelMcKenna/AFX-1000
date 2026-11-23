# Power and protection PCB

F_C402 now connects directly to the fan power switch input through a 0.40 mm trace on each face and a 0.30 mm through drill. A separate ground via connects the capacitor return to both reference planes. KiCad verified the intended connection and counted 736 remaining opens. [Route geometry](layout.json) · [Reference-plane measurements](plane-review.json)

The isolation survey found zero package-midline crossings. The two existing ground-pin ERC warnings remain open. [Connectivity](connectivity.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
