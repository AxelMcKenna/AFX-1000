"""Route the digital regulator source to eFuse inputs and bypass banks.

Current/thermal and complete eFuse local layout qualification remain separate.
"""
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape

BASE=STAGING/'two-board-power-regulator-distribution-native-04'
CAP=STAGING/'two-board-power-routing-inputs-2369-regulator-distribution-04/capture.json'
PLAN=REPO/'hardware/fabrication/digital_distribution_plan_01.json'
OUT=STAGING/'two-board-power-digital-distribution-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text()); plan=json.loads(PLAN.read_text())
    for p,h in cap['source_sha256'].items():assert sha(REPO/p)==h,p
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGDIST01:'+sha(CAP)+':'+label))
    pad=lambda r,p:next(o for o in cap['objects'] if o.get('ref')==r and o.get('pin')==p)
    supply='PWR_5V_DIG_SRC'; ground='PWR_AGND'
    wanted={supply:{pad('P_L20','2')['group']},ground:{pad('P_C103','2')['group']}}
    for i,r in enumerate(plan['routes']):
        o=pad(r['ref'],r['pin']);assert r['net']==o['net'] and r['path_mm'][0]==o['position_mm']
        wanted[r['net']].add(o['group']);r['segment_uuids']=[]
        for j,(p,q) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
            u=uid(f'track-{i}-{j}');r['segment_uuids'].append(u)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),r['width_mm']],
                          [a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
    for i,v in enumerate(plan['vias']):
        u=uid('via-'+str(i));v['uuid']=u
        board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),.6],[a('drill'),.3],
                      [a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),u]])
    regions=[('source-distribution',supply,'In6.Cu',unary_union([box(125.5,110,177.2,123),box(130,121,153,133.5)])),
             ('source-adjacent-return',ground,'In5.Cu',box(125,109.4,178,134)),
             ('eFuse-local-reference',ground,'In1.Cu',box(125,109.4,154,134))]
    zones=[]
    for label,net,layer,g in regions:
        g=g.intersection(shape(cap['outline']).buffer(-.51,join_style=2));excluded=[]
        for o in cap['objects']:
            if o.get('npth'):g=g.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
            if o['net']==net and o.get('group') not in wanted[net] and o['layers'].get(layer):
                h=shape(o['layers'][layer]).buffer(.21)
                if g.intersects(h):g=g.difference(h);excluded.append(o['uuid'])
        for z in cap['zones']:
            if z['layer']==layer and z['net']!=net:g=g.difference(shape(z['authored_outline']).buffer(.21,join_style=2))
        g=g.simplify(.00001,preserve_topology=True);assert g.is_valid and g.geom_type=='Polygon'
        u=uid(label);rings=[g.exterior,*g.interiors]
        polygons=[[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in r.coords[:-1]]]] for r in rings]
        board.append([a('zone'),[a('net'),codes[net]],[a('net_name'),net],[a('layer'),layer],[a('uuid'),u],
                      [a('priority'),1 if net==ground else 0],[a('hatch'),a('edge'),.5],
                      [a('connect_pads'),a('yes'),[a('clearance'),.2]],[a('min_thickness'),.25],
                      [a('filled_areas_thickness'),a('no')],[a('fill'),a('yes'),[a('thermal_gap'),.25],
                       [a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],*polygons])
        zones.append(dict(label=label,uuid=u,net=net,layer=layer,priority=1 if net==ground else 0,
                          outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(r.coords)[:-1] for r in g.interiors],
                          excluded_same_net_objects=excluded))
    changed={z['uuid'] for z in cap['zones'] if z['uuid'] in [
        '2d29f18e-f863-557a-bd84-b2d1a216144c','a94125f8-f63e-5d6b-a427-21dcfd31e312',
        '787e0385-5c4c-5b8f-9a2a-017054f7da0e','1893ea20-0fe1-5364-8239-d1853c450ce0']}
    for z in children(board,'zone'):
        if str(first(z,'uuid')[1]) in changed:z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    OUT.mkdir();sources=[]
    for p in BASE.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(BASE)
        if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (p.suffix=='.kicad_sch' or p.name in [
            'power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru',
            'fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
            q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);sources.append(p)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';sch=read_sexpr(p.read_text());first(first(sch,'title_block'),'rev')[1]='TBP37';p.write_text(sexpr(sch)+'\n')
    sources=[Path(__file__),CAP,PLAN,REPO/'hardware/fabrication/plan_two_board_digital_distribution.py',*sources]
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},routes=plan['routes'],vias=plan['vias'],
                new_zones=zones,refilled_existing_zones=sorted(changed),intended_previous_groups={n:sorted(g) for n,g in wanted.items()},
                added_tracks=sum(len(r['segment_uuids']) for r in plan['routes']),added_vias=len(plan['vias']),
                moved_footprints=[],circuit_changes=[],native_validation_pending=True,
                current_thermal_and_complete_return_qualification=False,fabrication_released=False)
    (OUT/'digital-distribution-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['added_tracks','added_vias']}))

if __name__=='__main__':run()
