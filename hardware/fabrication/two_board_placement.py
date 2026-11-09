"""TB01: bounded two-main-board placement study using every current part.

No old copper or electrical qualification is inherited. Same-source nets stay
separate from other source nets; interfaces are intentionally not guessed.
Dimensions are project receiving requirements, never manufacturing approval.
"""
import argparse
import copy
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np
from shapely import contains_xy
from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from hardware.cad.a12.repaired import height as power_height
from hardware.cad.a12.enclosure_growth.nf265_fpc91.model import selected_height
from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.assembly_layout import outline
from hardware.fabrication.digital_core_layout import pad_box

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'hardware/fabrication'
HC=ROOT/'staging/housing-consolidation-review-01/review.json'
AP=ROOT/'staging/assembly-layout-04/allocation.json'
PREFIX={'audio_main':'A','digital_core':'D','power_supply':'P','input_protection':'I',
        'rail_disconnect':'E','rail_monitor':'M','negative_startup_protection':'N','fan_health_protection':'F'}
PZ=7.9
SZ=6.75
STEP=.5
GAP=.3
EPS=1e-8


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def props(fp):return {p[1]:p[2] for p in children(fp,'property')}
def offset(b,dx,dy):return [b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
def overlap(a,b,gap=0):return a[0]<b[2]+gap-EPS and a[2]>b[0]-gap+EPS and a[1]<b[3]+gap-EPS and a[3]>b[1]-gap+EPS


def capture():
    hc=json.loads(HC.read_text());ap=json.loads(AP.read_text())
    audio_plan_path=ROOT/'staging/audio-main-controls-06/plan.json'
    audio_plan=json.loads(audio_plan_path.read_text())
    nfmodel_path=REPO/'hardware/cad/a12/enclosure_growth/nf265_fpc91/generated/model.json'
    nfmodel=json.loads(nfmodel_path.read_text())
    older={(p['id'].split('_')[0],p['ref']):p for p in nfmodel['component_records']}
    paths=[HC,AP,audio_plan_path,nfmodel_path,Path(__file__),
           REPO/'hardware/cad/a12/repaired.py',REPO/'hardware/cad/a12/positive_links/selected_parts.py',
           REPO/'hardware/cad/a12/enclosure_growth/nf265_fpc91/model.py',
           REPO/'hardware/electronics/output_stage/check_placement.py',
           ROOT/'digital_core_layout.py',ROOT/'assembly_layout.py',REPO/'hardware/electronics/common/sexpr.py']
    parts=[];retired=[];sources={};polys={}
    contexts=[dict(id=r[0],xy=[r[1],r[2],r[1]+r[4],r[2]+r[5]],z=[r[3],r[3]+r[6]]) for r in ap['retained_context_boxes']]
    for c in contexts:
        if c['id'].startswith(('input_rca_','input_ts_','output_rca_','output_ts_')):c['z']=[z+.8 for z in c['z']]
    # Entire touch-module receiver including the previous 3 mm tail allocation.
    contexts.append(dict(id='touch_module_body_and_tail_reserve',xy=[82,158,135.848,179.844],z=[17,28]))
    # Existing floor-post centres require true openings in the proposed board.
    posts=[[130.0871,168.922],[93.0871,168.9352]]
    for i,(x,y) in enumerate(posts):contexts.append(dict(id=f'touch_post_{i}',xy=[x-4.5,y-4.5,x+4.5,y+4.5],z=[2.7,20]))
    for b in hc['boards']:
        role=b['id'];path=REPO/b['source'];paths.append(path);tree,poly=outline(path)
        sources[role]=dict(path=b['source'],sha256=sha(path),footprints=len(children(tree,'footprint')))
        x0,y0,*_=poly.bounds;dx,dy=b['datum'][0]-x0,b['datum'][1]-y0
        polys[role]=translate(poly,dx,dy)
        netnames={str(n[1]):str(n[2]) for n in children(tree,'net')}
        for fp in children(tree,'footprint'):
            p=props(fp);r=p['Reference'];v=p['Value'];side=str(first(fp,'layer')[1])[0]
            if r.startswith('H') and role not in ['audio_main','digital_core','input_protection','negative_startup_protection']:
                retired.append(dict(role=role,ref=r,value=v,reason='old separate-board mounting hole; replaced by proposed common-board mounts'))
                continue
            pos=first(fp,'at');x,y=float(pos[1]),float(pos[2]);angle=float(pos[3]) if len(pos)>3 else 0
            cr=courtyard(fp,side+'.CrtYd');base=offset(cr,-x,-y)
            mechanical=r.startswith('H')
            old=older.get(('NF265' if role=='negative_startup_protection' else 'FPC91',r))
            if mechanical:h,basis=2.31,'unapproved fastener head/washer allocation'
            elif role=='audio_main':h,basis=audio_plan['declared_receiving_height_mm'][r],'AC04 unapproved installed-height allocation'
            elif role=='digital_core':h,basis=(17.2 if r=='U1001' else 13.5 if r.startswith('J') else 3.2),'AP04 unapproved installed-height allocation'
            elif role=='rail_monitor':h,basis=(13.5 if r.startswith('J') else 2.5 if r=='C50' else 2.0),'AP04 unapproved installed-height allocation'
            elif role in ['negative_startup_protection','fan_health_protection']:
                if old and old['part']==v:
                    h,basis=old['projection_mm'],'same value NR01 height; '+old['basis']
                else:
                    h,basis,_=selected_height(dict(part=v,footprint=str(fp[1]),source='current native footprint'),[])
                if r.startswith('J'):h=max(h,13.5);basis+='; provisional complete mate height 13.5 mm'
            elif role=='input_protection':
                h={'J1':12.31,'J2':11,'J3':12.31,'S1':4.31,'F1':4.31}[r];basis='AP04 existing inlet receiving height, part approval pending'
            else:
                try:h,basis=power_height(str(fp[1]),r,v)
                except ValueError:
                    if r.startswith('R'):h=0.9
                    elif r.startswith('C') and ('0603' in str(fp[1]) or '0402' in str(fp[1])):h=1.5
                    elif 'DCK0005A' in str(fp[1]):h=1.4
                    elif r.startswith('J'):h=13.5
                    else:raise
                    basis='new provisional package/mate receiving ceiling; exact supplier/process acceptance absent'
            # Preserve actual footprint courtyard; extra mated allowance is explicit.
            extra=.5 if r.startswith('J') and role not in ['input_protection','digital_core','audio_main'] else 0
            bb=[base[0]-extra,base[1]-extra,base[2]+extra,base[3]+extra]
            # NR01 selected force-port receivers can extend beyond the copper
            # courtyard: transfer the bound through the actual old/new poses.
            if old and old['part']==v and r.startswith('J') and old['native_side']==side:
                oldangle=float(old['native_pose'][2]) if len(old['native_pose'])>2 else 0
                if abs(oldangle-angle)<EPS:
                    wb=old['world_box_mm'];originx=172 if role=='negative_startup_protection' else 14
                    local=[wb[0]-originx,wb[2]-3.5,wb[0]-originx+wb[3],wb[2]-3.5+wb[5]]
                    ob=offset(local,-float(old['native_pose'][0]),-float(old['native_pose'][1]))
                    bb=[min(bb[0],ob[0]),min(bb[1],ob[1]),max(bb[2],ob[2]),max(bb[3],ob[3])]
            tails=[];padnets=[]
            for pad in children(fp,'pad'):
                if pad[2]=='thru_hole':tails.append(offset(pad_box(fp,pad,.15),-x,-y))
                nets=children(pad,'net');net=''
                if nets:
                    n=nets[0];net=str(n[2]) if len(n)>2 else netnames.get(str(n[1]),str(n[1]))
                padnets.append([str(pad[1]),net,str(pad[2])])
            parts.append(dict(id=PREFIX[role]+'_'+r,role=role,ref=r,value=v,footprint=str(fp[1]),side=side,
                angle=angle,source_xy=[x,y],source_world_xy=[x+dx,y+dy],body_relative_xy=bb,
                courtyard_relative_xy=base,height_mm=h,height_basis=basis,
                tails_relative_xy=tails,tail_projection_mm=3.2,
                pad_nets=padnets,mechanical=mechanical,
                target_board='signal_main' if role in ['audio_main','digital_core'] else 'power_protection'))
    signal=unary_union([polys['audio_main'],polys['digital_core'],box(180,47,184,104)])
    power=unary_union([box(8,108.5,328,182.5),box(8,30,27,110),box(8,30,250,40),polys['input_protection']])
    for x,y in posts:power=power.difference(Point(x,y).buffer(4.5,quad_segs=32))
    assert power.geom_type=='Polygon' and power.is_valid and signal.is_valid
    assert power.distance(signal)>=1.5-EPS
    # New power mounting candidates. Each keeps a 3.6 mm radial head/tool reserve.
    mounts=[[13,35],[240,35],[13,100],[13,113],[164,113],[323,113],[13,178],[164,178],[323,178]]
    for i,(x,y) in enumerate(mounts):
        assert power.buffer(-.5).covers(Point(x,y).buffer(3.6)),('mount outside',i)
    return dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},sources=sources,parts=parts,
        retired_mounts=retired,context=contexts,signal_polygon=list(signal.exterior.coords),
        power_polygon=list(power.exterior.coords),power_holes=[list(r.coords) for r in power.interiors],
        power_mount_centres=mounts,touch_post_hole_centres=posts,signal_Z=SZ,power_Z=PZ,
        board_thickness_range_mm=[1.44,1.76],board_Z_tolerance_mm=.2,
        source_codec_missing=True,codec_reserved_world_xy=[84,64,100,80],
        full_component_heights_supplier_approved=False,complete_harness_included=False,
        thermal_base_and_airflow_redesign_required=True,complete_fit_verified=False,fabrication_released=False)


