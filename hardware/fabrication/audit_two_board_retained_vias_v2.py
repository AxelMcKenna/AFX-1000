"""Recheck multiple generations of control vias against full successor geometry."""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    ap=argparse.ArgumentParser()
    for k in ['source','capture']:ap.add_argument('--'+k,required=True)
    ap.add_argument('--via-source',action='append',required=True)
    args=ap.parse_args();out=STAGING/args.source
    cp=STAGING/args.capture/'capture.json';rps=[STAGING/n/'via-routing.json' for n in args.via_source]
    cap=json.loads(cp.read_text());records=[json.loads(rp.read_text()) for rp in rps]
    for data in [cap,*records]:
        for p,h in data['source_sha256'].items():assert sha(REPO/p)==h,p
    assert cap['source_sha256'][str(out/'power_protection.kicad_pcb')]==sha(out/'power_protection.kicad_pcb')
    objects={o['uuid']:o for o in cap['objects']};smd=[];drills=[];copper=[]
    def shape(polys):return unary_union([Polygon(p['outer'],p['holes']) for p in polys])
    outline=shape(cap['outline'])
    for uid,o in objects.items():
        for layer,polys in o['layers'].items():
            if not polys:continue
            g=shape(polys);copper.append((uid,o['net'],layer,g))
            if o['kind']=='PAD' and not any(o['drill_mm']) and layer in ['F.Cu','B.Cu']:smd.append((uid,g))
        d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
        if radius:drills.append((uid,o['position_mm'],radius))
    rows=[]
    vias=[v for record in records for r in record['routes'] for v in r.get('vias',[r['via']] if r.get('via') else [])]
    assert len({v['uuid'] for v in vias})==len(vias)
    for v in vias:
        o=objects[v['uuid']];pt=Point(o['position_mm'])
        assert o['kind']=='PCB_VIA' and o['net']==v['net'] and math.dist(o['position_mm'],v['position_mm'])<2e-6
        assert o['width_mm']==.6 and o['drill_mm']==.3 and o['via_type']==4 and o['span']==['F.Cu','B.Cu']
        smd_gap=min((pt.distance(g)-.3,u) for u,g in smd)
        hole_gap=min((math.dist(o['position_mm'],p)-.15-radius,u) for u,p,radius in drills if u!=v['uuid'])
        copper_gap=min((pt.distance(g)-.3,u,layer) for u,net,layer,g in copper if net!=o['net'])
        edge_gap=pt.distance(outline.boundary)-.3
        assert outline.contains(pt) and edge_gap>=.5
        assert smd_gap[0]>=.01-2e-6 and hole_gap[0]>=.26-2e-6 and copper_gap[0]>=.21-2e-6
        rows.append(dict(uuid=v['uuid'],net=o['net'],copper_to_SMD_mm=smd_gap[0],nearest_SMD_uuid=smd_gap[1],
            drill_to_SMD_mm=smd_gap[0]+.15,hole_to_hole_mm=hole_gap[0],nearest_hole_uuid=hole_gap[1],
            copper_to_foreign_copper_mm=copper_gap[0],nearest_foreign_uuid=copper_gap[1],nearest_foreign_layer=copper_gap[2],
            copper_to_board_edge_mm=edge_gap))
    assert len(rows)==sum(record['added_vias'] for record in records)
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),cp,*rps,out/'additive-audit.json']},
        vias_checked=len(rows),all_copper_layers_checked=True,same_net_SMDs_and_drills_checked=True,
        minimum_drill_to_SMD_mm=min(r['drill_to_SMD_mm'] for r in rows),
        minimum_hole_to_hole_mm=min(r['hole_to_hole_mm'] for r in rows),
        minimum_copper_to_foreign_copper_mm=min(r['copper_to_foreign_copper_mm'] for r in rows),
        minimum_copper_to_edge_mm=min(r['copper_to_board_edge_mm'] for r in rows),evidence=rows,
        physical_stack_or_assembly_qualified=False,fabrication_released=False)
    with (out/'retained-via-clearance.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','evidence']},indent=2))


if __name__=='__main__':run()
