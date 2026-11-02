"""Add thermal vias in mask-covered EP copper, outside all solder apertures.

Only the four explicit TLC5947 copper-only spreader pads are exempt from the
ordinary SMD-copper exclusion. Mask/paste openings and every other pad retain
their explicit drill gap. No filled/capped via process is silently assumed.
"""
import json,math,uuid
from pathlib import Path
from shapely.geometry import Point,box
from shapely.strtree import STRtree
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent

def run():
    cp=ROOT/'staging/digital-distribution-inputs-255/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    b=read_sexpr(source.read_text());original,count=sexpr(b),len(b)
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(b,'footprint')}
    copper=[(o,shape(ps)) for o in c['objects'] for l,ps in o['layers'].items() if ps];index=STRtree([g for o,g in copper])
    drills=[(o['position_mm'],max(o['drill_mm'])/2) for o in c['objects'] if o['kind']=='PAD' and any(o['drill_mm'])]
    drills += [(o['position_mm'],.15) for o in c['objects'] if o['kind']=='PCB_VIA']
    rows=[];rejected=[]
    for ref in ['U3001','U3002','U3003','U3004']:
        f=fps[ref];at=first(f,'at');assert len(at)==3 or float(at[3])==0
        assert first(f,'layer')[1]=='F.Cu';cx,cy=map(float,at[1:3])
        ep=next(p for p in children(f,'pad') if p[1]=='33')
        assert list(map(float,first(ep,'size')[1:]))==[5.2,11] and first(ep,'layers')[1:]==['F.Cu']
        assert list(map(float,first(ep,'at')[1:3]))==[0,0] and first(ep,'net')[1]=='AGND'
        apertures=[]
        for p in children(f,'pad'):
            layers=first(p,'layers')[1:]
            if not any(l in layers for l in ['F.Mask','F.Paste']):continue
            assert p[3]=='rect'
            x,y=map(float,first(p,'at')[1:3]);w,h=map(float,first(p,'size')[1:3])
            apertures.append(box(cx+x-w/2,cy+y-h/2,cx+x+w/2,cy+y+h/2))
        assert len(apertures)==37
        for dx in [-1.5,1.5]:
            for dy in [-4.5,-3.,3.,4.5]:
                xy=(cx+dx,cy+dy);point=Point(xy);reason=None
                gap=min(point.distance(g)-.15 for g in apertures)
                if gap<.151:reason='mask or paste opening'
                for i in index.query(point.buffer(.52)):
                    o,g=copper[int(i)]
                    if o.get('ref')==ref and o.get('pin')=='33':continue
                    if o['net']!='AGND' and point.distance(g)<.511:reason='foreign copper'
                    if o['kind']=='PAD' and not any(o['drill_mm']) and point.distance(g)<.301:reason='other SMD copper'
                if any(math.dist(xy,q)<r+.411 for q,r in drills):reason='drill spacing'
                if reason:rejected.append(dict(ref=ref,xy_mm=xy,reason=reason));continue
                ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:thermalvia:{sha(source)}:{ref}:{xy}'))
                b.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],
                    [a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),'AGND'],[a('uuid'),ident]])
                drills.append((xy,.15));rows.append(dict(ref=ref,via_uuid=ident,xy_mm=xy,diameter_mm=.6,drill_mm=.3,
                    hole_edge_to_nearest_package_mask_or_paste_mm=gap,overlaps_mask_covered_EP_copper=True,overlaps_solder_opening=False))
    assert sexpr(b[:count])==original
    assert len(rows)>=16
    out=ROOT/'staging/digital-thermal-vias-01';out.mkdir(exist_ok=False);dest=out/source.name;dest.write_text(sexpr(b)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,Path(__file__),ROOT/'route_nf_surface.py']},candidate_PCB_sha256=sha(dest),thermal_vias=rows,rejected_sites=rejected,
        original_authored_geometry_exact=True,filled_or_capped_process_assumed=False,tenting_explicit=True,
        native_checks_pending=True,thermal_performance_and_mask_registration_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Thermal vias',len(rows),'rejected',len(rejected),flush=True)

if __name__=='__main__':run()
