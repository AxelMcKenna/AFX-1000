"""Resolve the native findings without changing component placement."""
import json
from pathlib import Path
ROOT=Path('hardware/fabrication/staging');OUT=ROOT/'two-board-analog-cell-plan-05'
p=json.loads((ROOT/'two-board-analog-cell-plan-04/routes.json').read_text())
# The U31 output shares the old (34.8,132) via and trunk with U14. Preserve
# these objects; only the former remote R100 branch is replaced.
restore={'8a98ed6e-abed-5551-8c60-662a068b4343','99db5e9c-4e5b-5c0b-89f8-e11491e7bd2b'}
c=json.loads((ROOT/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text())
oldvia=next(o for o in c['objects'] if o['kind']=='PCB_VIA' and o['net']=='/E_rail_disconnect/E28_ANA_FOLLOW' and o['position_mm']==[34.8,132.])
restore.add(oldvia['uuid']);assert restore<=set(p['retired_objects'])
p['retired_objects']=sorted(set(p['retired_objects'])-restore)
kept=[];vias=[];removed=[]
for route,via in zip(p['routes'],p['vias']):
 if route['ref']=='E_U13' and route['pin'] in ['7','9']:
  route=dict(route,chip=route['owner'],label='E_U13.'+route['pin']+' same-face fanout',quiet_return=False)
  p['connections'].append(route);removed.append(dict(net=via['net'],position_mm=via['position_mm'],reason='Fanout and support connection both use F.Cu; a through-via is unnecessary.'))
 else:kept.append(route);vias.append(via)
p['routes']=kept;p['vias']=vias
p['preserved_shared_enable_objects']=sorted(restore);p['removed_redundant_vias']=removed
p['scope']='Native-01 findings addressed; requires fresh native fill, DRC, connectivity and ownership/reference validation.'
(OUT/'routes.json').write_text(json.dumps(p,indent=2)+'\n')
pl=json.loads((ROOT/'two-board-analog-cell-plan-04/placement.json').read_text());pl['retired_objects']=p['retired_objects'];pl['scope']='Same native component poses as plan 04; preserve the shared enable backbone and omit two redundant same-face vias.'
(OUT/'placement.json').write_text(json.dumps(pl,indent=2)+'\n')
print(json.dumps(dict(restored_objects=sorted(restore),omitted_vias=len(removed))))
