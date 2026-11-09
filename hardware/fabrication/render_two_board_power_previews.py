"""Render checked native SVGs as bounded Quick Look previews on macOS."""
import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);args=ap.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.source)
    plots=STAGING/args.source/'plots';report=plots/'native-plots.json'
    native=json.loads(report.read_text())
    for name,h in native['source_sha256'].items():assert sha(REPO/name)==h,name
    files=[plots/(n+'.svg') for n in ['front','back',*[f'inner{i}' for i in range(1,7)]]]
    assert not list(plots.glob('*.png'))
    crops={};outputs=[]
    with tempfile.TemporaryDirectory(prefix='afx-native-previews-',dir='/private/tmp') as temp:
        temp=Path(temp);previews=[]
        for p in files:
            assert sha(p)==native['artifact_sha256'][p.name]
            s=p.read_text();m=re.search(r'viewBox="([^"]+)"',s)
            x,y,w,h=map(float,m.group(1).split());d=max(w,h)
            s=s[:m.start()]+f'viewBox="{x} {y} {d} {d}"'+s[m.end():]
            s=re.sub(r'width="[^"]+"','width="1800"',s,count=1)
            s=re.sub(r'height="[^"]+"','height="1800"',s,count=1)
            target=temp/p.name;target.write_text(s);previews.append(target)
            crops[p.name]=min(1800,math.ceil(1800*h/d)+16)
        cmd=['qlmanage','-t','-s','1800','-o',str(temp),*map(str,previews)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        assert result.returncode==0,(result.stdout,result.stderr)
        for p in files:
            im=Image.open(temp/(p.name+'.png')).convert('RGB');assert im.size==(1800,1800)
            target=plots/(p.stem+'.png');im.crop((0,0,1800,crops[p.name])).save(target);outputs.append(target)
    sheet=Image.new('RGB',(1800,1665),'white');draw=ImageDraw.Draw(sheet)
    for i in range(1,7):
        x=((i-1)%2)*900;y=((i-1)//2)*555
        im=Image.open(plots/f'inner{i}.png');im.thumbnail((900,518))
        sheet.paste(im,(x,y+30));draw.text((x+15,y+8),f'In{i}.Cu',fill='black')
    target=plots/'inner-contact-sheet.png';sheet.save(target);outputs.append(target)
    for p in files:assert sha(p)==native['artifact_sha256'][p.name]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),report,*files]},
        artifact_sha256={p.name:sha(p) for p in outputs},rendering='Quick Look 1800px square preview; blank lower canvas cropped; native SVG unchanged',
        crop_height_px=crops,visual_inspection_pending=True,fabrication_released=False)
    with (plots/'preview-render.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print('Rendered eight native layers and one inner-layer contact sheet')


if __name__=='__main__':run()
