#!/usr/bin/env python3
"""Place/route a B1 audio + power + watchdog carrier using KiCad's Python API.

Run with KiCad's bundled Python. Panel logic, Seed, SD and touch stay on wired
assemblies. This is a layout candidate until native DRC and physical review.
"""
import argparse
import collections
import heapq
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
_config=Path(__file__).resolve().parents[1]/'build/hardware/pcb-config'
_config.mkdir(parents=True,exist_ok=True)
os.environ['KICAD_CONFIG_HOME']=str(_config)
import pcbnew as pcb
import numpy as np
from generate_budget import ROOT, DEST, all_sheets

PITCH=.125
SIZE=100
GRID=int(SIZE/PITCH)+1
TRACK=.20
CLEAR=.20
# Inner 1 remains a continuous ground return. Inner 2 is a 5V pour with
# clearance around occasional signal escape tracks; native filling/DRC must
# confirm the remaining power plane reaches every supply pad.
LAYERS=[pcb.F_Cu,pcb.B_Cu,pcb.In2_Cu]


def mm(value):return pcb.FromMM(float(value))
def vec(x,y):return pcb.VECTOR2I(mm(x),mm(y))
def togrid(x,y):return round(x/PITCH),round(y/PITCH)
def point(p):return pcb.ToMM(p.x),pcb.ToMM(p.y)


def bounds(fp):
    box=fp.GetBoundingBox(False,False)
    return pcb.ToMM(box.GetX()),pcb.ToMM(box.GetY()),pcb.ToMM(box.GetRight()),pcb.ToMM(box.GetBottom())


