"""Map board-coordinate review viewports into native SVG coordinates via fiducials."""
import argparse,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--prefix',required=True);ap.add_argument('--viewport',nargs=3,type=float,required=True);ap.add_argument('--layers',nargs='+',default=['front','back']);a=ap.parse_args()
    assert all(c.isalnum() or c in '-_' for c in a.source+a.prefix)
    root=STAGING/a.source;pcb=root/'power_protection.kicad_pcb';b=read_sexpr(pcb.read_text());anchors=[]
    for f in children(b,'footprint'):
        for p in children(f,'pad'):
            if str(p[2])=='np_thru_hole' and abs(float(first(p,'drill')[1])-2.4)<1e-9:
                assert [float(x) for x in first(p,'at')[1:3]]==[0,0]
                anchors.append(tuple(float(x) for x in first(f,'at')[1:3]))
    assert len(anchors)>=3
    offsets=[];sources=[Path(__file__),pcb,REPO/'hardware/fabrication/render_two_board_detail_views.py']
    for layer in a.layers:
        src=root/'plots'/(layer+'.svg');sources.append(src)
        circles={(float(e.attrib['cx']),float(e.attrib['cy'])) for e in ET.parse(src).iter() if e.tag.endswith('circle') and abs(float(e.attrib['r'])-1.2)<1e-9}
        shifts=[]
        for x,y in circles:
            dx,dy=x-anchors[0][0],y-anchors[0][1]
            if all(any(abs(px+dx-qx)<1e-4 and abs(py+dy-qy)<1e-4 for qx,qy in circles) for px,py in anchors):shifts.append((round(dx,6),round(dy,6)))
        assert len(set(shifts))==1,(layer,shifts)
        offsets.append(shifts[0])
    assert len(set(offsets))==1,offsets
    dx,dy=offsets[0];x,y,size=a.viewport
    subprocess.run([sys.executable,'-m','hardware.fabrication.render_two_board_detail_views','--source',a.source,'--prefix',a.prefix,'--viewport',str(x+dx),str(y+dy),str(size),'--layers',*a.layers],check=True)
    target=root/'plots'/(a.prefix+'-coordinate-map.json');assert not target.exists()
    target.write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},matched_mounting_holes=len(anchors),board_to_svg_translation_mm=[dx,dy],board_viewport_mm=a.viewport,native_svg_viewport_mm=[x+dx,y+dy,size]),indent=2)+'\n')
    print('Mapped',len(anchors),'mounting holes; translation',dx,dy)

if __name__=='__main__':run()
