# Codec PLL regulator capacitors

A_C210 (100 nF C0G) and A_C211 (1 µF tantalum) sit on the front side beside the reserved codec location. Their positive terminals share 5.21 mm of 0.20 mm copper. A_C210 has a 0.40 mm connection to its own 0.60 mm ground via with a 0.30 mm drill. A_C211 reaches an existing ground via. Both vias contact the same continuous In1 ground region beneath the three traces.

KiCad verified the intended pad-group merge, 33 remaining opens, zero geometry violations and zero ERC findings. The signal schematic still calls for ES9292QPRO at A_U201. Its package drawing is needed to place pin 24 and verify the final PLL decoupling loop. The two-board capture uses modeled component envelopes.

[Ground and routing checks](reference-review.json) · [Connectivity](native-review.json) · [Placement](component-placement.json) · [Paired board check](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Prior LED and control review](../native-routes-92/README.md)