class Router:
    def __init__(self,board):
        self.board=board
        self.obstacles=np.zeros((len(LAYERS),GRID,GRID),dtype=np.int32)
        self.vias=np.zeros_like(self.obstacles)
        self.holes=np.zeros((GRID,GRID),dtype=np.bool_)
        self.existing_vias={}
        self.nodes=collections.defaultdict(list)
        self.pad_endpoints={}
        self.fanout=set()
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                n=pad.GetNetCode()
                x,y=point(pad.GetPosition());gx,gy=togrid(x,y)
                layer=0 if pad.IsOnLayer(pcb.F_Cu) else 1
                if n:self.nodes[n].append((gx,gy,layer,x,y))
                if n and fp.GetReference().startswith('U'):self.fanout.add((n,gx,gy))
                box=pad.GetBoundingBox()
                x0,y0=pcb.ToMM(box.GetX()),pcb.ToMM(box.GetY())
                x1,y1=pcb.ToMM(box.GetRight()),pcb.ToMM(box.GetBottom())
                for li,l in enumerate(LAYERS):
                    if pad.IsOnLayer(l):
                        self.rect(self.obstacles[li],n or -1,x0-.31,y0-.31,x1+.31,y1+.31)
                        self.rect(self.vias[li],n or -1,x0-.56,y0-.56,x1+.56,y1+.56)
                drill=max(point(pad.GetDrillSize()))
                if drill:
                    self.hole(gx,gy,drill/2+.40)
                    self.existing_vias[gx,gy]=n
        self.obstacles[:,:12,:]=-1;self.obstacles[:,-12:,:]=-1
        self.obstacles[:,:,:12]=-1;self.obstacles[:,:,-12:]=-1
        self.vias[:,:12,:]=-1;self.vias[:,-12:,:]=-1
        self.vias[:,:,:12]=-1;self.vias[:,:,-12:]=-1
        for x,y in [(4,4),(96,4),(4,96),(96,96)]:
            self.disk(self.obstacles,-1,*togrid(x,y),2.3,both=True)
            self.disk(self.vias,-1,*togrid(x,y),2.5,both=True)

    @staticmethod
    def merge(array,n):
        mask=(array!=0)&(array!=n);array[:]=np.where(mask,-1,n)

    def rect(self,array,n,x0,y0,x1,y1):
        a,b=max(0,math.ceil(x0/PITCH)),max(0,math.ceil(y0/PITCH))
        c,d=min(GRID-1,math.floor(x1/PITCH)),min(GRID-1,math.floor(y1/PITCH))
        self.merge(array[a:c+1,b:d+1],n)

    def disk(self,array,n,x,y,r,both=False,layer=0):
        cells=math.ceil(r/PITCH)
        for dx in range(-cells,cells+1):
            for dy in range(-cells,cells+1):
                if dx*dx+dy*dy>(r/PITCH)**2+.01:continue
                xx,yy=x+dx,y+dy
                if not(0<=xx<GRID and 0<=yy<GRID):continue
                for li in range(len(LAYERS)) if both else [layer]:
                    old=array[li,xx,yy]
                    array[li,xx,yy]=n if old in (0,n) else -1

    def hole(self,x,y,r):
        cells=math.ceil(r/PITCH)
        for dx in range(-cells,cells+1):
            for dy in range(-cells,cells+1):
                if dx*dx+dy*dy<=(r/PITCH)**2+.01 and 0<=x+dx<GRID and 0<=y+dy<GRID:self.holes[x+dx,y+dy]=True

    def via_ok(self,x,y,n):
        return self.existing_vias.get((x,y))==n or (not self.holes[x,y] and all(self.vias[l,x,y] in (0,n) for l in range(len(LAYERS))))

    def search(self,start,end,n,plane=False):
        sx,sy,sl=start[:3]
        if end:ex,ey,el=end[:3]
        def heuristic(x,y,l):return 0 if plane else abs(x-ex)+abs(y-ey)+(l!=el)*8
        serial=itertools.count();queue=[(heuristic(sx,sy,sl),0,next(serial),(sx,sy,sl))]
        costs={(sx,sy,sl):0};previous={};found=None
        while queue:
            _,g,_,state=heapq.heappop(queue)
            if costs.get(state)!=g:continue
            x,y,l=state
            if (plane and g>=3 and self.via_ok(x,y,n)) or (not plane and state==(ex,ey,el)):
                found=state;break
            if len(costs)>250000:break
            options=[(x+1,y,l,1),(x-1,y,l,1),(x,y+1,l,1),(x,y-1,l,1)]
            if not plane and self.via_ok(x,y,n):options.extend((x,y,ll,16) for ll in range(len(LAYERS)) if ll!=l)
            for xx,yy,ll,step in options:
                if not(12<=xx<GRID-12 and 12<=yy<GRID-12):continue
                if self.obstacles[ll,xx,yy] not in (0,n):continue
                ns=(xx,yy,ll);ng=g+step
                if ng>=costs.get(ns,1<<30):continue
                costs[ns]=ng;previous[ns]=state
                heapq.heappush(queue,(ng+heuristic(xx,yy,ll),ng,next(serial),ns))
        if found is None:return None
        path=[found]
        while path[-1]!=(sx,sy,sl):path.append(previous[path[-1]])
        path.reverse();return path

    def segment(self,n,a,b,l):
        if a==b:return
        track=pcb.PCB_TRACK(self.board);track.SetStart(vec(*a));track.SetEnd(vec(*b))
        track.SetLayer(LAYERS[l]);track.SetWidth(mm(TRACK));track.SetNetCode(n);self.board.Add(track)

    def via(self,n,x,y):
        if self.existing_vias.get((x,y))==n:return
        v=pcb.PCB_VIA(self.board);v.SetPosition(vec(x*PITCH,y*PITCH));v.SetWidth(mm(.60));v.SetDrill(mm(.30))
        v.SetViaType(pcb.VIATYPE_THROUGH);v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetNetCode(n);self.board.Add(v)
        self.disk(self.obstacles,n,x,y,.61,both=True);self.disk(self.vias,n,x,y,.81,both=True)
        self.existing_vias[x,y]=n;self.hole(x,y,.81)

    def commit(self,path,n,start,end=None,plane=False):
        self.segment(n,(start[3],start[4]),(path[0][0]*PITCH,path[0][1]*PITCH),path[0][2])
        begin=path[0];direction=None
        for a,b in zip(path,path[1:]):
            if a[2]!=b[2]:
                self.segment(n,(begin[0]*PITCH,begin[1]*PITCH),(a[0]*PITCH,a[1]*PITCH),a[2]);self.via(n,a[0],a[1]);begin=b;direction=None
            else:
                new=(b[0]-a[0],b[1]-a[1])
                if direction and direction!=new:
                    self.segment(n,(begin[0]*PITCH,begin[1]*PITCH),(a[0]*PITCH,a[1]*PITCH),a[2]);begin=a
                direction=new
        last=path[-1];self.segment(n,(begin[0]*PITCH,begin[1]*PITCH),(last[0]*PITCH,last[1]*PITCH),last[2])
        if end:self.segment(n,(last[0]*PITCH,last[1]*PITCH),(end[3],end[4]),last[2])
        if plane:self.via(n,last[0],last[1])
        for x,y,l in path:
            self.disk(self.obstacles,n,x,y,.41,layer=l);self.disk(self.vias,n,x,y,.61,layer=l)

    def route(self):
        names={n.GetNetCode():n.GetNetname() for n in self.board.GetNetInfo().NetsByNetcode().values()}
        failures=[];start_time=time.time()
        # Give fine-pitch IC pins their own escape before long buses can box
        # them in. Remaining routing starts at the escape via on inner 2.
        for n,pads in self.nodes.items():
            for i,pad in enumerate(pads):
                if (n,pad[0],pad[1]) not in self.fanout:continue
                path=self.search(pad,None,n,True)
                if path:
                    self.commit(path,n,pad,plane=True);x,y,_=path[-1]
                    pads[i]=(x,y,2,x*PITCH,y*PITCH)
                else:failures.append((names[n],pad[:2],'IC escape'))
        # Planes connect through-hole pads directly. Stitch each surface pad to
        # its plane before routing signals, keeping their return paths explicit.
        for n in self.nodes:
            if names[n] not in ('GND','+5V'):continue
            for pad in self.nodes[n]:
                # Duplicate top/bottom copper means a drilled pad, already on plane.
                x,y,_,_,_=pad
                if self.existing_vias.get((x,y))==n:continue
                is_th=any(abs(point(p.GetPosition())[0]-pad[3])<1e-6 and abs(point(p.GetPosition())[1]-pad[4])<1e-6 and p.IsOnLayer(pcb.In1_Cu) for f in self.board.GetFootprints() for p in f.Pads())
                if is_th:continue
                path=self.search(pad,None,n,True)
                if path:self.commit(path,n,pad,plane=True)
                else:failures.append((names[n],pad[:2],'plane stitch'))
        count=0
        priority={'EXT_RAILS_OK':0,'+3V3':1}
        for n,pads in sorted(self.nodes.items(),key=lambda item:(priority.get(names[item[0]],2),len(item[1]),item[0])):
            if names[n] in ('GND','+5V') or len(pads)<2:continue
            connected=[pads[0]];remaining=pads[1:]
            while remaining:
                distance,a,b=min((abs(p[0]-q[0])+abs(p[1]-q[1]),p,q) for p in connected for q in remaining)
                path=self.search(a,b,n)
                if path:self.commit(path,n,a,b)
                else:failures.append((names[n],a[:2],b[:2]))
                connected.append(b);remaining.remove(b);count+=1
                if count%20==0:print(f'Routed {count} signal branches; {len(failures)} unresolved; {time.time()-start_time:.1f}s',flush=True)
        return failures


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--footprints',type=Path,required=True)
    parser.add_argument('--no-route',action='store_true');args=parser.parse_args()
    board=pcb.BOARD();board.SetCopperLayerCount(4)
    settings=board.GetDesignSettings();settings.SetCopperLayerCount(4);settings.m_MinClearance=mm(.2)
    settings.m_TrackMinWidth=mm(.2);settings.m_ViasMinSize=mm(.6);settings.m_MinThroughDrill=mm(.3)
    nets={}
    for a,b in [((0,0),(100,0)),((100,0),(100,100)),((100,100),(0,100)),((0,100),(0,0))]:
        line=pcb.PCB_SHAPE();line.SetShape(pcb.SHAPE_T_SEGMENT);line.SetStart(vec(*a));line.SetEnd(vec(*b));line.SetLayer(pcb.Edge_Cuts);line.SetWidth(mm(.05));board.Add(line)
    fixed={'U28':(40,28),'K1':(80,32),'Q1':(82,14),'D1':(89,14),
           'U21':(15,62),'U25':(33,62),'U26':(45,62),'U22':(15,77),'U23':(31,77),
           'U24':(49,77),'U35':(67,62),'U27':(82,62),'U32':(80,78),
           'J_PWR1':(8,12),'J_SW1':(20,12),'J_PWR2':(30,12),'J_AUD1':(8,30),
           'J_IN1':(8,45),'J_IN2':(8,54),'J_OUT1':(93,45),'J_OUT2':(93,54),
           'J_BP2':(60,90),'J_BYP1':(80,90),'RV20':(54,34),'RV21':(54,18)}
    occupied=[(x-2.4,y-2.4,x+2.4,y+2.4) for x,y in [(4,4),(96,4),(4,96),(96,96)]];parts={};footprints={}
    def overlaps(rect):
        x,y,xx,yy=rect
        return x<3 or y<3 or xx>97 or yy>97 or any(x<d+.6 and xx>a-.6 and y<e+.6 and yy>b-.6 for a,b,d,e in occupied)
    sheets=all_sheets()
    globals_={v['net'] for d in sheets for p in d['components'] if p['ref'].startswith('J') for v in p['pins'] if v.get('net')}
    for d in sheets[:4]:
        for p in d['components']:
            if p.get('virtual') or p['ref'] in ('SW32','SW34'):continue
            assert p.get('footprint'),p['ref']+' needs a footprint'
            parts[p['ref']]=p
    # Match the hierarchical schematic's exported net names.
    for d in sheets[:4]:
        for p in d['components']:
            for v in p['pins']:
                if v.get('net') and v['net'] not in globals_:v['net']='/'+d['project']+'/'+v['net']
    for name in sorted({v['net'] for p in parts.values() for v in p['pins'] if v.get('net')}):
        net=board.FindNet(name)
        if not net or net.GetNetCode()<1:net=pcb.NETINFO_ITEM(board,name);board.Add(net)
        nets[name]=net
    order=sorted(parts,key=lambda r:(r not in fixed,0 if r.startswith(('R4','D4')) else 1 if r.startswith('C4') else 2 if r.startswith('C') else 3,r))
    for ref in order:
        part=parts[ref];lib,name=part['footprint'].split(':');f=pcb.FootprintLoad(str(args.footprints/(lib+'.pretty')),name)
        assert f,part['footprint'];f.SetReference(ref);f.SetValue(part['value']);f.Value().SetVisible(False)
        f.SetFPID(pcb.LIB_ID(lib,name))
        f.Reference().SetTextSize(vec(.7,.7));f.Reference().SetTextThickness(mm(.12))
        f.Reference().SetLayer(pcb.F_Fab)
        f.Reference().SetVisible(False) # the library's ${REFERENCE} fab text identifies the part once
        f.SetPosition(vec(0,0));board.Add(f)
        for pad in f.Pads():
            pin=next((v for v in part['pins'] if v['number']==pad.GetNumber()),None)
            assert pin,(ref,pad.GetNumber())
            if pin.get('net'):pad.SetNet(nets[pin['net']])
        if ref in fixed:
            f.SetPosition(vec(*fixed[ref]));rect=bounds(f)
            assert not overlaps(rect),('Fixed placement collision',ref,rect)
        else:
            # Place bulky parts first, then local decoupling / two-pin parts.
            # Net-neighbor distance guides placement; bounding boxes enforce
            # assembly room independently of copper routing.
            preferred=[]
            pin_nets={v.get('net') for v in part['pins']}-{'GND','+5V','+3V3','VREF_2V5',None}
            for other,fp in footprints.items():
                if pin_nets&{v.get('net') for v in parts[other]['pins']}:preferred.append(point(fp.GetPosition()))
            target=(sum(x for x,y in preferred)/len(preferred),sum(y for x,y in preferred)/len(preferred)) if preferred else (50,50)
            candidates=sorted(((x,y) for x in range(7,94,3) for y in range(8,94,3)),key=lambda t:(t[0]-target[0])**2+(t[1]-target[1])**2)
            for x,y in candidates:
                f.SetPosition(vec(x,y));rect=bounds(f)
                if not overlaps(rect):break
            else:raise RuntimeError('No room for '+ref)
        occupied.append(tuple(v+(-1 if i<2 else 1) for i,v in enumerate(rect)) if ref.startswith('U') else rect);footprints[ref]=f
    for i,(x,y) in enumerate([(4,4),(96,4),(4,96),(96,96)],1):
        f=pcb.FootprintLoad(str(args.footprints/'MountingHole.pretty'),'MountingHole_3.2mm_M3');f.SetReference('H'+str(i));f.Reference().SetLayer(pcb.F_Fab);f.Value().SetVisible(False);f.SetPosition(vec(x,y));board.Add(f)
    for layer,name in [(pcb.In1_Cu,'GND'),(pcb.In2_Cu,'+5V')]:
        zone=pcb.ZONE(board);zone.SetLayer(layer);zone.SetNet(nets[name]);zone.SetLocalClearance(mm(.25))
        zone.SetThermalReliefGap(mm(.25));zone.SetThermalReliefSpokeWidth(mm(.3));zone.SetMinThickness(mm(.2))
        outline=zone.Outline();outline.NewOutline()
        for x,y in [(1,1),(99,1),(99,99),(1,99)]:outline.Append(mm(x),mm(y))
        board.Add(zone)
    failures=[] if args.no_route else Router(board).route()
    # Fine-pitch escapes sometimes reconnect entirely on their original layer.
    # Remove the unused drill in that case; do not suppress dangling-via DRC.
    tracks=[t for t in board.GetTracks() if not isinstance(t,pcb.PCB_VIA)]
    for via in list(board.GetTracks()):
        if not isinstance(via,pcb.PCB_VIA) or via.GetNetname() in ('GND','+5V'):continue
        p=via.GetPosition();layers=set()
        for t in tracks:
            if t.GetNetCode()!=via.GetNetCode():continue
            a,b=t.GetStart(),t.GetEnd();dx,dy=b.x-a.x,b.y-a.y
            if abs((p.x-a.x)*dy-(p.y-a.y)*dx)<=1000*max(abs(dx),abs(dy),1) and min(a.x,b.x)-1000<=p.x<=max(a.x,b.x)+1000 and min(a.y,b.y)-1000<=p.y<=max(a.y,b.y)+1000:layers.add(t.GetLayer())
        if len(layers)<2:board.Remove(via)
    board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones())
    dest=DEST/'pcb';dest.mkdir(parents=True,exist_ok=True);path=dest/'carrier.kicad_pcb';pcb.SaveBoard(str(path),board)
    (dest/'carrier.kicad_pro').write_text('{"meta":{"filename":"carrier.kicad_pro","version":1}}\n')
    libraries=sorted({p['footprint'].split(':')[0] for p in parts.values()})
    (dest/'fp-lib-table').write_text('(fp_lib_table (version 7)\n'+'\n'.join(f'(lib (name "{n}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty") (options "") (descr "KiCad 10"))' for n in libraries)+')\n')
    (dest/'layout.json').write_text(json.dumps(dict(board_mm=[100,100],copper_layers=4,
        status='Layout candidate; native DRC and physical review required',routed=not args.no_route,
        unresolved_routes=failures,board_references=sorted(parts),offboard_switches=['SW32','SW34'],
        placements={r:[round(v,3) for v in point(f.GetPosition())] for r,f in footprints.items()}),indent=2)+'\n')
    print(f'Saved {path}; {len(parts)} circuit footprints; {len(failures)} routing failures',flush=True)


if __name__=='__main__':main()
