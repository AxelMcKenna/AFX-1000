import json,hashlib
from pathlib import Path
import pcbnew
R=Path(__file__).parent;p=R/'follow2-only/rail_disconnect.kicad_pcb';before=hashlib.sha256(p.read_bytes()).hexdigest();b=pcbnew.LoadBoard(str(p));b.BuildConnectivity();c=b.GetConnectivity();c.RecalculateRatsnest();ps=[p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip('/')=='E28_ANA_FOLLOW2'];ids={p.m_Uuid.AsString():p.GetParentFootprint().GetReference()+'.'+p.GetNumber() for p in ps};groups=[]
for p0 in ps:
 connected={p0.m_Uuid.AsString()}|{n.m_Uuid.AsString() for n in c.GetConnectedItems(p0)};row=sorted(v for k,v in ids.items() if k in connected)
 if row not in groups:groups.append(row)
assert len(groups)==1 and len(ps)>=2;assert hashlib.sha256(p.read_bytes()).hexdigest()==before
r=dict(pcb_sha256=before,native_version=pcbnew.GetBuildVersion(),uncapped_opens=c.GetUnconnectedCount(False),FOLLOW2_actual_pad_inventory=sorted(ids.values()),FOLLOW2_actual_native_connected_components=groups,FOLLOW2_closed=True,no_board_written=True,physical_qualified=False)
(R/'follow2-native-connectivity.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
