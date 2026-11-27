"""Local lead bay revision preserving r7/r8; exact circular external bundle path."""
from pathlib import Path
import json,math
R=Path(__file__).resolve().parent;s=(R.parent/'r7/cooling_candidate.scad').read_text().replace('tbh06_','tbh09_')
s='use <../r8/supports.scad>\nuse <../r8/terminal_harness.scad>\n'+s

def module(name,body):
 global s
 a=s.index('module '+name+'(');b=s.index('{',a);depth=1;c=b+1
 while depth:
  depth+=(s[c]=='{')-(s[c]=='}');c+=1
 s=s[:a]+body+s[c:]
module('tbh09_lead_cavity','module tbh09_lead_cavity(y){translate([-13,y+20.75,5])cube([11,13.65,37.5]);translate([-15.1,y+23,14])cube([2.2,11.4,24]);}')
module('tbh09_lead_bridge','module tbh09_lead_bridge(y){difference(){translate([-10,y+25,9])cube([8.1,10.5,2]);for(yy=[y+26,y+32.9])translate([-5.75,yy,8.9])cube([3,1.4,2.2]);}}')
module('tbh09_pod', '''module tbh09_pod(y=0){difference(){union(){difference(){union(){tbh09_pod_core(y);translate([-15,y+20.75,3.5])cube([15,14.75,41]);}tbh09_lead_cavity(y);translate([-15.1,y+20.2,28])cube([12.3,3,12]);}tbh09_lead_bridge(y);
 for(p=[[24.5,6],[32.5,42]])translate([-13,y+p[0]-2.5,p[1]-2.5])cube([7,5.5,5]);}
 tbh09_lead_bore(y);translate([-1.1,y+30.25,15])rotate([0,90,0])cylinder(d=10.4,h=1.2);
 for(p=[[24.5,6],[32.5,42]]){translate([-18,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2.4,h=13);translate([-8.4,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4.2/cos(30),h=1.8,$fn=6);}
}}''')
module('tbh09_lead_cap','module tbh09_lead_cap(y=0){difference(){translate([-17,y+20.75,3.5])cube([2,14.75,41]);for(p=[[24.5,6],[32.5,42]])translate([-18,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2.4,h=4);}}')
module('tbh09_lead_hardware','module tbh09_lead_hardware(){for(y=tbh09_fan_centres,p=[[24.5,6],[32.5,42]]){translate([-18.6,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4,h=1.6);translate([-17,y+p[0],p[1]])rotate([0,90,0])cylinder(d=2,h=12);translate([-8.3,y+p[0],p[1]])rotate([0,90,0])cylinder(d=4/cos(30),h=1.6,$fn=6);}}')
module('tbh09_tie_paths','module tbh09_tie_paths(){for(y=tbh09_fan_centres){for(yy=[y+26.1,y+33])translate([-5.5,yy,7.4])cube([2.5,1.1,13]);for(z=[7.4,19.3])translate([-5.5,y+26.1,z])cube([2.5,8,1.1]);}}')
s=s.replace('translate([17,-20.75,-8])tbh09_lead_cap()', 'translate([17,-20.75,-3.5])tbh09_lead_cap()')
s=s.replace('module tbh09_installed(){','module tbh09_base_installed(){')
s+='\nmodule tbh09_installed(){difference(){tbh09_base_installed();for(y=[118.5,171.5])translate([2.7,y-4,34])cube([5,8,8]);}tbh08_supports();tbh08_replacement_fasteners();}\n'
# Exact 10 mm circular turns; polyline sagitta <=0.001 mm, inflated native sphere radius2.57.
a0=math.asin(.26);points=[]
for i in range(81):
 a=a0+(math.pi/2-a0)*i/80;points.append([-11,20.25+10*math.sin(a),25+10*math.cos(a)])
for i in range(1,81):
 a=(math.pi/2)*i/80;points.append([-1-10*math.cos(a),30.25,25-10*math.sin(a)])
points.append([3,30.25,15]);s+='\ntbh09_external_points='+json.dumps(points)+';\n'
s+='''module tbh09_external_leads(){for(y=tbh09_fan_centres,k=[0:160])hull(){translate(tbh09_external_points[k]+[0,y,0])sphere(r=2.57,$fn=32);translate(tbh09_external_points[k+1]+[0,y,0])sphere(r=2.57,$fn=32);}}
module tbh09_tie_head_reservations(){for(y=tbh09_fan_centres)translate([-8,y+27.7,5.1])cube([5.5,5.5,3.4]);}
module tbh09_harness(){tbh08_harness();tbh09_external_leads();}
if(part=="external_pod")intersection(){tbh09_external_leads();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="external_parts")intersection(){tbh09_external_leads();tbh09_lead_parts();}
if(part=="external_fans")intersection(){tbh09_external_leads();tbh09_fans();}
if(part=="external_ties")intersection(){tbh09_external_leads();tbh09_tie_paths();}
if(part=="ties_pod")intersection(){tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="ties_parts")intersection(){tbh09_tie_paths();tbh09_lead_parts();}
if(part=="head_pod")intersection(){tbh09_tie_head_reservations();for(y=tbh09_fan_centres)tbh09_pod(y);}
if(part=="head_parts")intersection(){tbh09_tie_head_reservations();tbh09_lead_parts();}
if(part=="head_leads")intersection(){tbh09_tie_head_reservations();tbh09_external_leads();}
if(part=="external_harness")tbh09_harness();
if(part=="tie_positive")intersection(){translate([1,0,0])tbh09_tie_paths();for(y=tbh09_fan_centres)tbh09_lead_bridge(y);}
'''
(R/'cooling_candidate.scad').write_text(s)
(R/'external-path.json').write_text(json.dumps(dict(turn_radius_mm=10,nominal_bundle_radius_mm=2.5,native_sphere_radius_mm=2.57,local_entry=points[0],local_exit=points[-1],length_mm=10*(math.pi-a0)+4,sagitta_upper_mm=10*(1-math.cos(math.pi/320)),receiving_gap='Actual fan termination to first route datum is not dimensioned by manufacturer; inspect/measure receiving transition.',points=points),indent=2)+'\n')
