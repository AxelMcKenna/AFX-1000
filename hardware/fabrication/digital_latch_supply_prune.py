"""Remove obsolete latch and pull-up supply tails after the series-resistor move."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent
NETS={'/LED/LATCH_5V','V3V3_IO'}
def prune(c,eligible):
 geometry=[]
 for o in c['objects']:
  for layer,ps in o['layers'].items():
   if ps:geometry.append((o['uuid'],o['net'],layer,LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else shape(ps),o['kind']))
 tree=STRtree([g[3] for g in geometry]);removed=set();reasons=[]
 while True:
  changed=False
  for o in c['objects']:
   if o['uuid'] not in eligible or o['uuid'] in removed or o['net'] not in NETS:continue
   if o['kind']=='PCB_TRACK':
    layer=next(iter(o['layers']))
    for p in [o['position_mm'],o['end_mm']]:
     point=Point(p)
     if not any(uid!=o['uuid'] and uid not in removed and net==o['net'] and face==layer and point.distance(g)<=.002 for k in tree.query(point.buffer(.002)) for uid,net,face,g,kind in [geometry[int(k)]]):
      removed.add(o['uuid']);reasons.append(dict(uuid=o['uuid'],net=o['net'],unsupported_endpoint_mm=p));changed=True;break
   elif o['kind']=='PCB_VIA':
    contacts=[]
    for face,ps in o['layers'].items():
     g=shape(ps)
     contacts += [(uid,layer,kind) for k in tree.query(g.buffer(.000002)) for uid,net,layer,h,kind in [geometry[int(k)]] if uid!=o['uuid'] and uid not in removed and net==o['net'] and layer==face and g.distance(h)<=.000002]
    if not any(kind=='PAD' for _,_,kind in contacts) and len({f for _,f,_ in contacts})<2:
     removed.add(o['uuid']);reasons.append(dict(uuid=o['uuid'],net=o['net'],remaining_contact_layers=sorted({f for _,f,_ in contacts})));changed=True
  if not changed:break
 return removed,reasons

def run():
 cp=ROOT/'staging/digital-latch-supply-prune-inputs-42/capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
 pcb=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));drcpath=pcb.parent/'drc.json';drc=json.loads(drcpath.read_text());assert len(drc['violations'])==3 and all(v['type']=='track_dangling' and v['severity']=='warning' for v in drc['violations'])
 parent=ROOT/'staging/digital-blank-pullup-native-01/digital_core.kicad_pcb';base=read_sexpr(parent.read_text());eligible={first(n,'uuid')[1] for tag in ('segment','via') for n in children(base,tag) if first(n,'net')[1] in NETS}
 removed,reasons=prune(c,eligible);assert {i['uuid'] for v in drc['violations'] for i in v['items']}<=removed
 before=read_sexpr(pcb.read_text());board=read_sexpr(pcb.read_text());nodes=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in removed];assert len(nodes)==len(removed)
 for n in nodes:board.remove(n)
 out=ROOT/'staging/digital-latch-supply-clean-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,drcpath,parent,Path(__file__),ROOT/'route_nf_surface.py']
 r=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),removed_objects=nodes,removed_uuids=sorted(removed),reasons=reasons,geometry_delta=geometry_delta(before,board),all_new_reconnection_copper_retained=True,native_checks_pending=True,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(r,indent=2)+'\n');print('Pruned',len(nodes),'obsolete copper objects',[(x[0],first(x,'net')[1]) for x in nodes],flush=True)
if __name__=='__main__':run()
