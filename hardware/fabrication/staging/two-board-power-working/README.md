# Power and protection PCB

The module eFuse output at G_U1 pins 23 and 24 now connects to clamp G_D2. The force trace is 0.80 mm wide and splits into two equal 0.25 mm pin connections shorter than 0.61 mm. All eight layers retain the same filled copper after refill. KiCad verified the intended pad groups and counted 730 remaining opens. [Route geometry](layout.json) · [Reference-plane measurements](plane-review.json)

The isolation survey found zero package-midline crossings. The two existing ground-pin ERC warnings remain open. [Connectivity](connectivity.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
