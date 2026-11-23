# 19 V regulator feedback and compensation

P_C34 now connects between the output and inverting input of error amplifier P_U5. The output trace to the capacitor is 4.08 mm long. The feedback trace is 9.71 mm long. The R21 and R22 divider joins the feedback trace at a branch on the front layer. All four assigned feedback pads are connected. [Route geometry](layout.json) · [Connectivity](connectivity.json)

KiCad counted 718 remaining opens and verified that every other pad group was preserved. A ground via within 2.40 mm of each layer change connects the adjacent reference planes. The new traces have ground coverage up to the signal via clearances. The existing routed signals retain their ground reference. [Ground measurements](plane-review.json)

All eight layers refill reproducibly. The signal and power placements match the enclosure capture. Copper clears the surveyed isolation-package midlines. The power schematic retains two ground-pin ERC warnings. [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
