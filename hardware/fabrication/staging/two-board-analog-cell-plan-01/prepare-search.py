import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import STAGING
c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text());old={o['uuid']:o for o in c['objects']}
cells=[['E_U13','E_R97','E_R98','E_C39','E_R96'],['E_U14','E_R101','E_R102','E_C41','E_R100'],['E_U32','E_R117','E_R118','E_C49','E_R116']]
retire=set();branches=[]
for folder,file,labels in [('two-board-power-startup-completion-native-06','startup-completion-routing.json',['E_R96.1 escape','E_R116.1 escape','Analog follower2 pulldown signal','Analog enable pulldown signal hop 1','Analog enable pulldown signal hop 2']),('two-board-power-permission-native-04','permission-routing.json',['E_R100.1 escape','Analog follower pulldown signal hop 1','Analog follower pulldown signal hop 2'])]:
 r=json.loads((STAGING/folder/file).read_text());selected=[x for x in r['routes'] if x.get('label') in labels];assert len(selected)==len(labels)
 for x in selected:retire.update(x['segment_uuids']);branches.append(x)
for xy in [[36.5,109.5],[70.2,125.2],[32.5,139.5],[25.5,141.5],[34.8,132.0]]:
 vs=[o for o in c['objects'] if o['kind']=='PCB_VIA' and o['position_mm']==xy];assert len(vs)==1;retire.add(vs[0]['uuid'])
net='/E_rail_disconnect/E28_ANA_0_DVDT_CAP';os=[o for o in c['objects'] if o['net']==net];assert {(o['ref'],o['pin']) for o in os if o['kind']=='PAD'}=={('E_R98','2'),('E_C39','1')}
retire.update(o['uuid'] for o in os if o['kind']!='PAD')
assert len(retire)==86
Path('/private/tmp/analog-cell-seed.json').write_text(json.dumps(dict(cells=cells,moving=[r for cell in cells for r in cell[1:]],retired_objects=sorted(retire),replaced_enable_branches=branches,restored_preexisting_net=net),indent=2)+'\n')
s=(STAGING/'two-board-digital-cell-plan-01/packing-search.py').read_text()
s=s.replace("BASE=STAGING/'two-board-power-digital-distribution-native-02'","BASE=STAGING/'two-board-power-permission-native-04'")
s=s.replace("c=json.loads((STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json').read_text());prior=json.loads((BASE/'digital-distribution-routing.json').read_text())","c=json.loads((STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json').read_text());seed=json.loads(Path('/private/tmp/analog-cell-seed.json').read_text())")
a=s.index("cells=[('E_U15'");b=s.index('objects=[',a);s=s[:a]+"cells=seed['cells'];moving=set(seed['moving']);retire=set(seed['retired_objects'])\n"+s[b:]
s=s.replace("for flip in ([False] if ref in {'E_C44','E_C48','E_C52'} else [False,True])","for flip in [False]")
a=s.index('# Place the three input caps');b=s.index('updated=dict(fps)',a)
s=s[:a]+'''for ref,ilm,dvdt,capref,pulldown in cells:
 p9=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='9')
 p7=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='7')
 p1=next(o['position_mm'] for o in objects if o.get('ref')==ref and o.get('pin')=='1')
 place(ilm,[p9[0]+2.5,p9[1]-1],p9)
 os=place(dvdt,[p7[0]+2.5,p7[1]+1],p7)
 p2=next(o['position_mm'] for o in os if o['pin']=='2');place(capref,p2,p2)
 place(pulldown,[p1[0]-2.5,p1[1]-1],p1)
'''+s[b:]
s=s.replace("Path('/private/tmp/digital-cell-placement.json')","Path('/private/tmp/analog-cell-placement-v1.json')")
Path('/private/tmp/pack_analog_cells_v1.py').write_text(s)
print('Prepared 12-part analog support packing with 86 obsolete branch objects to replace.')
