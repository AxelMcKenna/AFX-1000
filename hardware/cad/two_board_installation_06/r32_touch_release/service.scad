use <../r29_touch_inline/route-draft.scad>
// Project receiving test: lift3 then +Y24 mm; actual latch/mate geometry unknown.
// Installed controls remain diagnosed; a collision is not automatically waived.
module touch_service_sweep(){union(){hull(){touch_inline_receiving();translate([0,0,3])touch_inline_receiving();}hull(){translate([0,0,3])touch_inline_receiving();translate([0,24,3])touch_inline_receiving();}}}
