# Codec 3.3 V supervisor

A_U205 connects its open-drain reset output to CODEC_PGOOD through one 0.60/0.30 mm via. New front-layer traces reconnect SENSE to the existing A3V3 via, ground to the original ground via, and VDD and MR to the 3.3 V logic supply. Its bypass capacitor A_C221 remains beside it. Native connectivity verifies 52 remaining connections and the pending ES9292QPRO footprint.

[Supervisor placement](component-placement.json) · [Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
