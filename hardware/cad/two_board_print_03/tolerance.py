"""Conditional receiving limits; these are measured acceptance limits, not printer guarantees."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent
G=(1.95,2.05);shim=(.88,.92)
endplay=(G[0]-2*shim[1],G[1]-2*shim[0]);assert endplay[0]>=.1 and endplay[1]<=.3
# Conservative +/-0.3 mm rotor axial position. Guard face measured at332.3 +/-0.1.
shaft=(15.9,16.1);face=(332.2,332.4);rotor_shift=(-.3,.3)
shaft_tip=(315+rotor_shift[0]+shaft[0],315+rotor_shift[1]+shaft[1])
free_gap=(face[0]-shaft_tip[1],face[1]-shaft_tip[0]);assert free_gap[0]>0
# At the furthest right permitted shaft position, rod still spans full right bearing.
rod_left=face[1]-shaft[0];right_bearing=(324,327)
engagement=min(323+rotor_shift[0],face[0])-max(315+rotor_shift[1],rod_left)
assert rod_left<right_bearing[0] and face[0]>right_bearing[1] and engagement>5
v=dict(scope='Measured conditional limits for unpowered fit prototype',units='mm',total_hub_gap_receiving_mm=G,each_default_shim_receiving_mm=shim,total_endplay_mm=endplay,shaft_length_receiving_mm=shaft,shaft_diameter_receiving_mm=[2.98,3.00],guard_inner_face_receiving_x_mm=face,rotor_axial_allowance_mm=rotor_shift,seated_tip_x_mm=shaft_tip,seated_shaft_to_guard_gap_mm=free_gap,maximum_walk_rod_left_x_mm=rod_left,minimum_hub_engagement_after_walk_mm=engagement,right_bearing_engagement_mm=3,right_screw_length_mm=25,right_screw_underhead_z_mm=20.5,right_screw_tip_z_mm=-4.5,minimum_feet_height_mm=6,nominal_screw_tip_ground_clearance_mm=1.5,receiving_notes=['Verify measured endplay0.10..0.30 across full stroke; never use clamping screws to force an undersized gap.','Verify radial free motion with actual shaft and deburred bearing bores.','Guard face tolerance is an assembly measurement relative to original datum, not a universal printer accuracy claim.','No allowance for load-induced guard deflection; manual unpowered fit only.'])
(R/'tolerance-review.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v,indent=2))
