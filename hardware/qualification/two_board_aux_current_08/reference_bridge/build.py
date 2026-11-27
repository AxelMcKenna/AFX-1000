"""Author isolated In6 main-return bridge and old-LDO input reference extension."""
import copy,json,uuid,shutil
from pathlib import Path
from shapely.geometry import Polygon
from ..routed.plan import sha,shape
from ..held_cell.preflight import zone_coordinates
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,a
H=Path(__file__).resolve().parent;BASE=H.parent/'distribution/native-01';OUT=H/'authored-01';MAIN='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb';ISLAND='78fadc71-5bdb-5968-8ca8-0e3b4b40722f';GROUP='00b41082-e346-59e4-aee2-f34d9b87e697';POINTS=[[184.5,117.5],[203,117.5],[203,140.5],[184.5,140.5]]
def run():
 c=json.loads((H/'capture-01/capture.json').read_text());assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items());island=next(z for z in c['zones'] if z['uuid']==ISLAND);assert island['net']=='PWR_AGND' and island['layer']=='In6.Cu' and not island['keepout'];g=shape(island['polygons']);contacts=[]
 for o in c['objects']:
  if o['net']=='PWR_AGND' and 'In6.Cu' in o['layers'] and g.intersects(shape(o['layers']['In6.Cu'])):
   assert o['group']==GROUP;contacts.append({'uuid':o['uuid'],'kind':o['kind'],'group':o['group'],'contact_area_mm2':g.intersection(shape(o['layers']['In6.Cu'])).area})
 assert len(contacts)==13 and all(x['contact_area_mm2']>0 for x in contacts)
 q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet=set(q['retained_object_uuids']);quietz={x['zone_uuid'] for x in q['plane_exclusions']};assert ISLAND not in quietz;outline=Polygon(POINTS)
 for o in c['objects']:
  if o['uuid'] in quiet and 'In6.Cu' in o['layers']:assert outline.distance(shape(o['layers']['In6.Cu']))>=.2
 for z in c['zones']:
  if z['uuid'] in quietz and z['layer']=='In6.Cu':assert outline.distance(shape(z['authored_outline']))>=.2
 OUT.mkdir();tree=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());zone=copy.deepcopy(next(z for z in children(tree,'zone') if first(z,'uuid')[1]==MAIN));uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:HELD-DISTRIBUTION:In6-main-bridge-01'));first(zone,'uuid')[1]=uid;first(zone,'priority')[1]=a('2');zone[:]=[x for x in zone if not isinstance(x,list) or x[0] not in ['filled_polygon','polygon']];zone.append([a('polygon'),[a('pts'),*[[a('xy'),a(x),a(y)] for x,y in POINTS]]]);assert zone_coordinates(zone)==[POINTS];tree.append(zone);(OUT/'power_protection.kicad_pcb').write_text(sexpr(tree)+'\n');(H/'plan.json').write_text(json.dumps({'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'authored_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'builder_sha256':sha(Path(__file__)),'capture_sha256':sha(H/'capture-01/capture.json'),'quiet_exclusions_sha256':sha(H.parent/'routed/quiet-exclusion.json'),'new_zone_uuid':uid,'main_source_zone_uuid':MAIN,'other_main_zone_uuid':ISLAND,'main_group_uuid':GROUP,'other_main_zone_contacts':contacts,'outline_mm':POINTS,'new_zone_priority':2,'layer':'In6.Cu','net':'PWR_AGND','expected_original_group_changes':[],'qualified':False},indent=2)+'\n')
if __name__=='__main__':run()
