"""Independently screen common signal-board height; render HC01 without CAD."""
import itertools
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box

from hardware.fabrication.assess_housing_consolidation import REPO, OUT, AP, digest, overlaps, prism, calculate


def run():
    saved = json.loads((OUT/'review.json').read_text())
    assert json.loads(json.dumps(calculate())) == saved, 'Current source/geometry replay differs'
    ap = json.loads(AP.read_text())
    context = [prism(r[0],'context',[r[1],r[2],r[1]+r[4],r[2]+r[5]],r[3],r[3]+r[6],'context') for r in ap['retained_context_boxes']]
    for r in context:
        if r['name'].startswith(('input_rca_','input_ts_','output_rca_','output_ts_')):
            r['z'] = [v+.8 for v in r['z']]
    original = saved['declared_receivers'] + saved['declared_THT_tail_receivers']
    monitor = Polygon(next(b for b in saved['boards'] if b['id']=='rail_monitor')['polygon_world_mm'])
    rows=[]
    for z in [6.5,6.75,7.0]:
        receivers=json.loads(json.dumps(original))
        for r in receivers:
            if r['owner'] in ('audio_main','digital_core'):
                delta=z-(6.5 if r['owner']=='audio_main' else 7)
                r['z']=[v+delta for v in r['z']]
        ctx_hits=[[r['owner'],r['name'],c['name']] for r in receivers for c in context if overlaps(r,c,.25)]
        mutual=[[a['owner'],a['name'],b['owner'],b['name']] for a,b in itertools.combinations(receivers,2) if a['owner']!=b['owner'] and overlaps(a,b,.25)]
        gaps=[(23.8-r['z'][1],r['name']) for r in receivers if r['owner']=='audio_main' and r['kind']=='declared_component_receiver' and r['z'][0]>z and box(*r['xy']).intersects(monitor)]
        floor=min((r['z'][0]-2.8,r['owner'],r['name']) for r in receivers)
        positive=[r['name'] for r in receivers if r['owner']=='audio_main' and r['z'][0]>z and r['z'][1]>22.0 and box(*r['xy']).intersection(monitor).area>1e-8]
        rows.append(dict(common_board_underside_Z_mm=z,minimum_floor_gap_mm=floor[0],floor_limiting_receiver=list(floor[1:]),
            minimum_audio_to_monitor_board_gap_mm=min(gaps)[0],monitor_limiting_receivers=[r for g,r in gaps if abs(g-min(gaps)[0])<1e-8],
            context_intersections_at_0p25_margin=ctx_hits,cross_board_receiver_intersections_at_0p25_margin=mutual,
            deliberate_monitor_lowered_to_Z22_detected_intersections=positive,
            all_listed_receiving_checks_pass=not ctx_hits and not mutual and floor[0]>=.25-1e-8 and min(gaps)[0]>=.3-1e-8))
        assert positive, 'Deliberate monitor intrusion did not trigger'
    result=dict(source_sha256={str(p.relative_to(REPO)):digest(p) for p in [Path(__file__),OUT/'review.json',AP]},
                exact_HC01_source_and_geometry_replay_pass=True,common_height_sensitivity=rows,
                preferred_study_height_mm=6.75,preferred_height_is_approved=False,
                limited_clearance_check_only=True,native_full_assembly_rebuilt=False,complete_fit_verified=False)
    target=OUT/'height-study.json'
    assert not target.exists()
    target.write_text(json.dumps(result,indent=2)+'\n')
    render(saved)
    return result


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
    im.save(OUT/'comparison.png')


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
