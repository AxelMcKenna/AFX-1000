"""Dimensioned source-coloured front/back review images for TB05."""
import html,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hardware.fabrication.two_board_placement import ROOT,REPO,sha

FOLDER=ROOT/'staging/two-board-placement-05'
OUT=ROOT/'staging/two-board-review-01'
COLOURS={'audio_main':'#c88a3d','digital_core':'#268b7f','power_supply':'#bd6269','input_protection':'#7772b2',
         'rail_disconnect':'#9d64ad','rail_monitor':'#3777b0','negative_startup_protection':'#aa8c20','fan_health_protection':'#707b2b'}


def run():
    assert not OUT.exists();OUT.mkdir()
    c=json.loads((FOLDER/'capture.json').read_text());p=json.loads((FOLDER/'placement.json').read_text())
    fontpath='/System/Library/Fonts/Supplemental/Arial.ttf';font=ImageFont.truetype(fontpath,20)
    small=ImageFont.truetype(fontpath,17);big=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',29)
    scale=3.2;ox=35;oy=150
    artifacts=[]
    for side in ['F','B']:
        im=Image.new('RGB',(1550,970),'#f5f7fa');d=ImageDraw.Draw(im)
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1550" height="970" viewBox="0 0 1550 970"><rect width="1550" height="970" fill="#f5f7fa"/>']
        def text(x,y,t,large=False):
            d.text((x,y),t,font=big if large else font,fill='#223344')
            svg.append(f'<text x="{x}" y="{y+25 if large else y+18}" font-family="Arial,sans-serif" font-size="{29 if large else 20}" fill="#223344">{html.escape(t)}</text>')
        def poly(coords,fill,stroke='#607080'):
            pts=[(ox+x*scale,oy+y*scale) for x,y in coords];d.polygon(pts,fill=fill,outline=stroke,width=2)
            svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="{fill}" stroke="{stroke}"/>')
        text(35,22,'AFX-1000 · two-main-board placement study',True)
        text(35,65,('Component face' if side=='F' else 'Underside, shown in the same enclosure coordinates')+' · TB05 · all eight source functions accounted for')
        text(35,101,'Placement only: codec footprint, merged circuits, routing, thermal hardware and full harness remain unfinished.')
        poly([[0,0],[334,0],[334,188.4],[0,188.4]],'#ffffff')
        poly(c['power_polygon'],'#f2e8da');poly(c['signal_polygon'],'#dfefeb')
        for h in c['power_holes']:poly(h,'#ffffff')
        for part in c['parts']:
            if part['side']!=side:continue
            x,y=p['poses'][part['id']]['xy'];b=part['body_relative_xy'];x0=ox+(x+b[0])*scale;y0=oy+(y+b[1])*scale
            x1=ox+(x+b[2])*scale;y1=oy+(y+b[3])*scale;col=COLOURS[part['role']]
            d.rectangle([x0,y0,x1,y1],fill=col,outline='#303a40',width=1)
            svg.append(f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{x1-x0:.3f}" height="{y1-y0:.3f}" fill="{col}" stroke="#303a40" stroke-width=".6"><title>{html.escape(part["id"]+": "+part["value"])}</title></rect>')
        for x,y in c['power_mount_centres']:
            radius=1.2*scale;cx=ox+x*scale;cy=oy+y*scale;d.ellipse([cx-radius,cy-radius,cx+radius,cy+radius],fill='white',outline='#161e27',width=2)
            svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="white" stroke="#161e27"/>')
        codec=c['codec_reserved_world_xy'];points=[(codec[0],codec[1]),(codec[2],codec[1]),(codec[2],codec[3]),(codec[0],codec[3])]
        poly(points,'#f7d6d0','#a32f27');text(ox+codec[0]*scale+2,oy+codec[1]*scale+10,'U201')
        text(1130,155,'Signal main: 268 × 63 mm')
        text(1130,187,'466 electrical parts')
        text(1130,217,'Board underside Z6.75 mm')
        text(1130,262,'Power/protection:')
        text(1130,294,'320 × 181.1 mm overall')
        text(1130,326,'1077 electrical parts')
        text(1130,356,'Board underside Z7.9 mm')
        for i,(role,col) in enumerate(COLOURS.items()):
            yy=410+i*29;d.rectangle([1130,yy,1146,yy+16],fill=col)
            svg.append(f'<rect x="1130" y="{yy}" width="16" height="16" fill="{col}"/>')
            text(1156,yy-2,role.replace('_',' ').capitalize())
        text(1130,675,'Red reserve: missing codec')
        text(1130,708,'No parts silently removed.')
        text(35,785,'Exterior power jack and switch retained; monitor/NF/fan circuits now placed on the power board.')
        text(35,820,'Two Ø9 mm openings pass around existing touch-module posts. Supports are proposed, not qualified.')
        text(35,855,'The large power PCB requires new thermal and airflow design; old cooling evidence does not transfer.')
        text(35,914,'NOT FOR FABRICATION · panel boards and bought-in modules are additional',True)
        path=OUT/('placement-'+side+'.png');im.save(path);artifacts.append(path)
        path=OUT/('placement-'+side+'.svg');path.write_text('\n'.join(svg+['</svg>'])+'\n');artifacts.append(path)
    (OUT/'drawing.json').write_text(json.dumps(dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in [Path(__file__),FOLDER/'capture.json',FOLDER/'placement.json']},artifact_sha256={q.name:sha(q) for q in artifacts},fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
