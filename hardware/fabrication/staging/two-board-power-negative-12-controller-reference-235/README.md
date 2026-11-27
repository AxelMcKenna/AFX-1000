# Negative 12 V controller reference

Front and back PWR_N12_SOURCE copper links the LTC4261 controller N_U23 to the return contacts of nine nearby capacitors. Six 0.60 mm through vias with 0.30 mm drills join the local copper. The outer trace branches are 0.40 mm wide, and the inner connections are 0.60 or 0.80 mm wide.

KiCad verified all six intended pad-group joins and 979 remaining opens. The connectivity check covers every original pad group and every new via. The copper review identifies the pads and vias attached to each new filled region. Installed isolation and loaded rail performance remain open.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
