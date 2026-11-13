"""Bounded buffered-reference joins with native copper/reference screened alternatives."""
import json,hashlib,math
from pathlib import Path
from shapely.geometry import LineString
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r126 as C
R=C.R;routes=[];families=[]
left_detour=[[67.273816,93.328749],[73.059815,93.10884],[74.92998,93.640006]]
for net,anchors,end,direction in [('/A_ADC/REF_HALF_L',[[69.19,94.475],[70.46,94.475]],[74.27,94.475],1),('/A_ADC/REF_HALF_R',[[76.81,89.525],[75.54,89.525]],[71.73,89.525],-1)]:
 paths=[]
 for start in anchors:
  paths+=list(C.S.candidate_paths(start,end));paths +=[[start,[start[0],round(start[1]+direction*d,6)],[end[0],round(start[1]+direction*d,6)],end]for d in [.8,1,1.2,1.4,1.5,1.6,1.8,2,2.5,3,-.8,-1,-1.2,-1.4,-1.5,-1.6,-1.8,-2,-2.5,-3]]
  if net.endswith('_L'):paths.append([start,*left_detour,end])
 legal=[p for p in paths if C.screen.legal(net,'F.Cu',p)];assert legal,net
 p=min(legal,key=lambda p:LineString(p).length);row={'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':p,'role':'buffered half-reference join','trace_length_mm':LineString(p).length};routes.append(row);C.screen.added.append((net,'F.Cu',LineString(p)));families.append({'net':net,'tested_paths':len(paths),'legal_paths':len(legal),'selected_length_mm':LineString(p).length});print(row,flush=True)
paths=[Path(__file__),R/'adc_context_r126.py',R/'capture-r125/capture.json',R/'transitions-r125.json',R/'visibility_path.py',R.parents[3]/'hardware/electronics/adc_driver/revision2/README.md'];out={'planning_only':True,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'routes':routes,'bounded_family':families,'original_copper_and_poses_unchanged':True,'new_vias':[],'analog_qualified':False};p=R/'adc-surface-r130.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
