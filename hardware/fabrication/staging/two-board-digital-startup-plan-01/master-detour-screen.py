import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_nf_surface import Screen,shape
import hardware.fabrication.route_nf_surface as routing
from shapely.geometry import LineString,Point
f=json.loads(Path('/private/tmp/digital-startup-fanout-v6.json').read_text())
retired=['6f316004-0ce1-5238-a3c4-b787448cdb09','e18c12dd-782b-54b8-9d85-f7347eb2a164'];f['retired_objects']=sorted(set(f['retired_objects']+retired))
r=dict(net='/E_rail_disconnect/E28_MASTER_ENABLE',layer='B.Cu',width_mm=.2,path_mm=[[139.5,113],[139.5,112.5],[132.25,112.5],[132.25,117.45]],label='U29 master-enable top detour')
c=json.loads((STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json').read_text());c['objects']=[o for o in c['objects'] if o['uuid'] not in f['retired_objects']];c['zones']=[]
routing.SIGNAL_LAYERS=('F.Cu','B.Cu');screen=Screen(c)
assert screen.legal(r['net'],r['layer'],r['path_mm'])
for v in f['vias']+f['extra_quiet_vias']+[dict(net='PWR_AGND',position_mm=f['relocated_star']['position_mm'])]:
 if v['net']!=r['net']:assert LineString(r['path_mm']).distance(Point(v['position_mm']))>.61
for q in f['routes']+f['fixed_routes']:
 if q['layer']==r['layer'] and q['net']!=r['net']:assert LineString(r['path_mm']).distance(LineString(q['path_mm']))>.41
f['fixed_routes'].append(r)
Path('/private/tmp/digital-startup-fanout.json').write_text(json.dumps(f,indent=2))
print('Master-enable detour passes captured copper screen')
