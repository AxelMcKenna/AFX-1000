"""Diagnose a rejected candidate without treating its DRC as passed."""
import json
import pcbnew
from collections import defaultdict
from hardware.fabrication.integrate_two_board_signal import STAGING

def load(name):
 b=pcbnew.LoadBoard(str(STAGING/name/'power_protection.kicad_pcb'));b.BuildConnectivity();c=b.GetConnectivity();c.RecalculateRatsnest();groups={};membership={};pads={}
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.GetNumber() and p.GetNetname():pads[(f.GetReference(),p.GetNumber())]=p
 bynet=defaultdict(set)
 for key,p in pads.items():
  u=p.m_Uuid.AsString()
  if u not in membership:
   g={u}|{v.m_Uuid.AsString() for v in c.GetConnectedItems(p) if v.GetNetname()==p.GetNetname()};gid=min(g);membership.update({v:gid for v in g});groups[gid]=g
  bynet[p.GetNetname()].add(membership[u])
 return b,c,{k:len(v)-1 for k,v in bynet.items()},pads,membership
b0,c0,n0,p0,m0=load('two-board-power-digital-distribution-native-02')
b,c,n,p,m=load('two-board-power-digital-cells-native-01')
print(json.dumps(dict(changed_net_opens={k:[n0[k],v] for k,v in n.items() if n0[k]!=v})))
main=m[p['P_C103','2'].m_Uuid.AsString()]
refs=['E_U15','E_U16','E_U17','E_U33','E_R105','E_R109','E_R113','E_R121','E_C43','E_C45','E_C47','E_C51','E_C44','E_C48','E_C52']
print(json.dumps(dict(disconnected_ground_pins=[list(k) for k,v in p.items() if k[0] in refs and v.GetNetname()=='PWR_AGND' and m[v.m_Uuid.AsString()]!=main])))
