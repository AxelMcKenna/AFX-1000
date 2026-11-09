import sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_startup_completion_routes_v8.py').read_text();exec(s[:s.index('# Restore every')])
done=json.loads(Path('/private/tmp/startup-completion-routes-v9.json').read_text())
new=copy.deepcopy(done['routes']);extra=copy.deepcopy(done['extra_vias']);joins=copy.deepcopy(done['joins']);deferred=copy.deepcopy(done['deferred'])
for r in new:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in extra:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
 if (v['ref'],v['pin']) not in cellvias:cellvias[v['ref'],v['pin']]=v
source=cellvias['E_U34','7'];o=pads['E_R120','1'];anchors=[t for t in objects if t.get('group')==o['group']]
for t in anchors:
 for layer in ['F.Cu','B.Cu']:
  if not t['layers'].get(layer):continue
  pt=t['position_mm']; print('ANCHOR',t['uuid'],layer,pt,'quiet distance',min(Point(pt).distance(q) for q in qfields),'exits',[(dx,dy) for dx,dy in [(.1,0),(-.1,0),(0,.1),(0,-.1)] if screen.legal(o['net'],layer,[pt,[pt[0]+dx,pt[1]+dy]])],flush=True)
print('SOURCE',source['position_mm'],[(l,inner_free(source,l)) for l in ['In2.Cu','In3.Cu','In6.Cu']],flush=True)
for z in c['zones']:
 if z['uuid'] in qids:print('QUIET',z['layer'],routing.shape(z['authored_outline']).bounds)
