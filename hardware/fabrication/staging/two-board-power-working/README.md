# Power and protection PCB

The input TVS diode G_D1 and bypass capacitor G_C1 now share a short supply and return loop. A separate branch joins the output clamp G_D2 to the return of G_C2. All three connections use 0.80 mm front-layer copper and extend their full width inside each terminal land. KiCad verified the three pad joins and counted 731 remaining opens. The filled copper zones on all eight layers match the previous revision. [Route geometry](layout.json) · [Reference-plane measurements](plane-review.json)

The isolation survey found zero package-midline crossings. The two existing ground-pin ERC warnings remain open. [Connectivity](connectivity.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
