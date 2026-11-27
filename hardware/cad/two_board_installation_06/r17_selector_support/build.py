from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
source=P.parent/'r15_right_ground/right-routes.json'
v=json.loads(source.read_text());pts=next(e for e in v['edges'] if e['id']=='R13')['points_mm']
a=[p for p in pts if 52.5<=p[1]<=55.95];b=[p for p in pts if 51.4<=p[1]<=57.2]
s='// Generated from frozen R13 points; do not hand edit.\n'
s+='release_guide_outer_points='+json.dumps(a)+';\nrelease_guide_bore_points='+json.dumps(b)+';\n'
(P/'curve.scad').write_text(s)
(P/'curve-source.json').write_text(json.dumps({'source':str(source.relative_to(P.parents[3])),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'edge':'R13','receiving_wire_radius_mm':.6,'guide_bore_radius_mm':.85},indent=2)+'\n')
