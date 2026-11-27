"""Read-only retained single-row header snapshot, independent of native KiCad."""
from pathlib import Path
import argparse,json,hashlib,math
from hardware.electronics.common import sexpr as sx
from hardware.fabrication import assembly_layout
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();tree,_=assembly_layout.outline(a.pcb)
 expected={i['reference']:i for i in json.loads((HERE.parent/'r7/interface-manifest.json').read_text())['interfaces'] if i['reference']=='D_J2003' or i['reference'] in ['D_J'+str(n) for n in range(1020,1030)]};rows=[]
 for fp in sx.children(tree,'footprint'):
  props={str(x[1]):str(x[2]) for x in sx.children(fp,'property')};ref=props.get('Reference')
  if ref not in expected:continue
  at=sx.first(fp,'at');x,y,angle=map(float,at[1:4]);assert sx.first(fp,'layer')[1]=='F.Cu' and angle==90;N=5 if ref=='D_J2003' else 3
  assert str(fp[1]).endswith('PinHeader_1x0'+str(N)+'_P2.54mm_Vertical')
  pads=[]
  for pad in sx.children(fp,'pad'):
   pin=str(pad[1]);pa=sx.first(pad,'at');px,py=map(float,pa[1:3]);wx=x+px*math.cos(math.radians(angle))+py*math.sin(math.radians(angle));wy=y-px*math.sin(math.radians(angle))+py*math.cos(math.radians(angle))
   net=str(sx.first(pad,'net')[-1]);drill=float(sx.first(pad,'drill')[1]);size=list(map(float,sx.first(pad,'size')[1:3]));assert pad[2]=='thru_hole' and drill==1 and size==[1.7,1.7]
   old=next(p for p in expected[ref]['pads'] if p['pin']==pin);assert math.dist([wx,wy],old['xy'])<1e-7 and net==old['net'];pads.append(dict(pin=pin,xy_mm=[wx,wy],net=net,drill_mm=drill,pad_size_mm=size))
  assert len(pads)==N;rows.append(dict(reference=ref,retained_mpn=props.get('MPN'),footprint=str(fp[1]),pose=[x,y,angle,'F.Cu'],pads=sorted(pads,key=lambda x:int(x['pin']))))
 assert len(rows)==11
 board_path=str(a.pcb);marker='hardware/';board_path=marker+board_path.split(marker,1)[1] if marker in board_path else a.pcb.name
 out=dict(board_provenance=dict(path=board_path,sha256=hashlib.sha256(a.pcb.read_bytes()).hexdigest()),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),retained_header_count=11,pad_count=35,header_pattern_matches_frozen_capture=True,manufacturer_identity_retained=False,headers=sorted(rows,key=lambda x:x['reference']))
 a.output.write_text(json.dumps(out,indent=2)+'\n');print('11 headers/35 pads match retained capture; manufacturer identity remains generic')
if __name__=='__main__':main()
