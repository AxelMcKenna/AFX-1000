"""Bounded diagnostic: fill only manifest-declared AGND zones; not acceptance."""
import hashlib,json,sys,time
from pathlib import Path
import pcbnew
from hardware.qualification.two_board_aux_current_08.ldo_local.immutable_inputs import check_tree
H=Path(sys.argv[1]); OUT=Path(sys.argv[2]); manifest=json.loads((H/'manifest-IN-slot-01.json').read_text()); src=H/manifest['bundle_name']; check_tree(src,manifest)
start=time.monotonic(); events=[]
def phase(name,**kw):
 events.append(dict(phase=name,elapsed_seconds=time.monotonic()-start,**kw)); (OUT/'phases.json').write_text(json.dumps(events,indent=2)+'\n');print(name,flush=True)
phase('load_started'); b=pcbnew.LoadBoard(str(src/'power_protection.kicad_pcb')); assert b is not None; phase('load_completed'); assert b.BuildConnectivity();phase('connectivity_completed')
ids=set(manifest['allowed_AGND_zone_UUIDs']); selected=pcbnew.ZONES(); found=set()
for z in b.Zones():
 if z.m_Uuid.AsString() in ids:
  assert z.GetNetname()=='PWR_AGND';selected.append(z);found.add(z.m_Uuid.AsString())
assert found==ids
filler=pcbnew.ZONE_FILLER(b);phase('fill_started',zone_UUIDs=sorted(ids));assert filler.Fill(selected);phase('fill_completed');pcbnew.SaveBoard(str(OUT/'selected-fill.kicad_pcb'),b);phase('save_completed');check_tree(src,manifest)
