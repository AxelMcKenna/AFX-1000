# Power and protection PCB

A 0.60 mm front-layer trace connects P_C66 directly to the positive 17 V rectifier output at P_D3. A 0.40 mm back-layer trace connects F_C403 and F_C404 on the fan switch output rail. Each trace has continuous analog ground beneath it, with at least 0.30 mm of ground beyond the trace edges. KiCad verified both intended joins and counted 734 remaining opens. [Route geometry](layout.json) · [Reference-plane measurements](plane-review.json)

The isolation survey found zero package-midline crossings. The two existing ground-pin ERC warnings remain open. [Connectivity](connectivity.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
