"""Mechanical contract and independent scalar checks; not native collision proof."""
import json, math, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[2]
def spring(a):
 r=math.radians(a)
 fixed=(316,70,35.6); moving=(316,82+10*math.sin(r),31.6+10*math.cos(r))
 v=tuple(fixed[i]-moving[i] for i in range(3));length=math.sqrt(sum(x*x for x in v))
 # Torque per unit spring tension around pivot X, restoring direction negative.
 ry=moving[1]-82;rz=moving[2]-31.6
 moment=abs(ry*v[2]-rz*v[1])/length
 return {'angle_deg':a,'fixed_eye_mm':fixed,'moving_eye_mm':moving,'eye_spacing_mm':length,'restoring_moment_arm_mm':moment}
def main():
 positions=[spring(a/10) for a in range(351)]
 assert all(b['eye_spacing_mm']>a['eye_spacing_mm'] for a,b in zip(positions,positions[1:]))
 assert all(p['restoring_moment_arm_mm']>0 for p in positions)
 report={'scope':'Derived mechanical contract; see verified-r3/review.json for source-bound native clearance evidence; physical verification pending',
 'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'carrier.scad',ROOT/'analysis.py',REPO/'hardware/cad/a11/mechanisms.scad',REPO/'hardware/cad/two_board_print_03/retention_r5.scad']},
 'sensor_board':{'kind':'New custom PCB mechanical specification, NOT an existing board','outline_yz_mm':[72,21.6,92,39.6],'thickness_mm':1.6,'thickness_receiving_mm':[1.5,1.7],'board_x_mm':[299.7,301.3],'edge_slot_x_mm':[299.5,301.5],'copper_component_keepout_mm':{'edge_y':1.0,'edge_bottom_z':1.0,'edge_top_z':1.0},'mounting_holes':[],'package_face_toward_magnet':'+X','nominal_sensor_axis_yz_mm':[82,31.6],'package_envelope_x_mm':[301.3,303.05],'package_envelope_yz_mm':[78.8,28.4,85.2,34.8],'package_envelope_basis':'Conservative mechanical allocation, supplier exact maximum receiving required','backside_wiring_reserve_xyz_mm':[[293.7,76,23],[299.7,88,28]],'backside_population_reserve_xyz_mm':[[298.2,73.1,22.7],[299.7,90.9,38.5]],'alignment_requires':'Measure printed slot clearance and alignment; select shim/adjust CAD before acceptance'},
 'carrier_hardware':{'mounts_existing_xyz_mm':[[306,69,17.6],[306,102,17.6]],'left_bolts':'2 x M3x25, replaces r5 M3x20; 0.5mm washers','left_screw_tip_z_mm':-4.9,'six_mm_foot_clearance_mm':1.1,'top_cap':'2 x M2x5, head OD <=3.8mm height<=2mm, inserted horizontally from opposite Y ends; tap 1.6mm pilots M2; verify engagement before use'},
 'magnet_retention':{'disk_required_mm':[6,2],'magnetization':'diametric','barrier_x_mm':[303.5,304.3],'barrier_hole_diameter_mm':4,'nominal_sensor_package_to_magnet_gap_mm':2.05,'axial_motion_allowance_mm':0.5,'gap_range_mm':[1.55,2.55],'nominal_rotor_face_to_guard_mm':0.7,'minimum_expanded_rotor_guard_gap_mm':0.1,'torque_coupling':'Compatible adhesive still required; guard is positive axial retention only','supplier_grade_and_adhesive':'unselected; field and bond tests required'},
 'spring':{'rest':positions[0],'pulled':positions[-1],'travel_mm':positions[-1]['eye_spacing_mm']-positions[0]['eye_spacing_mm'],'maximum_OD_mm':4,'anchor_hole_diameter_mm':2.2,'required_hook_clearance':'Hook/contact and entire swept spring envelope need native check after exact spring selection','force_selection':'Not selected: target hand force and manufacturer spring load/stroke rating needed','restoring_moment_arm_range_mm':[min(p['restoring_moment_arm_mm'] for p in positions),max(p['restoring_moment_arm_mm'] for p in positions)],'sampling':'0.1 degree samples plus positive analytic derivative throughout 0..35deg'},
 'remaining':['populated custom sensor PCB design and connector','exact spring and hook selection','magnet grade/adhesive receiving','physical axis/gap/AGC/angle/return/load tests']}
 (ROOT/'mechanical-contract.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report['spring'],indent=2))
if __name__=='__main__':main()
