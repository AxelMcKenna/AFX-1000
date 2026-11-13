"""Author isolated main-ground extension; retain all original filled zones."""
import copy,json,uuid,shutil
from pathlib import Path
from ..routed.plan import sha
from .preflight import zone_coordinates
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,a
H=Path(__file__).resolve().parent;BASE=H.parent/'shared_cutover/native-04';OUT=H/'authored-03'
def run():
 assert not OUT.exists();shutil.copytree(BASE,OUT);tree=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());zone=copy.deepcopy(next(z for z in children(tree,'zone') if first(z,'uuid')[1]=='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb'));uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:HELD-CELL:In6-main-extension-01'));first(zone,'uuid')[1]=uid;first(zone,'priority')[1]=a('2');zone[:]=[x for x in zone if not isinstance(x,list) or x[0] not in ['filled_polygon','polygon']];zone.append([a('polygon'),[a('pts'),*[ [a('xy'),a(str(x)),a(str(y))] for x,y in [(136,158),(158,158),(158,180),(136,180)]]]]);assert zone_coordinates(zone)==[[[136,158],[158,158],[158,180],[136,180]]];tree.append(zone);(OUT/'power_protection.kicad_pcb').write_text(sexpr(tree)+'\n');(H/'plane-plan-03.json').write_text(json.dumps({'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'authored_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'builder_sha256':sha(Path(__file__)),'new_zone_uuid':uid,'main_source_zone_uuid':'4b63f119-2e71-5d61-96f6-8b78a1f5c6cb','outline_mm':[[136,158],[158,158],[158,180],[136,180]],'new_zone_priority':2,'layer':'In6.Cu','net':'PWR_AGND','expected_original_group_changes':[],'qualified':False},indent=2)+'\n')
if __name__=='__main__':run()
