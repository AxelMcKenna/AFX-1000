import json,hashlib
from pathlib import Path
import pcbnew
R=Path('/private/tmp/afx-e28-p12-layerhop')
p=R/'candidate-paired/rail_disconnect.kicad_pcb';b=pcbnew.LoadBoard(str(p));b.BuildConnectivity();c=b.GetConnectivity();c.RecalculateRatsnest()
nets=['P12_OV_OK','E28_MASTER_ENABLE','P19_OV_OK_SCHMITT','V5_REG_OV_OK_SCHMITT']
rows={}
for name in nets:
 ps=[p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip('/')==name]
 ids={p.m_Uuid.AsString():f'{p.GetParentFootprint().GetReference()}.{p.GetNumber()}' for p in ps}
 comps=[]
 for p0 in ps:
  group={p0.m_Uuid.AsString()}|{x.m_Uuid.AsString() for x in c.GetConnectedItems(p0)}
  group=sorted(v for k,v in ids.items() if k in group)
  if group not in comps:comps.append(group)
 rows[name]=dict(actual_pads=sorted(ids.values()),native_connected_pad_components=comps,all_actual_pads_connected=len(comps)==1)
raw=json.loads((R/'candidate-drc.json').read_text())
report=dict(pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),native_version=pcbnew.GetBuildVersion(),uncapped_unconnected_count=c.GetUnconnectedCount(False),reported_unconnected_count=len(raw['unconnected_items']),targets=rows,method='native BuildConnectivity; RecalculateRatsnest; transitive GetConnectedItems from each actual target pad; GetUnconnectedCount(False)',physical_qualified=False)
(R/'native-connectivity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
