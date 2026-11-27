"""Conditional JST XH body receiving and exact six-wire entry masks; no route edits."""
import argparse,json,hashlib,math,re
import numpy as np
from pathlib import Path
from hardware.electronics.common import sexpr as sx
from hardware.fabrication import assembly_layout
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True);a=p.parse_args();tree,_=assembly_layout.outline(a.pcb)
 manifest=B/'r7/interface-manifest.json';catalog=R/'hardware/cad/a12/enclosure_growth/front_bay_receiving/sources/jst-eXH-official-US.pdf';terminal=B/'r8/terminal-routes.json'
 expected={x['reference']:x for x in json.loads(manifest.read_text())['interfaces'] if x['reference'] in ['F_J202','F_J203']};rows=[]
 for fp in sx.children(tree,'footprint'):
  props={str(x[1]):str(x[2]) for x in sx.children(fp,'property')};ref=props.get('Reference')
  if ref not in expected:continue
  e=expected[ref];assert props['Value']==e['value'];assert 'JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical' in str(fp[1]);at=sx.first(fp,'at');x,y=map(float,at[1:3]);angle=float(at[3]) if len(at)>3 else 0;assert sx.first(fp,'layer')[1]=='F.Cu'
  pads=[]
  for pad in sx.children(fp,'pad'):
   pin=str(pad[1]);local=sx.first(pad,'at');px,py=map(float,local[1:3]);c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle));xy=[x+px*c+py*s,y-px*s+py*c];net=str(sx.first(pad,'net')[-1]);q=next(q for q in e['pads'] if q['pin']==pin);assert math.dist(xy,q['xy'])<1e-8 and net==q['net'];assert pad[2]=='thru_hole'
   pads.append(dict(pin=pin,xy_mm=xy,net=net,drill_mm=float(sx.first(pad,'drill')[1])))
  assert len(pads)==3;old=e['installed_box'];receiving=old[:5]+[20.0]
  rows.append(dict(ref=ref,value=props['Value'],footprint=str(fp[1]),pose=[x,y,angle,'F.Cu'],pads=sorted(pads,key=lambda q:int(q['pin'])),captured_box=old,conditional_receiving_box=receiving))
 assert len(rows)==2
 paths=json.loads(terminal.read_text())['rows'];assert len(paths)==6
 for e in rows:
  for p in e['pads']:
   t=next(q for q in paths if q['ref']==e['ref'] and str(q['pin'])==p['pin']);assert t['control_points'][-1]==p['xy_mm']+[22.3]
 sources=[R/'hardware/cad/a12/enclosure_growth/front_bay_receiving/xh_reference_variant/contract.json',B/'r7/fan_harness.scad',B/'r7/route-pair-search.json',B/'r8/terminal-search.json',Path(__file__),manifest,catalog,terminal,B/'r8/terminal_harness.scad',B/'r9/cooling_candidate.scad']
 boardpath='hardware/'+str(a.pcb).split('hardware/',1)[1]
 contract=dict(source_sha256={str(f.relative_to(R)):sha(f) for f in sources},native_pcb=dict(path=boardpath,sha256=sha(a.pcb)),headers=rows,primary=dict(url='https://www.jst.com/wp-content/uploads/2025/06/eXH.pdf',reviewed_pages=[1,2,4,5],assembled_height_reference_mm=9.8,header_reference_mm=[9.9,5.75,7.0],housing_reference_mm=[9.8,5.7,7.5],body_maximum_or_tolerances_available=False,individual_2d_download_attempt='Manufacturer links returned product page; direct HTTP403. No controlled assembled maximum obtained.'),receiving_contract=dict(pcb_top_z_mm=9.5,max_projection_mm=10.5,max_world_z_mm=20.0,origin='Project receiving cap, consistent with previous front-bay XH receiving contract; NOT a manufacturer maximum',xy='Preserve complete captured XY allocation; no lateral reduction',mask_radius_mm=.98,mask_z_mm=[18.3,20.00001],mask_scope='Only six straight own-wire entry columns at exact retained pad coordinates; wire end hemispheres reach18.33. No masking of curved routing or foreign connector interactions.'),conditional_only=True,dimensionally_qualified=False,route_changed=False,fabrication_released=False)
 # Retain an exact prefix of the existing160-segment polyline through the first
 # grid station at/after each frozen fanout start. This is a union subset.
 curvefile=B/'r7/route-pair-search.json';bases=json.loads(curvefile.read_text())['control_points'];starts=json.loads((B/'r8/terminal-search.json').read_text());transition=[];trim=['use <../r8/terminal_harness.scad>']
 bern=lambda n,t:np.array([[math.comb(n,k)*u**k*(1-u)**(n-k) for k in range(n+1)] for u in t])
 for i,(ref,base) in enumerate(bases.items()):
  cp=np.array(base);t=starts[ref]['start'];stop=math.ceil(160*t);pts=bern(5,np.linspace(0,1,161))@cp;center=(bern(5,[t])@cp)[0];tangent=(bern(4,[t])@(5*np.diff(cp,axis=0)))[0];tangent/=np.linalg.norm(tangent)
  assert pts.tolist()==json.loads(re.search('tbh06_points_'+str(i)+r'=(\[.*?\]);',(B/'r7/fan_harness.scad').read_text()).group(1)), 'Original emitted segment/cap stations changed'
  sag=float(np.linalg.norm(20*np.diff(cp,n=2,axis=0),axis=1).max()/(8*160**2));strands=[]
  for q in [q for q in paths if q['ref']==ref]:
   wirecp=np.array(q['control_points']);pack=wirecp[0]-center;assert abs(pack@tangent)<1e-7;v=wirecp[1]-wirecp[0];v/=np.linalg.norm(v);dot=float(v@tangent);assert dot>1-1e-8
   reserve=2.56*math.cos(math.pi/24)**2-np.linalg.norm(pack)-.97-sag;assert reserve>0
   strands.append(dict(pin=q['pin'],start_mm=wirecp[0].tolist(),packing_offset_mm=pack.tolist(),tangent_dot=dot,complete_start_sphere_containment_margin_mm=float(reserve)))
  transition.append(dict(ref=ref,fanout_start_parameter=t,retained_original_segment_count=stop,retained_last_station=stop/160,centerline_chord_sag_bound_mm=sag,strands=strands,proof='Each translated prefix and complete start sphere fits inside original bundle sweep; endpoint derivative is parallel. Retain original segments through ceil(160*t), so ownership overlaps with no bridge gap.'))
  trim.append('module fan_prefix_'+str(i)+'(){'+''.join('hull(){translate('+json.dumps(a.tolist())+')sphere(r=2.56,$fn=24);translate('+json.dumps(b.tolist())+')sphere(r=2.56,$fn=24);}' for a,b in zip(pts[:stop],pts[1:stop+1]))+'}')
 trim.append('module retained_fan_bundle(){fan_prefix_0();fan_prefix_1();}')
 trim.append('module reconciled_fan_harness(){retained_fan_bundle();tbh08_terminal_wires();}')
 trim.append('module fanout_start_spheres(){'+''.join('translate('+json.dumps(q['start_mm'])+')sphere(r=.97,$fn=32);' for x in transition for q in x['strands'])+'}')
 (H/'harness.scad').write_text('\n'.join(trim)+'\n');contract['fanout_transition']=transition;contract['route_changed']=False;contract['redundant_bundle_proxy_trimmed']=True
 (H/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 sc=['// Project receiving cap; manufacturer only provides reference assembly height.','module fan_box(b){translate([b[0],b[1],b[2]])cube([b[3]-b[0],b[4]-b[1],b[5]-b[2]]);}']
 for name,key in [('captured_fan_connectors','captured_box'),('conditional_fan_connectors','conditional_receiving_box')]:sc.append('module '+name+'(){'+''.join('fan_box('+json.dumps(e[key])+');' for e in rows)+'}')
 sc.append('module fan_entry_masks(){'+''.join('translate('+json.dumps(p['xy_mm']+[18.3])+')cylinder(r=.98,h=1.70001,$fn=64);' for e in rows for p in e['pads'])+'}')
 (H/'mates.scad').write_text('\n'.join(sc)+'\n');print('2 exact native XH identities;6 entry columns;conditional20mm cap;no route change')
if __name__=='__main__':main()
