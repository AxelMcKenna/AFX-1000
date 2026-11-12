// Workflow aliases only. Frozen source modules own all geometry and parameters.
// Coordinates are installed housing millimetres. No top-level solids or overrides.
use <../r9/cooling_candidate.scad>
use <../r8/terminal_harness.scad>
use <../r10_interfaces/panel_mates.scad>
module cooling_shell(){tbh09_shell_variant();}
module cooling_installed(){tbh09_installed();}
module cooling_fans(){tbh09_fans();}
module cooling_internal_harness(){tbh08_harness();}
module cooling_external_harness(){tbh09_external_leads();}
module cooling_tie_path(){tbh09_tie_paths();}
module cooling_tie_head(){tbh09_tie_head_reservations();}
module panel_mates(){tbh10_panel_mates();}
