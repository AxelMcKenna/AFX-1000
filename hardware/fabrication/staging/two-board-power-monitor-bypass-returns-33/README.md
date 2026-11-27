# Rail-monitor bypass capacitor returns

Ten 100 nF bypass capacitors now connect to analog ground. M_C37 and M_C39 use existing grounded contacts. M_C40 through M_C44 and M_C46 through M_C48 use individual 0.60 mm vias with 0.30 mm drills. The ground traces are 0.30 mm wide and 1.15–2.70 mm long.

The eight new via openings remove 6.33 mm² from each DC input plane. Each opening has a 1.485 mm continuous copper band around it on both layers. Native KiCad connectivity confirms ten joins and 1,602 remaining opens. The power board still requires supply distribution and loaded verification.

[Trace geometry](routes.json) · [Plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
