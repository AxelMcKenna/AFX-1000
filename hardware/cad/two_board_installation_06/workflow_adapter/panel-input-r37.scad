// Additive r37 candidates. Replace both original holder roles; no selection here.
use <../r37_tap_auto/routes.scad>
use <../r37_tap_auto/control_variant.scad>
module panel_signal_r37_tap(){panel_signal_S05();}
module panel_signal_r37_auto(){panel_signal_S06();}
module panel_holders_r37(){panel_r37_button_holders();}
module panel_mechanisms_r37(){panel_r37_button_mechanisms();}
