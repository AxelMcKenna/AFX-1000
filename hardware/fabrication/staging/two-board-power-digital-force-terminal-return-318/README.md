# Digital force terminal return

The plated ground barrel at E_J4 pin 2 now connects directly to the existing In1 and In5 ground pours. Two opposing 1.00 mm spokes on each layer bridge the clearance around the pad. In1 uses the vertical pair and In5 uses the horizontal pair. Each spoke overlaps its target plane across a 0.99 mm diameter. The copper around the other sides of the barrel remains clear for soldering. The change adds no drills.

KiCad verified one ground-group join and 838 remaining open connections. The force-return stud interconnect and end-to-end resistance still require completion and verification. The AWG14 solder joint requires assembly process qualification.

[Spoke geometry](layout.json) · [Plane contacts](plane-review.json) · [Connectivity](connectivity.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
