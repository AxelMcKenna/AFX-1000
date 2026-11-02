"""Draw the actual partial main-board lands/courtyards; never invent routes."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform
from hardware.fabrication.audit_candidate import sha

REPO=Path(__file__).resolve().parents[2]
OUT=REPO/"hardware/fabrication/staging/audio-main-placement-02"
SOURCE=REPO/"hardware/fabrication/staging/audio-main-integration-04b"
COLORS={"ADC":"#55a6dc","CODEC":"#ba8ce8","DAC":"#55bfad","INPUT":"#a4bc67","OUTPUT":"#e6bc60","BYPASS":"#e68b80"}


def run():
    pcb=OUT/"audio_core.kicad_pcb"
    plan=json.loads((OUT/"plan.json").read_text())
    native=json.loads((OUT/"placement-native-review.json").read_text())
    assert all(sha(REPO/p)==h for p,h in native["source_sha256"].items())
    tree=read_sexpr(pcb.read_text())
    assert not children(tree,"segment") and not children(tree,"via")
    expected=json.loads((SOURCE/"expected-circuit.json").read_text())
    plots=OUT/"plots"
    plots.mkdir(exist_ok=False)
    receipts={}
    for face in ("F","B"):
        im=Image.new("RGB",(1510,850),"#101923")
        d=ImageDraw.Draw(im)
        large=ImageFont.load_default(size=26)
        font=ImageFont.load_default(size=17)
        small=ImageFont.load_default(size=10)
        scale,left,top=9,70,140

        def xy(x,y):
            return left+scale*(150-x if face=="B" else x),top+scale*y

        def rect(b):
            x,y=xy(b[0],b[1])
            xx,yy=xy(b[2],b[3])
            return min(x,xx),min(y,yy),max(x,xx),max(y,yy)

        title="TOP" if face=="F" else "BOTTOM / VIEW FROM BELOW"
        d.text((60,25),"AC04 AUDIO MAIN / "+title,fill="#e5edf4",font=large)
        d.text((60,67),"150 x 63 mm  |  328 of 329 electrical parts placed  |  6 proposed mounts  |  NO ROUTING",fill="#c4d0dc",font=font)
        d.text((60,97),"Native footprint lands and courtyards. Codec land data, power/return and complete installed receiving remain open.",fill="#c4d0dc",font=font)
        d.rectangle(rect((0,0,150,63)),fill="#1b2b35",outline="#d0d9df",width=2)
        missing=rect(plan["codec_missing_land_reserve_mm"])
        d.rectangle(missing,fill="#472c34",outline="#f49b95",width=2)
        d.multiline_text(((missing[0]+missing[2])/2,(missing[1]+missing[3])/2),"U201\nUNPLACED\nLAND DATA HOLD",fill="#f8c0b8",font=small,anchor="mm",align="center")
        labels=[]
        for fp in children(tree,"footprint"):
            ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
            side=str(first(fp,"layer")[1]).split(".")[0]
            if side==face:
                b=courtyard(fp,face+".CrtYd")
                color=COLORS[expected[ref]["source_domain"]] if ref in expected else "#a9b8c4"
                d.rectangle(rect(b),outline=color,width=1)
                labels.append(((b[0]+b[2])/2,(b[1]+b[3])/2,ref))
            for pad in children(fp,"pad"):
                layer_names=first(pad,"layers")[1:]
                copper="*.Cu" in layer_names or face+".Cu" in layer_names
                if not copper:
                    continue
                px,py=transform(fp,first(pad,"at")[1:3])
                sx,sy=map(float,first(pad,"size")[1:3])
                at=first(fp,"at")
                angle=float(at[3]) if len(at)>3 else 0
                pat=first(pad,"at")
                angle+=float(pat[3]) if len(pat)>3 else 0
                assert abs(angle/90-round(angle/90))<1e-8
                if round(angle/90)%2:
                    sx,sy=sy,sx
                box=rect((px-sx/2,py-sy/2,px+sx/2,py+sy/2))
                shape=str(pad[3])
                fill="#d9ad62" if pad[2]!="np_thru_hole" else "#0b1118"
                if shape=="circle":
                    d.ellipse(box,fill=fill)
                elif shape in ("roundrect","oval"):
                    ratio=float(first(pad,"roundrect_rratio")[1]) if shape=="roundrect" else .5
                    d.rounded_rectangle(box,radius=min(sx,sy)*scale*ratio,fill=fill)
                else:
                    assert shape=="rect",("Unsupported actual pad shape",ref,shape)
                    d.rectangle(box,fill=fill)
                drill=children(pad,"drill")
                if drill:
                    assert len(drill[0])==2
                    diameter=float(drill[0][1])
                    d.ellipse(rect((px-diameter/2,py-diameter/2,px+diameter/2,py+diameter/2)),fill="#0b1118")
        for x,y,ref in labels:
            point=xy(x,y)
            b=d.textbbox(point,ref,font=small,anchor="mm")
            d.rectangle((b[0]-1,b[1],b[2]+1,b[3]),fill="#1b2b35")
            d.text(point,ref,font=small,fill="#eaf2f7",anchor="mm")
        for tick in range(0,151,10):
            x,y=xy(tick,0)
            d.text((x,y-18),str(tick),font=small,fill="#b9c7d2",anchor="mm")
        for i,(group,color) in enumerate(COLORS.items()):
            x=70+225*i
            d.rectangle((x,735,x+16,751),fill=color)
            d.text((x+24,733),group,font=font,fill="#e5edf4")
        d.text((60,775),f"Native geometry: {native['DRC_geometry_findings']}   Parity findings: {native['schematic_parity_findings']}   ERC: {native['ERC_findings']}   Opens: {native['uncapped_open_connections']}",font=font,fill="#c4d0dc")
        d.text((60,808),"PARTIAL PLACEMENT / NOT FOR ORDER. Keepout is a design allocation, not an ESS land pattern or approved package limit.",font=font,fill="#f1b6a9")
        path=plots/("top.png" if face=="F" else "bottom.png")
        im.save(path,optimize=True)
        receipts[path.name]=sha(path)
    inputs=[Path(__file__),pcb,OUT/"plan.json",OUT/"placement-native-review.json",SOURCE/"expected-circuit.json"]
    (plots/"render-receipt.json").write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        artifact_sha256=receipts,images_show_actual_native_lands_and_courtyards=True,
        CAM_mask_stencil_and_assembly_qualification_inferred=False,fabrication_released=False),indent=2)+"\n")
    print("Rendered actual top/bottom placement; codec unplaced; no copper routes")


if __name__=="__main__":
    run()
