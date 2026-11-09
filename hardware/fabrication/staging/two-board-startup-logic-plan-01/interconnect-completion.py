from pathlib import Path
import json,inspect,types
s=Path('/private/tmp/plan_startup_interconnects_v2.py').read_text()
prefix=s[:s.index('# Reserve the two fixed')]
exec(prefix)
previous=json.loads(Path('/private/tmp/startup-interconnects-v2.json').read_text())
for v in previous['extra_vias']:
 extra.append(v);cellvias[v['ref'],v['pin']]=v;screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
for r in previous['routes']:new.append(r);screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
func=s[s.index('def connect('):s.index('# Restore both')].replace('budget=18000','budget=120000').replace("layers=('In2.Cu','In3.Cu','In6.Cu')","layers=('In6.Cu','In2.Cu','In3.Cu')")
exec(func)
joins=previous['joins'];deferred=[]
# Widen the path search window without changing the clearance screen.
method=inspect.getsource(routing.Screen.grid_path)
import textwrap
method=textwrap.dedent(method).replace('min(u, v)-50','min(u, v)-100').replace('max(u, v)+50','max(u, v)+100')
ns=dict(routing.__dict__);exec(method,ns);screen.grid_path=types.MethodType(ns['grid_path'],screen)
for key,label in [(('E_U40','1'),'PG0 to Schmitt input'),(('E_U40','6'),'PG2 to Schmitt input')]:
 net=cellvias[key]['net'];link(key,[o for o in objects if o['kind']=='PCB_VIA' and o['net']==net],label)
Path('/private/tmp/startup-interconnects-v3.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2))
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
