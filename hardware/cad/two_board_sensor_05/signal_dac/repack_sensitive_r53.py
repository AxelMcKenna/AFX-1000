"""Move the unrouted R308 and transport its source-derived sensitive-pad exclusion."""
import json,copy,uuid,hashlib
from pathlib import Path
from shapely.affinity import translate
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;source=R/'native-r50/signal_main.kicad_pcb';capture=R/'capture-r50/capture.json';c=json.loads(capture.read_text());t=read_sexpr(source.read_text())
pads=[o for o in c['objects']if o.get('ref')=='A_R308'];assert len(pads)==2
for pad in pads:assert c['all_groups'][pad['group']]==[pad['uuid']]
f=next(f for f in children(t,'footprint')if any(v[1]=='Reference'and v[2]=='A_R308'for v in children(f,'property')));assert list(map(float,first(f,'at')[1:3]))==[116,68]and first(f,'layer')[1]=='F.Cu';first(f,'at')[1:3]=[120.5,81]
move={'reference':'A_R308','uuid':first(f,'uuid')[1],'before_mm':[116,68],'after_mm':[120.5,81],'side':'F.Cu','footprint':f[1]}
pad=next(p for p in pads if p['pin']=='2');assert pad['net']==next(o['net']for o in c['objects']if o.get('ref')=='A_U304'and o.get('pin')=='2')=='/A_DAC/RX_NEG_L'
geom=translate(shape(pad['layers']['F.Cu']),4.5,13).buffer(.5);assert not geom.interiors
# Foreign front copper cannot be deprived of its original reference by this new pad opening.
foreign=[o['uuid']for o in c['objects']if o['net']not in ['LINK_AGND',pad['net']]and o.get('ref')!='A_R308'and o['layers'].get('F.Cu')and geom.intersection(shape(o['layers']['F.Cu'])).area>1e-6];assert not foreign,foreign
proto=next(z for z in children(t,'zone')if children(z,'keepout')and first(first(z,'keepout'),'tracks')[1]=='allowed'and children(z,'layers')and first(z,'layers')[1:]==['In1.Cu','In2.Cu'])
z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];zone_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-dac-r53-moved-R308-sensitive-pad'));first(z,'uuid')[1]=zone_id;outline=[[round(x,6),round(y,6)]for x,y in list(geom.exterior.coords)[:-1]];z.append([a('polygon'),[a('pts'),*[[a('xy'),*p]for p in outline]]]);t.append(z)
contract={'reference':'A_R308','footprint_uuid':move['uuid'],'pad_uuid':pad['uuid'],'pin':'2','net':pad['net'],'before_pad_mm':pad['position_mm'],'after_pad_mm':[121.4125,81],'translation_mm':[4.5,13],'pad_layer':'F.Cu','excluded_layers':['In1.Cu','In2.Cu'],'buffer_mm':.5,'zone_uuid':zone_id,'authored_outline_mm':outline,'source_rule':'hardware/fabrication/audio_main_ground.py:58-72','scope':'transported sensitive pad only; no new route-wide exclusion','foreign_front_copper_intersections':foreign}
r={'expected_opens':194,'moves':[move],'supplemental_lowcap_exclusions':[contract],'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),source,capture,R.parents[3]/'hardware/fabrication/audio_main_ground.py']}}
out=R/'candidate-r53';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('Moved R308; added source-rule pad opening',geom.area)
