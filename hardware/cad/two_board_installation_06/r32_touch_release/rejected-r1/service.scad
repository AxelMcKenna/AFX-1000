use <../r29_touch_inline/route-draft.scad>
// Project receiving test only: released latch, mating axis +Y, travel24 mm.
// Sweeps the entire23 mm box conservatively, not a controlled JST motion model.
module touch_service_sweep(){hull(){touch_inline_receiving();translate([0,24,0])touch_inline_receiving();}}
