from pathlib import Path
import sys,uuid,json,math
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import coded,named
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
r=Path(__file__).parent;t=coded(read_sexpr((r/'c84-vertical-native.kicad_pcb').read_text()));names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')};ids={'e648649c-d1d8-53f8-ac30-4a58ef1a647f','61a1b572-8749-5852-bb4e-de04d8170d49','657d2fa6-4545-5744-9ea3-80bae1a0a0ff','39fd5070-8a97-5379-bd06-e557bfaecc88'};removed=[]
for n in list(children(t,'segment')):
 if str(first(n,'uuid')[1]) in ids:
  removed.append(dict(uuid=str(first(n,'uuid')[1]),net=names[str(first(n,'net')[1])],source_object=sexpr(n)));t.remove(n)
assert len(removed)==4;rt=Router(t);routes=[]
for aa,bb in [((61.95,52.225),(61.95,51.55)),((61.95,51.55),(62.8,51.6)),((60.975,51.25),(62.8,51.6)),((61.95,52.225),(61.75,53.475))]:
 assert legal_line(rt,'V2V5_AUX',0,aa,bb,.2);rt.path('V2V5_AUX',0,[aa,bb],.2);routes.append(dict(net='V2V5_AUX',layer='F.Cu',width_mm=.2,start=aa,end=bb,length_mm=math.dist(aa,bb)))
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['segment','via'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-C84-only:'+str(i)+sexpr(n))))])
(r/'candidate-paired/rail_disconnect.kicad_pcb').write_text(sexpr(named(t))+'\n');(r/'c84-only-authored-delta.json').write_text(json.dumps(dict(removed=removed,added_routes=routes,C84_pose_local=[62.8,52.4,270,'F'],sourcepad_newroute_length_mm=.675+routes[2]['length_mm'],cap_GND_direct_same_net_existing_annulus=[63.275,53.475],no_new_via=True,not_receiver_closure=True),indent=2)+'\n')
