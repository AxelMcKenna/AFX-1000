# Right ADC negative connection

A_R119 pin 1 and A_C117 pin 2 now share the right-channel ADC negative input net. The 2.70 mm route uses the front and rear copper layers and one 0.30 mm through-drill. The front trace runs over connected In1 ground and the rear trace runs over connected In6 ground. A ground via 3.13 mm from the signal via contacts both reference regions.

KiCad verifies the intended pad-group merge and 45 remaining opens. The saved ground fills match a fresh refill. Existing traces and adjacent component lands retain their checked reference copper. Plotted mask and paste openings clear the new drill. KiCad reports zero geometry violations, zero ERC findings and the outstanding A_U201 footprint mismatch. Audio performance and assembly qualification remain open.

[Route and reference copper](reference-review.json) · [Connectivity](native-review.json) · [Enclosure check](placement.json) · [DRC](drc.json) · [ERC](erc.json)
