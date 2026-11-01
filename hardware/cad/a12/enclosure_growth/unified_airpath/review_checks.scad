// Fresh changed review families; all parents remain immutable.
include <generated/entry_v6.scad>
if(ua_case=="review_electronics")render()ui_electronics(false,false);
if(ua_case=="review_remaining_power")render(){ui_h9_head();tc2_heads();}
