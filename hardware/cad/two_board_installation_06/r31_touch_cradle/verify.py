"""Bind conditional cradle evidence without accepting hardware/copper/retention."""
import json,hashlib,re
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(R/'hardware/cad/two_board_print_01/captured.scad').read_text();mounts=json.loads(re.search(r'^mounts = (.*);',s,re.M).group(1));assert next(m for m in mounts if m[0]=='H_NEW5')==['H_NEW5',164.,113.,7.9,2.4]
body=(H/'support.scad').read_text();assert 'touch_cradle_pocket_extension' not in body and 'touch_cradle_fastener' not in body
records={}
for case in ['positive','strap_positive','population','controls','wires','strap_support','raw_pcbs']:
 p=H/'native'/(case+'-r3')/'result.json';v=json.loads(p.read_text())
 for n,h in v['source_sha256'].items():assert sha(R/n)==h,n
 assert not v['runtime_failure']
 if case.endswith('positive'):assert v['mesh']['closed_oriented_boundary'] and v['mesh']['degenerate_triangles_excluded']==0 and mesh(p.parent/(case+'.stl'))==v['mesh'];status='CLOSED_POSITIVE'
 elif case=='raw_pcbs':
  m=v['mesh'];assert mesh(p.parent/'raw_pcbs.stl')==m and m['volume_mm3']<1e-9 and m['min_mm'][2]==m['max_mm'][2]==9.5;status='RAW_ZERO_VOLUME_SEAT_PLANE_NOT_SOLID_PASS'
 else:assert v['empty'] and not list(p.parent.glob('*.stl'));status='EMPTY'
 records[case]={'status':status,'result_sha256':sha(p),'artifacts':{str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']}}
r={'status':'UNSELECTED_CRADLE_RECEIVING_STUDY','mount_id':'H_NEW5','mount_xy_mm':[164,113],'board_top_mm':9.5,'original_head_reservation_mm':{'diameter':4.5,'z':[9.5,12.]},'original_nut_pocket_mm':{'AF':4.2,'z':[-.1,1.8]},'pocket_revision_selected':False,'replacement_hardware_selected':False,'copper_keepout_qualified':False,'retention_qualified':False,'release_access_qualified':False,'full_assembly_checked':False,'completed_touch_wires':0,'completed_panel_edges':0,'native':records,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'support.scad',H.parent/'r29_touch_inline/route-draft.scad',R/'hardware/cad/two_board_print_01/captured.scad',R/'hardware/cad/two_board_print_01/housing.scad']}}
(H/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
