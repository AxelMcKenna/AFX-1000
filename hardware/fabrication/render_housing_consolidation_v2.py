"""HC01 figure: move the audio label out of the upper monitor overlay."""
import json
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from hardware.fabrication.assess_housing_consolidation import OUT

def render(d):
    im=Image.new('RGB',(1460,1120),'#f4f6f8')
    dr=ImageDraw.Draw(im)
    fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
    font=ImageFont.truetype(fontpath,18)
    small=ImageFont.truetype(fontpath,15)
    title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',26)
    dr.text((35,22),'AFX-1000 housing and board consolidation study',font=title,fill='#152530')
    dr.text((35,60),'334 × 188.4 × 45.6 mm outer shell • Latest PCB outlines • Conditional receiving geometry',font=font,fill='#425364')
    dr.text((35,91),'Complete fit unverified: missing current mounts, five boards’ component envelopes, harness and codec package.',font=font,fill='#9b3d32')
    palette=['#e4b47d','#7fc7bb','#d99199','#b2abd7','#bca0ce','#8eb4dd','#dec96d','#dec96d']
    scale=2.1
    def poly(coords,offset,fill):
        pts=[(offset[0]+x*scale,offset[1]+y*scale) for x,y in coords]
        dr.polygon(pts,fill=fill,outline='#263b4b',width=2)
    for row,off in enumerate([(35,175),(35,655)]):
        dr.rectangle([off[0],off[1],off[0]+334*scale,off[1]+188.4*scale],fill='white',outline='#526777',width=2)
        if row==0:
            dr.text((35,138),'Current allocation: eight main boards',font=title,fill='#152530')
            for i,(b,c) in enumerate(zip(d['boards'],palette),1):
                poly(b['polygon_world_mm'],off,c)
                p=Polygon(b['polygon_world_mm']).representative_point()
                if b['id']=='audio_main':
                    from shapely.geometry import Point
                    p=Point(145,75)
                dr.text((off[0]+p.x*scale-5,off[1]+p.y*scale-10),str(i),font=font,fill='#101820')
                label=f'{i}. '+b['id'].replace('_',' ').capitalize()
                if b['id']=='rail_monitor':label+=' (above audio)'
                if b['vertical']:label+=' (vertical)'
                dr.text((780,190+(i-1)*30),label,font=font,fill='#263b4b')
            dr.text((780,460),'Panel PCBs, touch module and wiring omitted',font=small,fill='#526777')
            dr.text((780,486),'from this main-board outline comparison.',font=small,fill='#526777')
            dr.text((780,527),'No nominal board-to-board slab collisions.',font=font,fill='#263b4b')
        else:
            dr.text((35,610),'First consolidation studies — not finished PCB designs',font=title,fill='#152530')
            for key,col in [('combined_signal_board','#7fc7bb'),('combined_power_and_disconnect','#d99199')]:
                s=d['consolidation_studies'][key]
                poly(s['polygon_world_mm'],off,col)
            lines=['Signal board: 268 × 63 mm','Audio + digital, common underside Z6.75 study.','0.55 mm floor / 0.59 mm monitor gap.','',
                   'Power/disconnect outline: 320 × 60.5 mm','Different existing heights and thermal interfaces.','Component fit has NOT been checked.','',
                   'Monitor, inlet, NF and fan functions still need','placement before a two-main-board design exists.']
            for i,line in enumerate(lines):dr.text((780,680+i*28),line,font=font if i in (0,4) else small,fill='#263b4b')
    dr.text((35,1080),'Screen only. No merged netlist, routed PCB, manufacturing outputs or fabrication approval.',font=font,fill='#9b3d32')
    im.save(OUT/'comparison-v2.png')


if __name__=="__main__":
    assert not (OUT/"comparison-v2.png").exists()
    render(json.loads((OUT/"review.json").read_text()))
