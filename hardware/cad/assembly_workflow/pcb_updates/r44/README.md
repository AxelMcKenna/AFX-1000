# R303 mechanical capture revision

The builder accepts exactly A_R303 F.Cu translation(120,73)→(109,82.5), with all other footprint physical fields unchanged. It translates the existing receiving box by(-11,+9.5,0), retains its height and package assumptions, and regenerates the selected body allocation module. Frozen structural CAD is unchanged.

The moved receiving box clears all other modeled parts/allocations. Its own signal-board substrate contact is excluded; a separate planar check proves zero intersection with the other power PCB. Native positive operands and the empty intersection are retained. This is receiving-envelope verification, not supplier height approval.

The assembly manifest explicitly selects this capture. A regression proves switching captures invalidates board freshness even when PCB filenames are unchanged; unchanged capture/boards reuse the verified result. Future routing-only revisions such as r46 preserve this placement and can reuse mechanical checks after exact physical comparison.
