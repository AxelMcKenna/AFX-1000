include <../../two_board_print_01/captured.scad>
// Exact receiving module extracted from frozen root source, not a supplier maximum.
module tbh04_pot_body_receiving(guard=0){for(k=knobs)translate([k[1]-8,k[2]-8,29.1])cube([16,16,14.5-guard]);}
