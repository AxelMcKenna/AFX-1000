# Analog regulator SET capacitor

P_U22 pin 7 connects to P_C241 pad 1 through 6.22 mm of copper and one 0.30 mm drill. The capacitor return already reaches the regulator ground pins and exposed pad. A ground via 0.88 mm from the SET signal via connects the adjacent reference planes. The SET resistors P_R241 and P_R242 still need their bias connections. [Route geometry](layout.json) · [Connectivity](connectivity.json)

KiCad verified the pad-group join and counted 717 remaining opens. All eight layers refill reproducibly. Ground covers both new traces up to the signal via clearance, and the existing routed signals retain their ground reference. The paired placements match the enclosure capture. Copper clears the surveyed isolation-package midlines. The power schematic retains two ground-pin ERC warnings. [Ground measurements](plane-review.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
