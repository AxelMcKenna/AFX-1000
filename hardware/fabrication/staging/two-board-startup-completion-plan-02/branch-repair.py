import sys,json,copy,shutil
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),'/private/tmp']
s=Path('/private/tmp/plan_startup_completion_routes_v5.py').read_text();exec(s[:s.index('# Restore every')])
from hardware.fabrication.integrate_two_board_signal import REPO,sha
plan=json.loads((STAGING/'two-board-startup-completion-plan-01/plan.json').read_text())
retire_more={'56de9fc8-c0ab-533a-b77b-ce9173f82890','7ce905ff-c9cd-5579-b692-710f396ee77e','ba021f32-8b61-59fe-a8b2-8909faae1892','d7003052-2fc4-5192-b0b1-3d3c6eda4999'}
# The new bridge is outside both retired bottom tracks, so retaining their
# collision geometry in this screen is conservative. Same-net copper is legal.
for r in plan['routes']:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in plan['extra_vias']:
 for layer in c['copper_layers']:screen.added.append((v['net'],layer,Point(v['position_mm']).buffer(.2)))
net=pads['E_U29','5']['net'];start=[124.5,133.0];end=[130.5,149.0]
# Reference-projection guards for the deliberately retired branch are omitted.
from shapely.ops import unary_union
screen.geometry['In6.Cu']=[(n,g,d) for n,g,d in screen.geometry['In6.Cu'] if n is not None or not any(g.intersection(LineString([o['position_mm'],o['end_mm']]).buffer(.101)).area>1e-8 for o in objects if o['uuid'] in retire_more and o['kind']=='PCB_TRACK')]
screen.trees['In6.Cu']=STRtree([g for n,g,d in screen.geometry['In6.Cu']])
path=screen.simple(net,'In6.Cu',start,end,35)
if not path:
 q=screen.grid_path(net,'In6.Cu',start,end,budget=45000);assert q;path=(LineString(q).length,q)
assert screen.legal(net,'In6.Cu',path[1])
plan['routes'].append(dict(net=net,layer='In6.Cu',width_mm=.2,path_mm=path[1],label='Restore both retained master-enable branches'))
plan['retired_objects']=sorted(set(plan['retired_objects'])|retire_more)
for j in plan['joins']:
 if j['label']=='Restore U30 PG1 Schmitt input':j['target_uuid']=pads['E_U40','5']['uuid'];j['target']=['E_U40','5']
 if j['label']=='Restore U34 PG2 Schmitt input':j['target_uuid']=pads['E_U40','2']['uuid'];j['target']=['E_U40','2']
# The recorded In5 extension must cover the new In6 bridge before native fill.
g=shape=__import__('hardware.fabrication.route_nf_surface',fromlist=['shape']).shape
assert LineString(path[1]).buffer(.1).difference(g(plan['reference_regions']['In5.Cu']['polygons'])).area<1e-6
out=STAGING/'two-board-startup-completion-plan-02';assert not out.exists();out.mkdir()
for q in (STAGING/'two-board-startup-completion-plan-01').iterdir():
 if q.name not in ['manifest.json','plan.json','README.md']:shutil.copy2(q,out/q.name)
shutil.copy2(Path(__file__),out/'branch-repair.py')
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
sources=[STAGING/'two-board-startup-completion-plan-01/manifest.json',STAGING/'two-board-power-startup-completion-native-01/review.json',STAGING/'two-board-power-startup-completion-native-01/drc.json',STAGING/'two-board-power-routing-inputs-2294-logic-references-02/capture.json',*out.iterdir()]
(out/'manifest.json').write_text(json.dumps(dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in sources},moves=plan['moves'],planned_interconnects=20,additional_existing_branch_restore=True,expected_closed_connections=24,deferred=plan['deferred'],clearance_rules_unchanged=True,native_validation_pending=True,fabrication_released=False),indent=2)+'\n')
(out/'README.md').write_text((STAGING/'two-board-startup-completion-plan-01/README.md').read_text()+'''\nThe first native candidate retained two now-unused PG transition vias and a\nmaster-enable branch whose chip-pad bridge had moved. This plan retires those\ntwo vias and two old bottom tracks, then reconnects the two retained master\nbranches on In6. PG route endpoint witnesses use the unchanged U40 pads. The\ninitial four dangling-copper warnings and one missing join require fresh native\nvalidation; they are not waived.\n''')
print('bridge',path,'retired',len(plan['retired_objects']),flush=True)
