"""AP04: renew conditional digital receiving against the partial signal-routing PCB."""
import html,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hardware.fabrication import assembly_layout as base
from hardware.fabrication.assembly_layout import component_boxes,intersects
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_digital_signals import check as check_digital,OUT as DIGITAL
from hardware.electronics.common.sexpr import read_sexpr
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=ROOT/'staging/assembly-layout-04'

def calculate():
    result=base.calculate()
    evidence=check_digital();handoff=DIGITAL/'handoff.json'
    assert evidence==json.loads(handoff.read_text())
    scope=json.loads((ROOT/'scope.json').read_text())
    assert REPO/scope['shared_digital_core']['source']==DIGITAL/'digital_core.kicad_pro'
    pcb=DIGITAL/'digital_core.kicad_pcb'
    boxes=component_boxes(read_sexpr(pcb.read_text()),[184,44,7],True)
    result['declared_component_boxes']['digital_core']=boxes
    result['conditional_component_context_collisions']=[[group,b[0],o[0]] for group,rows in result['declared_component_boxes'].items() for b in rows for o in result['retained_context_boxes'] if intersects(b[1:7],o[1:7])]
    result['conditional_floor_collisions']=[[group,b[0]] for group,rows in result['declared_component_boxes'].items() for b in rows if b[3]<2.8]
    assert not result['conditional_component_context_collisions'] and not result['conditional_floor_collisions']
    board=next(b for b in result['boards'] if b['id']=='digital_core')
    board.update(source=str(pcb.relative_to(REPO)),state='138 parts; power and SD/audio nets connected; 143 opens; SD timing and electrical/thermal qualification unfinished')
    next(b for b in result['boards'] if b['id']=='audio_main')['state']='329-part integration; partial main-board placement/local routing; codec and global routing unfinished'
    result.update(revision='AP04',digital_open_connections=143,digital_local_connections=39,
        next_required_work=['Complete main audio routing and missing codec package/interface receiving',
        'Revise digital LED/control escapes and SD length/via matching, then qualify power/return/noise and thermal paths',
        'Complete NF routing and current power/fault interfaces',
        'Rebuild floor bosses and supports; renew the full assembly, harness and power/thermal/return analysis'])
    result['source_sha256'].update({str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),pcb,handoff,ROOT/'audit_digital_signals.py']})
    return result

def render(result):
    width,height,scale,ox,oy = 1400,850,3,35,92
    im = Image.new("RGB",(width,height),"#111820")
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",16)
    title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf",25)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#111820"/>']
    def text(x,y,s,large=False):
        draw.text((x,y),s,font=title if large else font,fill="#e6edf2")
        svg.append(f'<text x="{x}" y="{y+20 if large else y+15}" font-family="Arial,sans-serif" font-size="{25 if large else 16}" fill="#e6edf2">{html.escape(s)}</text>')
    def poly(points,color):
        pts=[(ox+x*scale,oy+y*scale) for x,y in points]
        draw.polygon(pts,fill=color,outline="#f0f5f8",width=2)
        svg.append(f'<polygon points="{" ".join(f"{x:.4f},{y:.4f}" for x,y in pts)}" fill="{color}" stroke="#f0f5f8" stroke-width="2"/>')
    text(35,20,"AFX-1000 / proposed PCB arrangement",True)
    text(35,55,"AP04 · current source profiles · placement allocation, not fabrication approval")
    poly([[0,0],[334,0],[334,188.4],[0,188.4]],"#273340")
    palette={"audio_main":"#945e2e","digital_core":"#167568","rail_monitor":"#376daa",
             "power_supply":"#87484d","rail_disconnect":"#794866","input_protection":"#5e678d",
             "negative_startup_protection":"#c49a3c","fan_health_protection":"#c49a3c"}
    for b in result["boards"]:
        poly(b["polygon"],palette[b["id"]])
    for b in result["additional_panel_PCBS"]:
        _,x,y,z,dx,dy,*_ = b
        poly([[x,y],[x+dx,y],[x+dx,y+dy],[x,y+dy]],"#64727e")
    poly([[82,158],[135.848,158],[135.848,179.844],[82,179.844]],"#64727e")
    # Actual digital placement courtyards, by side. No imaginary routing shown.
    for b in result["declared_component_boxes"]["digital_core"]:
        _,x,y,z,dx,dy,dz,side,*_=b
        pts=[(ox+x*scale,oy+y*scale),(ox+(x+dx)*scale,oy+(y+dy)*scale)]
        col="#c9eadc" if side=="F" else "#b79ee1"
        draw.rectangle((*pts[0],*pts[1]),outline=col,width=1)
        svg.append(f'<rect x="{pts[0][0]:.4f}" y="{pts[0][1]:.4f}" width="{dx*scale:.4f}" height="{dy*scale:.4f}" fill="none" stroke="{col}"/>')
    text(ox+33*scale,oy+64*scale,"AUDIO MAIN")
    text(ox+39*scale,oy+34*scale,"MONITOR (upper)")
    text(ox+192*scale,oy+105*scale,"DIGITAL CORE")
    text(ox+188*scale,oy+122*scale,"POWER")
    text(ox+20*scale,oy+118*scale,"DISCONNECT")
    text(ox+85*scale,oy+166*scale,"TOUCH")
    for i,line in enumerate([
        "334 × 188.4 × 45.6 mm case", "8 functional PCB allocations", "Plus panel PCBs and touch module", "", "Audio: 150 × 63 mm allocation", "Digital: notched 114 × 60 mm",
        "Monitor: 80 × 70 mm above audio", "", "Digital: power/ground connected", "143 opens; 201 supply/ground pads", "", "Digital geometry / parity / ERC: 0",
        "All native categories enabled", "", "Purple outlines: underside parts", "Pale outlines: top-side parts", "", "Height limits are conditional.", "Complete assembly fit remains open."]):
        text(1065,100+28*i,line)
    text(35,695,"Fixed for layout: audio on the left; combined digital on the right; touch module keeps the front bay.")
    text(35,729,"Next: finish audio and digital routing; correct SD matching; renew supports and full assembly checks.")
    text(35,774,"NOT FOR ORDER · Full current-component, harness, process and thermal acceptance remains unfinished.")
    svg.append('</svg>')
    im.save(OUT/"arrangement.png")
    (OUT/"arrangement.svg").write_text("\n".join(svg)+"\n")


if __name__=='__main__':
    result=calculate();OUT.mkdir(exist_ok=False)
    (OUT/'allocation.json').write_text(json.dumps(result,indent=2)+'\n')
    render(result)
    print('AP04: current digital poses clear conditional component context; complete assembly receiving remains open')
