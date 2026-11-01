# FPC01-M1: native mount keepouts

This 84-part successor implements the FR01 edge-clip contact areas in the actual
66 × 38 mm fan power/health PCB. The original sealed FPC01 and FR01 packets are
unchanged. All 84 complete footprints remain identical to FPC01, including pad,
pose, value, footprint and symbol-path data. All unrelated track/via trees remain
identical. The narrow clock and sensor routes were not disturbed.

Four clip sites at PCB-local x = 17 and 54.5 mm, on both board edges, each have
7.2 mm-wide keepouts on all four copper layers. Tracks, vias, pads and pours are
forbidden through the complete keepout depth of 1.65 mm. The physical receiving
contact is 6 × 1.2 mm; the keepout width includes 20% allowance. No soldermask
insulation credit is taken. The receiving rear allowance is 1.2 mm for complete
SMD height and 1.5 mm for through-hole tail plus fillet; these are receiving
requirements, not measured assembled-board dimensions.

Only RAW5 copper required rerouting. Two existing 0.65/0.30 mm tented vias move
away from the bottom and top keepouts. The 1 mm B.Cu supply trunk turns before
the upper clip, and its low-current branch uses a 0.2 mm B.Cu route around the
fixed tach, clear and ground vias. Native failures from the intermediate routes
remain in the packet. The abandoned C++ mutation script failed before saving;
the successful changes use the captured text edits and JSON route ledgers.

The final strict native ERC, all-severity DRC, connectivity and schematic parity
checks have zero findings and no ignored checks. All 68 ground pads connect to
the actual In1 ground plane; all 130 conventional vias remain tented on both
faces. Six portable tests include mutations that remove a keepout, allow vias,
delete unrelated clock copper, move a component and narrow a supply track.
The handoff binds the exact checked PCB and preserved source packets.

This is an electrical layout and mounting interface checkpoint. Polymer,
preload, shims, assembly process, physical fit, source/startup current, fault
energy, PDN, noise, installed airflow and temperature remain unqualified.
The final complete unit has not adopted this PCB in a refreshed MCAD receipt.
This packet does not authorize fabrication.
