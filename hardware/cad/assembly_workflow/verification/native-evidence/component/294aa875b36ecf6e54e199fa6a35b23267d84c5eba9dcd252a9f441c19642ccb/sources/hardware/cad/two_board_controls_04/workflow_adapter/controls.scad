// Generated adapters: no top-level geometry. World frame millimetres.
use <../button_follow_on/buttons.scad>
use <../connected_guide.scad>
use <../display.scad>
use <../led_follow_on/banks.scad>
use <../led_follow_on/button_motion.scad>
use <../led_follow_on/meters.scad>
use <../pot_follow_on/body_receiving.scad>
use <../pot_follow_on/knobs.scad>
use <../ring_follow_on/ring.scad>
use <../selectors.scad>
use <../workflow_adapter/key_scope.scad>
use <../workflow_adapter/touch_reserve.scad>

module controls_display(){tbh04_display_installed(); tbh04_fasteners();}
module controls_display_wiring(){tbh04_wire_reserve();}
module controls_selectors(){tbh04_selector_brackets(); tbh04_selector_pcbs(); tbh04_selector_bodies(); tbh04_selector_leads(); tbh04_selector_fasteners();}
module controls_selector_wiring(){tbh04_selector_wiring();}
module controls_selector_motion(){tbh04_selector_motion();}
module controls_meters(){tbh05_meters_frames(); tbh05_meters_boards(); tbh05_meters_emitters(); tbh05_meters_fasteners();}
module controls_meters_lenses(){tbh05_meters_lenses();}
module controls_meters_wiring(){tbh05_meters_wires();}
module controls_banks(){tbh05_banks_frames(); tbh05_banks_boards(); tbh05_banks_emitters(); tbh05_banks_fasteners();}
module controls_banks_lenses(){tbh05_banks_lenses();}
module controls_banks_wiring(){tbh05_banks_wires();}
module controls_ring(){tbh06_pose(){tbh06_frame(); tbh06_board(); tbh06_emitters(); tbh06_resistors(); tbh06_fasteners();}}
module controls_ring_lens(){tbh06_pose()tbh06_lens();}
module controls_ring_wiring(){tbh06_pose()tbh06_wires();}
module controls_button_indicators(){tbh07_boards_installed(); tbh07_emitters(); tbh07_solder(); tbh07_shims(); tbh07_fasteners();}
module controls_button_wiring(){tbh07_wires();}
module controls_button_motion(){tbh05_button_motion_native();}
module controls_lid(){translate([0,0,43.6])tbh07_lid_variant();}
module controls_guide(){translate([0,0,42.2])tbh07_connected_guide_variant();}
module controls_knobs(){tbh04_pot_knobs_installed();}
module controls_pot_hardware(){tbh04_pot_panel_hardware();}
module controls_pot_shafts(){tbh04_pot_shafts_max();}
module controls_pot_body(){tbh04_pot_body_receiving();}
module controls_keycaps(){controls_keys_delegate();}
module controls_switches(){controls_switches_delegate();}
module controls_retaining_clips(){controls_clips_delegate();}
module controls_button_mechanisms(){controls_mechanisms_delegate();}
module controls_touch_backer(){controls_touch_backer_delegate();}
module controls_touch_lens(){controls_touch_lens_delegate();}
module controls_touch_module_receiving(){controls_touch_reserve_delegate();}
