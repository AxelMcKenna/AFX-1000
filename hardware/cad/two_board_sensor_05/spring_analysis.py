"""Selected spring candidate, pin bearing geometry and conditional force model."""
import json, math, hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
# Manufacturer catalogue values for LE014A01 music-wire candidate. Not measured.
C={'manufacturer':'Lee Spring','part':'LE 014A 01 M','material':'Music wire','outside_diameter_mm':3.18,'wire_diameter_mm':0.36,'free_inside_loop_length_mm':12.7,'rate_N_per_mm':0.35,'initial_tension_N':0.53,'catalog_max_load_N':4.89,'catalog_max_inside_loop_length_mm':25.15,'source':'https://www.leespring.co.uk/sites/default/files/2020-01/Lee_Spring_Catalogue_UK_Eng.pdf','source_scope':'Manufacturer catalogue dimensional candidate; availability and current supplier drawing not confirmed','loop_position':'Catalogue random; receiving must confirm compatible loop orientation without forcing/twisting spring'}
def pose(a):
 t=math.radians(a);y=82+7.5*math.sin(t);z=31.6+7.5*math.cos(t);dy=y-70;dz=z-38.6;l=math.hypot(dy,dz)
 # Inside-loop end-to-end length spans the OUTSIDE bearing surfaces of two Ø2 pins.
 inside=l+2.;extension=inside-C['free_inside_loop_length_mm'];f=C['initial_tension_N']+C['rate_N_per_mm']*extension
 arm=abs((y-82)*(38.6-31.6)-(z-31.6)*(70-82))/l
 return {'angle_deg':a,'eye_centres_mm':[[327.5,70,38.6],[327.5,y,z]],'pin_centres_distance_mm':l,'inside_loop_length_mm':inside,'extension_mm':extension,'tension_N':f,'restoring_moment_arm_mm':arm,'torque_Nmm':f*arm,'tangential_hand_force_at_24mm_N':f*arm/24}
def main():
 rows=[pose(i/10)for i in range(351)]
 assert all(r['extension_mm']>0 and r['tension_N']<C['catalog_max_load_N'] and r['inside_loop_length_mm']<C['catalog_max_inside_loop_length_mm'] for r in rows)
 d={'scope':'Conditional design model, not measured force, fatigue or strength qualification','candidate':C,'geometry':'New spring.scad arm/bracket, not unchanged r5 spring anchors','source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'spring.scad',Path(__file__)]},'rest':rows[0],'full_pull':rows[-1],'max_tension_N':max(r['tension_N']for r in rows),'max_torque_Nmm':max(r['torque_Nmm']for r in rows),'catalog_load_ratio':C['catalog_max_load_N']/max(r['tension_N']for r in rows),'axial_receiving':{'spacer_length_mm':8.15,'spacer_OD_mm':4,'spacer_ID_mm':2.2,'washer_x_mm':[327.85,328.25],'nominal_loop_free_gap_mm':.7,'wire_nominal_mm':.36,'nominal_remaining_axial_play_mm':.34,'modeled_spring_axial_reserve_mm':.6},'clevis_pin':{'material':'Brass or verified low-magnetic noncorroding material','shaft_diameter_mm':2,'underhead_length_mm':17,'head_max_OD_mm':3.8,'head_max_height_mm':1.6,'cross_hole_diameter_mm':.6,'cross_hole_distance_from_underhead_mm':15.6,'retainer':'0.5mm split pin, positively spread/bent; receiving envelope X328.2..330, Yeye±3, Zeye±1.2','supplier_part':'Custom receiving drawing/specification; actual supplied part dimensions must be checked'},'receiving_gates':['Manufacturer current spring dimensions/material/load data and loop orientation match candidate','Measure inside-loop length using pin bearing datums, not eye-center distance','Smooth pin fits both printed Ø2.2 holes and unmodified spring loops','Measure spacer/washer/retainer stack and all axial play','No spring loop permanently opened or bent to install','Check spring influence on AS5600 field and angle','Measure return at every angle, friction and stop impact','Repeat cycling/wear and retention checks before functional release']}
 (R/'spring-force-model.json').write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:d[k]for k in ['rest','full_pull','max_tension_N','max_torque_Nmm']},indent=2))
if __name__=='__main__':main()
