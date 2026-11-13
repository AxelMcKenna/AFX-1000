"""One bounded NBIAS_L join with an adjacent LINK_AGND reference extension."""
import copy,json,hashlib,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a,children,first
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3];source=R/'native-r131/signal_main.kicad_pcb';t=read_sexpr(source.read_text());c=json.loads((R/'capture-r131/capture.json').read_text())
path=[[67.525,78.5],[65.325,77.5]];net='/A_ADC/NBIAS_L';g=LineString(path).buffer(.6,quad_segs=8);uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-NBIAS-r139-'+name))
anchors=[next(o for o in c['objects']if o['net']==net and o['kind']=='PAD'and o['position_mm']==p)for p in path];assert anchors[0]['group']!=anchors[1]['group']
for z in c['zones']:
 if z['layer']=='In6.Cu' and z['keepout']:assert not g.intersects(shape(z['polygons'])),z['uuid']
for o in c['objects']:
 if o['net']!='LINK_AGND'and o['layers'].get('In6.Cu'):assert g.distance(shape(o['layers']['In6.Cu']))>.2,o['uuid']
t.append([a('segment'),[a('start'),*path[0]],[a('end'),*path[1]],[a('width'),.2],[a('layer'),'B.Cu'],[a('net'),net],[a('uuid'),uid('track')]])
proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='9e84fa37-ceee-58af-b72b-75e51945fe6a');z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];first(z,'uuid')[1]=uid('zone');first(z,'priority')[1]=13000;boundary=[[round(x,6),round(y,6)]for x,y in list(g.exterior.coords)[:-1]];z.append([a('polygon'),[a('pts'),*[[a('xy'),*p]for p in boundary]]]);t.append(z)
row={'net':net,'layer':'B.Cu','path_mm':path,'width_mm':.2,'role':'NBIAS_L surface join','trace_length_mm':LineString(path).length,'before_group_pair':[o['group']for o in anchors],'anchor_pad_uuids':[o['uuid']for o in anchors]}
r={'routes':[row],'vias':[],'transitions':[],'declared_removed':[],'expected_opens':163,'new_reference_zones':[{'uuid':uid('zone'),'layer':'In6.Cu','net':'LINK_AGND','boundary_mm':boundary,'prototype_uuid':first(proto,'uuid')[1]}],'all_existing_authored_objects_unchanged':True,'analog_qualified':False,'physical_qualified':False,'candidate_not_selected':True,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),source,R/'capture-r131/capture.json',R/'native-r131/signal_main.kicad_dru',REPO/'hardware/electronics/adc_driver/revision2/README.md']}}
o=R/'candidate-r139';o.mkdir();(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'signal_main.kicad_dru').write_bytes((R/'native-r131/signal_main.kicad_dru').read_bytes());(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('One NBIAS_L surface join and bounded In6 ground patch; native/reference proof pending')
