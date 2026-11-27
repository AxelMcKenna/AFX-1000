"""Phase-recorded selected-zone diagnostic, with all other board objects present."""
import hashlib,json,sys,time,uuid
from pathlib import Path
import pcbnew
SRC=Path(sys.argv[1]);OUT=Path(sys.argv[2]);start=time.monotonic();events=[]
def phase(name,**kwargs):
 events.append({'phase':name,'elapsed_seconds':time.monotonic()-start,**kwargs});(OUT/'phases.json').write_text(json.dumps(events,indent=2)+'\n');print(name,flush=True)
phase('load_started',source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest());b=pcbnew.LoadBoard(str(SRC));assert b is not None;phase('load_completed',zone_count=len(b.Zones()));assert b.BuildConnectivity();phase('connectivity_completed')
uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:LDO-LOCAL-DIRECT:In1-return-01'));zs=[z for z in b.Zones() if z.m_Uuid.AsString()==uid];assert len(zs)==1;selection=pcbnew.ZONES();selection.append(zs[0]);filler=pcbnew.ZONE_FILLER(b);phase('selected_fill_started',zone_uuid=uid);assert filler.Fill(selection);phase('selected_fill_completed');pcbnew.SaveBoard(str(OUT/'selected-fill.kicad_pcb'),b);phase('save_completed',output_sha256=hashlib.sha256((OUT/'selected-fill.kicad_pcb').read_bytes()).hexdigest())
