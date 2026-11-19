# Negative-startup control bypass return

N_C39, the 100 nF capacitor on PWR_NF_RAW5, now connects to analog ground through a 1.35 mm bottom-layer trace and a 0.60 mm via with a 0.30 mm drill. The trace is 0.30 mm wide and runs over In6.Cu ground. The new via clears the DC input planes. Native KiCad connectivity confirms the intended join and 1,600 remaining opens. Effective capacitance and loaded startup behavior still require verification.

[Trace and via](routes.json) · [Plane comparison](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
