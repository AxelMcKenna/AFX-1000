"""Native negative tests: conductive objects cannot enter the unchanged receiving discs."""
import json,sys,shutil,subprocess,hashlib
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
R=Path(__file__).resolve().parent;O=R/sys.argv[1];B=R/'native-r105';assert O.is_dir()and not list(O.iterdir())
reports=[]
for case in ['track','via','smd_pad','npth_annulus']:
 d=O/case;d.mkdir()
 for name in ['signal_main.kicad_pro','signal_main.kicad_dru']:shutil.copy2(B/name,d/name)
 b=pcbnew.LoadBoard(str(B/'signal_main.kicad_pcb'));net=b.FindNet('LINK_SDA')
 if case=='track':
  o=pcbnew.PCB_TRACK(b);o.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(190.1),pcbnew.FromMM(79.6)));o.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(190.5),pcbnew.FromMM(85.1)));o.SetWidth(pcbnew.FromMM(.2));o.SetLayer(pcbnew.F_Cu);o.SetNet(net);b.Add(o)
 elif case=='via':
  o=pcbnew.PCB_VIA(b);o.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(189.2),pcbnew.FromMM(77.8)));o.SetWidth(pcbnew.FromMM(.6));o.SetDrill(pcbnew.FromMM(.3));o.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);o.SetNet(net);b.Add(o)
 else:
  f=next(f for f in b.GetFootprints()if f.GetReference()=='D_H4');o=next(iter(f.Pads()))
  if case=='smd_pad':o.SetAttribute(pcbnew.PAD_ATTRIB_SMD);o.SetDrillSize(pcbnew.VECTOR2I(0,0));o.SetLayerSet(pcbnew.LSET(pcbnew.F_Cu));o.SetNet(net)
  else:o.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(3),pcbnew.FromMM(3)))
 uid=o.m_Uuid.AsString();p=d/'signal_main.kicad_pcb';pcbnew.SaveBoard(str(p),b)
 proc=subprocess.run(['kicad-cli','pcb','drc','--severity-all','--format','json','-o',str(d/'drc.json'),str(p)],capture_output=True,text=True,timeout=90);(d/'run.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0
 drc=json.loads((d/'drc.json').read_text());hits=[v for v in drc['violations']if v['type']=='items_not_allowed'and any(x['uuid']==uid for x in v['items'])]
 assert hits,(case,drc['violations']);reports.append({'case':case,'mutated_uuid':uid,'caught':hits})
paths=[Path(__file__),B/'signal_main.kicad_pcb',B/'signal_main.kicad_dru',B/'signal_main.kicad_pro'];(O/'review.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'tests':reports},indent=2)+'\n');print('PASS four native rejection tests')
