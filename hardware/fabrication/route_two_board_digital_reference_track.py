"""Keep the third digital eFuse DVDT trace over its own quiet reference."""
import json,shutil,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape,Screen
BASE=STAGING/'two-board-power-digital-reference-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2320-digital-reference-01/capture.json'
ORIGINAL=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
OUT=STAGING/'two-board-power-digital-reference-02'
PATH=[[135.46,122.575],[135.5,123.7],[136.6,125.3],[137.1,125.5],[137.6,125.2],[138.0,124.3],[138.81,123.7625]]


def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text());old=next(r for r in json.loads(ORIGINAL.read_text())['routes'] if r.get('label')=='E_R114.1')
 for name,h in c['source_sha256'].items():assert sha(Path(name) if Path(name).is_absolute() else REPO/name)==h
 assert old['path_mm'][0]==PATH[0] and old['path_mm'][-1]==PATH[-1]
 assert Screen(c).legal(old['net'],'F.Cu',PATH)
 z=next(z for z in c['zones'] if z['uuid']=='f4ced2b6-1129-5f08-9964-81793db22150')
 g=LineString(PATH).buffer(.1);assert g.difference(shape(z['polygons']).buffer(.001)).area<1e-6
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());retired=set(old['segment_uuids'])
 board[:]=[n for n in board if not(isinstance(n,list) and n and n[0]=='segment' and str(first(n,'uuid')[1]) in retired)]
 code=next(int(n[1]) for n in children(board,'net') if str(n[2])==old['net']);ids=[]
 for i,(p,q) in enumerate(zip(PATH,PATH[1:])):
  u=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGREFTRACK01:'+sha(CAP)+':'+str(i)));ids.append(u)
  board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),code],[a('uuid'),u]])
 OUT.mkdir();sources=[]
 for p in BASE.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (p.suffix=='.kicad_sch' or p.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json','digital-reference-routing.json'])):
   dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);sources.append(p)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 r=dict(old,path_mm=PATH,length_mm=LineString(PATH).length,segment_uuids=ids)
 sources=[Path(__file__),CAP,ORIGINAL,REPO/'hardware/fabrication/route_nf_surface.py',*sources]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retired_route=old,replacement_route=r,reference_zone=z['uuid'],reference_uncovered_mm2=g.difference(shape(z['polygons']).buffer(.001)).area,all_zone_edits=[],native_validation_pending=True,full_parasitic_qualification=False,fabrication_released=False)
 (OUT/'digital-reference-track-routing.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(retired_tracks=len(retired),added_tracks=len(ids),length_mm=r['length_mm'])))
if __name__=='__main__':run()
