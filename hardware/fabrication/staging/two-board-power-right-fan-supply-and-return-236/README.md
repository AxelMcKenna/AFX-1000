# Right fan output and return

The fan load switch F_U301, bypass capacitor F_C303 and connector F_J203 share a continuous front-layer supply connection. The switch-to-capacitor branch is 1.00 mm wide and 8.51 mm long. The capacitor-to-connector branch is 1.20 mm wide. The added In1 ground copper provides the adjacent return beneath both supply branches. F_J203 pin 1, F_C303 pin 2 and the ground contacts of F_C301 and F_R3 connect to board ground.

KiCad verified six intended pad-group joins and 973 remaining opens. The ground comparison measures added and removed copper and checks its projected clearance to the run-loop nets and isolation packages. Installed isolation and loaded fan voltage remain open.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