class Packer:
    def __init__(self,cap):
        self.cap=cap;self.poly=Polygon(cap['power_polygon'],cap['power_holes'])
        self.edge=self.poly.buffer(-.5)
        self.x=np.arange(0,334+STEP,STEP);self.y=np.arange(0,188.5+STEP,STEP)
        self.xx,self.yy=np.meshgrid(self.x,self.y)
        # Grid cell upper/right corners: require every sample inside the shrunken
        # board; an exact continuous polygon check follows every proposed pose.
        self.base=~contains_xy(self.edge,self.xx,self.yy)
        self.mask={s:self.base.copy() for s in ['F','B']}
        self.placed={};self.spatial={s:{} for s in ['F','B']};self.context_cache={}
        for x,y in cap['power_mount_centres']:
            for s in ['F','B']:self.paint(self.mask[s],[x-3.6,y-3.6,x+3.6,y+3.6],.15)

    def paint(self,mask,b,gap=0):
        x0=max(0,math.floor((b[0]-gap)/STEP));y0=max(0,math.floor((b[1]-gap)/STEP))
        x1=min(mask.shape[1],math.ceil((b[2]+gap)/STEP)+1);y1=min(mask.shape[0],math.ceil((b[3]+gap)/STEP)+1)
        mask[y0:y1,x0:x1]=True

    def zrange(self,p,kind='body'):
        if kind=='tail':return [PZ-.2-p['tail_projection_mm'],PZ+.2]
        return [PZ-.2+1.44,PZ+.2+1.76+p['height_mm']] if p['side']=='F' else [PZ-.2-p['height_mm'],PZ+.2]

    def context_mask(self,p,tail=False):
        z=self.zrange(p,'tail' if tail else 'body');key=tuple(z)
        if key not in self.context_cache:
            mask=np.zeros_like(self.base)
            for c in self.cap['context']:
                if min(z[1]+.25,c['z'][1])-max(z[0]-.25,c['z'][0])>EPS:self.paint(mask,c['xy'],.25)
            if z[0]<3.05-EPS or z[1]>43.35+EPS:mask[:]=True
            self.context_cache[key]=mask
        return self.context_cache[key]

    @staticmethod
    def keys(b):return [(x,y) for x in range(math.floor(b[0]/10),math.floor(b[2]/10)+1) for y in range(math.floor(b[1]/10),math.floor(b[3]/10)+1)]

    def add_obstacle(self,side,b,ident):
        for k in self.keys([b[0]-.3,b[1]-.3,b[2]+.3,b[3]+.3]):self.spatial[side].setdefault(k,[]).append((b,ident))

    def legal(self,p,xy,fixed_inlet=False,ignore=()):
        b=offset(p['body_relative_xy'],*xy);tails=[offset(t,*xy) for t in p['tails_relative_xy']]
        if not fixed_inlet and not self.edge.covers(box(*b)):return False
        for kind,bb in [('body',b)]+[('tail',t) for t in tails]:
            z=self.zrange(p,kind)
            if z[0]<3.05-EPS or z[1]>43.35+EPS:return False
            for c in self.cap['context']:
                # Inlet context already describes these exact retained parts.
                if c['id'].startswith('inlet_') and p['role']=='input_protection':continue
                if min(z[1]+.25,c['z'][1])-max(z[0]-.25,c['z'][0])>EPS and overlap(bb,c['xy'],.25):return False
            side=p['side'] if kind=='body' else ('B' if p['side']=='F' else 'F')
            for k in self.keys(bb):
                for other,ident in self.spatial[side].get(k,[]):
                    if ident not in ignore and overlap(bb,other,GAP):return False
        return True

    def install(self,p,xy,fixed=False):
        assert self.legal(p,xy,fixed_inlet=fixed),(p['id'],xy)
        self.placed[p['id']]=dict(xy=list(xy),side=p['side'],angle=p['angle'],fixed_inlet=fixed)
        b=offset(p['body_relative_xy'],*xy);side=p['side']
        self.paint(self.mask[side],b,GAP);self.add_obstacle(side,b,p['id'])
        for t in p['tails_relative_xy']:
            bb=offset(t,*xy);op='B' if side=='F' else 'F'
            self.paint(self.mask[op],bb,GAP);self.add_obstacle(op,bb,p['id'])

    def sums(self,mask,b):
        # At each grid anchor, sum occupied samples inside the relative bbox.
        integral=np.pad(mask.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
        x0=np.arange(len(self.x))+math.floor(b[0]/STEP);x1=np.arange(len(self.x))+math.ceil(b[2]/STEP)+1
        y0=np.arange(len(self.y))+math.floor(b[1]/STEP);y1=np.arange(len(self.y))+math.ceil(b[3]/STEP)+1
        valid=(x0>=0)[None,:]&(x1<=mask.shape[1])[None,:]&(y0>=0)[:,None]&(y1<=mask.shape[0])[:,None]
        x0=x0.clip(0,mask.shape[1]);x1=x1.clip(0,mask.shape[1]);y0=y0.clip(0,mask.shape[0]);y1=y1.clip(0,mask.shape[0])
        sums=integral[y1[:,None],x1]-integral[y0[:,None],x1]-integral[y1[:,None],x0]+integral[y0[:,None],x0]
        return valid & (sums==0)

    def find(self,p,target):
        mask=self.mask[p['side']]|self.context_mask(p)
        free=self.sums(mask,p['body_relative_xy'])
        op='B' if p['side']=='F' else 'F'
        for t in p['tails_relative_xy']:
            free &= self.sums(self.mask[op]|self.context_mask(p,tail=True),t)
        iy,ix=np.nonzero(free)
        if not len(ix):return None
        cost=(self.x[ix]-target[0])**2+(self.y[iy]-target[1])**2
        for index in np.argsort(cost)[:100]:
            xy=[float(self.x[ix[index]]),float(self.y[iy[index]])]
            if self.legal(p,xy):return xy
        return None


def build(label):
    out=ROOT/'staging'/label;assert not out.exists()
    cap=capture();out.mkdir();(out/'capture.json').write_text(json.dumps(cap,indent=2)+'\n')
    power=[p for p in cap['parts'] if p['target_board']=='power_protection']
    pack=Packer(cap);failed=[];moved=[];start=time.monotonic()
    # Remove duplicated inlet context only from packing; the source record remains.
    pack.cap=copy.deepcopy(cap)
    pack.cap['context']=[c for c in cap['context'] if not c['id'].startswith('inlet_')]
    for p in power:
        if p['role']=='input_protection':pack.install(p,p['source_world_xy'],fixed=True)
    # Retain the force/strain interface as one rigid local group.
    force=[p for p in power if p['role']=='negative_startup_protection' and p['ref'] in ['J2','J4','H101','H102']]
    force_xy={p['id']:[p['source_xy'][0]+112,p['source_xy'][1]+137] for p in force}
    for p in force:
        if not pack.legal(p,force_xy[p['id']]):failed.append(dict(id=p['id'],reason='fixed force/strain group cannot fit'))
        else:pack.install(p,force_xy[p['id']])
    # Largest receiving envelopes first; nearest legal original positions are
    # preferred. Former upper/vertical circuits get explicit horizontal targets.
    remaining=[p for p in power if p['id'] not in pack.placed]
    remaining.sort(key=lambda p:(-((p['body_relative_xy'][2]-p['body_relative_xy'][0])*(p['body_relative_xy'][3]-p['body_relative_xy'][1])),p['id']))
    for i,p in enumerate(remaining):
        role=p['role'];xy=p['source_world_xy']
        if role=='negative_startup_protection':target=[172+p['source_xy'][0],143+p['source_xy'][1]]
        elif role=='fan_health_protection':target=[14+p['source_xy'][0],144+p['source_xy'][1]]
        elif role=='rail_monitor':target=[12+p['source_xy'][0]*2.7,35+p['source_xy'][1]*.08]
        else:target=xy
        if role in ['power_supply','rail_disconnect'] and pack.legal(p,xy):chosen=xy
        else:chosen=pack.find(p,target)
        if chosen is None:failed.append(dict(id=p['id'],role=role,reason='bounded fixed-angle/fixed-face packing exhausted',body=p['body_relative_xy']))
        else:
            pack.install(p,chosen)
            if chosen!=xy:moved.append(p['id'])
        if i%100==0:print(f'{i}/{len(remaining)} scanned; placed {len(pack.placed)}; missing {len(failed)}',flush=True)
    signal={p['id']:dict(xy=p['source_world_xy'],side=p['side'],angle=p['angle']) for p in cap['parts'] if p['target_board']=='signal_main'}
    result=dict(source_sha256={str((out/'capture.json').relative_to(REPO)):sha(out/'capture.json'),str(Path(__file__).relative_to(REPO)):sha(Path(__file__))},
        poses={**signal,**pack.placed},failed=failed,source_part_count=len(cap['parts']),placed_count=len(signal)+len(pack.placed),
        source_counts=dict(Counter(p['role'] for p in cap['parts'])),moved_power_parts=moved,
        search_elapsed_seconds=time.monotonic()-start,all_known_parts_placed=not failed,
        old_nets_merged=False,old_copper_reused=False,complete_fit_verified=False,fabrication_released=False)
    (out/'placement.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['source_part_count','placed_count','failed','search_elapsed_seconds']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='two-board-placement-01')
    build(parser.parse_args().label)
