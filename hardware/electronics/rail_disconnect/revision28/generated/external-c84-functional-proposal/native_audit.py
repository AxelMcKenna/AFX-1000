import json,hashlib
from pathlib import Path
import pcbnew
R=Path(__file__).parent;p=R/'candidate-paired/rail_disconnect.kicad_pcb';b=pcbnew.LoadBoard(str(p));b.BuildConnectivity();c=b.GetConnectivity();c.RecalculateRatsnest();f={f.GetReference():f for f in b.GetFootprints()};allpads=[p for fp in f.values() for p in fp.Pads()];by={(p.GetParentFootprint().GetReference(),p.GetNumber()):p for p in allpads};nets=['ANA_PG1','E28_ANA_FOLLOW2','ANA_SOURCE_OK_SCHMITT','ANA_PG1_SCHMITT','V2V5_AUX'];result={}
for net in nets:
 ps=[p for p in allpads if p.GetNetname().lstrip('/')==net];ids={p.m_Uuid.AsString():p.GetParentFootprint().GetReference()+'.'+p.GetNumber() for p in ps};groups=[]
 for p0 in ps:
  known={p0.m_Uuid.AsString()}|{v.m_Uuid.AsString() for v in c.GetConnectedItems(p0)};group=sorted(v for k,v in ids.items() if k in known)
  if group not in groups:groups.append(group)
 result[net]=dict(actual_pad_count=len(ps),connected_pad_components=groups,closed=len(groups)==1)
pgnd=by['C84','2'];v=next(v for v in b.GetTracks() if v.GetClass()=='PCB_VIA' and v.GetPosition()==pcbnew.VECTOR2I(pcbnew.FromMM(163.275),pcbnew.FromMM(153.475)))
assert pgnd.GetNetname()==v.GetNetname()=='/AGND';assert pgnd.HitTest(v.GetPosition());assert result['V2V5_AUX']['closed']
report=dict(pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),native_version=pcbnew.GetBuildVersion(),uncapped_opens=c.GetUnconnectedCount(False),actual_pad_components=result,C84_GND_existing_via_centre_inside_actual_native_pad=True,C84_GND_via_uuid=v.m_Uuid.AsString(),C84_pose_mm=[pcbnew.ToMM(f['C84'].GetPosition().x)-100,pcbnew.ToMM(f['C84'].GetPosition().y)-100,f['C84'].GetOrientationDegrees()],C84_pads=[dict(pin=p.GetNumber(),net=p.GetNetname(),xy_mm=[pcbnew.ToMM(p.GetPosition().x)-100,pcbnew.ToMM(p.GetPosition().y)-100],world_angle=p.GetOrientationDegrees()) for p in f['C84'].Pads()],no_physical_or_local_impedance_qualification=True)
(R/'native-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('uncapped',report['uncapped_opens'],'C84GND native HitTest',True,'targetcomponents',{n:len(v['connected_pad_components']) for n,v in result.items()})
