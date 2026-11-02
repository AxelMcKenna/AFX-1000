"""Screen small moves of two bypass vias to free the adjacent CT escape channels."""
import itertools
import json
import math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.route_nf_surface import shape,sha
from hardware.fabrication.nf_ct_leaf_cleanup import prune_leaf_returns
ROOT=Path(__file__).resolve().parent
VIA_IDS=['0d4222e8-babe-4b09-8f82-e2eecaf37f72','d2790e69-30b9-4c0b-86cb-fd3a942df47c']


def run():
    capture_path=ROOT/'staging/nf-ct-routed-inputs-166/capture.json';c=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));t=read_sexpr(source.read_text())
    c['objects'],pruned=prune_leaf_returns(c);pruned_ids={o['uuid'] for o in pruned}
    vias=[next(o for o in c['objects'] if o['uuid']==uid) for uid in VIA_IDS]
    tracks=[o for o in c['objects'] if o['kind']=='PCB_TRACK' and any(math.dist(v['position_mm'],p)<.00001 for v in vias for p in [o['position_mm'],o['end_mm']])]
    changed_ids=set(VIA_IDS)|{o['uuid'] for o in tracks}
    assert all(o['net']=='/N12_INTVCC' for o in vias+tracks)
    rows={layer:[] for layer in c['copper_layers']}
    for o in c['objects']:
        if o['uuid'] in changed_ids:continue
        for layer,polys in o['layers'].items():rows[layer].append((o,shape(polys)))
    trees={l:STRtree([g for o,g in rs]) for l,rs in rows.items()}
    keepouts=[shape(z['polygons']) for z in c['zones'] if z['keepout'] and z['prohibit_vias']]
    def legal_via(p):
        g=Point(p).buffer(.325,quad_segs=32)
        if any(k.distance(g)<.01 for k in keepouts):return False
        for layer,rs in rows.items():
            for i in trees[layer].query(g.buffer(.21)):
                o,h=rs[int(i)]
                if o['net']!='/N12_INTVCC' and g.distance(h)<.205:return False
                if o['kind']=='PAD' and o.get('drill_mm')==[0.,0.] and h.distance(Point(p))<.255:return False
        return True
    options=[]
    for v in vias:
        if v["uuid"]==VIA_IDS[0]:
            options.append([(0.,tuple(v["position_mm"]))]);continue
        found=[]
        for dx,dy in itertools.product([i/20 for i in range(-12,13)],[i/20 for i in range(3,13)]):
            pt=tuple(round(a+b,6) for a,b in zip(v['position_mm'],(dx,dy)))
            if legal_via(pt):found.append((math.hypot(dx,dy),pt))
        options.append(sorted(found))
        print('Via',v['uuid'],'legal positions',len(found),flush=True)
    choices=[]
    for left,right in itertools.product(*options):
        new=[left[1],right[1]]
        pairs=list(zip([v['position_mm'] for v in vias],new));proposals=[]
        for o in tracks:
            endpoints=[]
            for pt in [o['position_mm'],o['end_mm']]:endpoints.append(next((q for p,q in pairs if math.dist(p,pt)<.00001),pt))
            proposals.append((o,endpoints))
        ok=True
        for o,pts in proposals:
            layer=next(iter(o['layers']));g=LineString(pts)
            if any(rows[layer][int(i)][0]['net']!=o['net'] and g.distance(rows[layer][int(i)][1])<o['width_mm']/2+.205 for i in trees[layer].query(g.buffer(.5))):ok=False;break
        if ok:choices.append((left[0]+right[0],new,proposals))
    assert choices,'No legal narrow via adjustment found'
    _,new,proposals=min(choices,key=lambda row:row[0]);edits={o['uuid']:pts for o,pts in proposals};removed_nodes=[]
    for tag in ['segment','via']:
        for n in list(children(t,tag)):
            uid=first(n,'uuid')[1]
            if uid in pruned_ids:removed_nodes.append(n);t.remove(n);continue
            if uid in edits:
                first(n,'start')[1:3]=edits[uid][0];first(n,'end')[1:3]=edits[uid][1]
            if uid in VIA_IDS:first(n,'at')[1:3]=new[VIA_IDS.index(uid)]
    output=ROOT/'staging/nf-ct-via-clearance-01';output.mkdir(exist_ok=False)
    (output/source.name).write_text(sexpr(t)+'\n')
    inputs=[source,capture_path,Path(__file__),ROOT/'nf_ct_leaf_cleanup.py']
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},via_moves=[dict(uuid=v['uuid'],before=v['position_mm'],after=p) for v,p in zip(vias,new)],
        changed_track_uuids=sorted(edits),removed_leaf_objects=removed_nodes,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Moved vias to',new,'updated',len(edits),'attached tracks; pruned',len(removed_nodes),'reference leaf objects')


if __name__=='__main__':run()
