"""Draw the actual partial audio copper, conventional vias and preserved lands."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform
from hardware.fabrication.audit_candidate import sha

REPO=Path(__file__).resolve().parents[2]
OUT=REPO/"hardware/fabrication/staging/audio-main-supplies-06"
PAD_SOURCE=REPO/"hardware/fabrication/staging/audio-main-ground-02"
SOURCE=REPO/"hardware/fabrication/staging/audio-main-integration-04b"
COLORS={"ADC":"#55a6dc","CODEC":"#ba8ce8","DAC":"#55bfad","INPUT":"#a4bc67","OUTPUT":"#e6bc60","BYPASS":"#e68b80"}


def run():
    pcb=OUT/"audio_core.kicad_pcb"
    plan=json.loads((OUT/"plan.json").read_text())
    native=json.loads((OUT/"placement-native-review.json").read_text())
    assert all(sha(REPO/p)==h for p,h in native["source_sha256"].items())
    tree=read_sexpr(pcb.read_text())
    proof=json.loads((OUT/"routing-handoff.json").read_text())
    assert len(children(tree,"via")) == proof["vias"]
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
        d.text((60,67),"150 x 63 mm  |  131 local endpoints + 17 control pairs  |  200/200 ground pads  |  ROUTING INCOMPLETE",fill="#c4d0dc",font=font)
        d.text((60,97),"Actual pad lands and local copper. Codec land, remaining routing, power/return and installed receiving remain open.",fill="#c4d0dc",font=font)
        d.rectangle(rect((0,0,150,63)),fill="#1b2b35",outline="#d0d9df",width=2)
        missing=rect(plan["codec_missing_land_reserve_mm"])
        d.rectangle(missing,fill="#472c34",outline="#f49b95",width=2)
        d.multiline_text(((missing[0]+missing[2])/2,(missing[1]+missing[3])/2),"U201\nUNPLACED\nLAND DATA HOLD",fill="#f8c0b8",font=small,anchor="mm",align="center")
        for track in children(tree,"segment"):
            if first(track,"layer")[1] == face+".Cu":
                points = [xy(*map(float,first(track,key)[1:3])) for key in ("start","end")]
                d.line(points,fill="#dc9c59" if face=="F" else "#64b1d9",width=max(1,round(scale*float(first(track,"width")[1]))))
        for via in children(tree,"via"):
            vx,vy=map(float,first(via,"at")[1:3])
            radius=float(first(via,"size")[1])/2
            drill=float(first(via,"drill")[1])/2
            d.ellipse(rect((vx-radius,vy-radius,vx+radius,vy+radius)),fill="#d9ad62")
            d.ellipse(rect((vx-drill,vy-drill,vx+drill,vy+drill)),fill="#0b1118")
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
        d.text((60,808),"PARTIAL ROUTING / NOT FOR ORDER. Keepout is a design allocation, not an ESS land pattern or approved package limit.",font=font,fill="#f1b6a9")
        path=plots/("top.png" if face=="F" else "bottom.png")
        im.save(path,optimize=True)
        receipts[path.name]=sha(path)
    # The inner reference view uses actual stored native zone fill. Ground
    # voids and drilled/plated features remain visible at the same board scale.
    from shapely.geometry import Polygon

    im=Image.new("RGB",(1510,850),"#101923")
    d=ImageDraw.Draw(im)
    def xy(x,y):
        return 70+9*x,140+9*y
    font=ImageFont.load_default(size=17)
    large=ImageFont.load_default(size=26)
    d.text((60,25),"AC04 AUDIO MAIN / INNER 1 GROUND REFERENCE",font=large,fill="#e5edf4")
    d.text((60,67),"200/200 placed AGND pads connected to J701.2  |  Sensitive-node plane openings preserved",font=font,fill="#c4d0dc")
    d.text((60,97),"Stored native copper fill and actual lands/drills. Current, noise, stability and stack/process qualification remain open.",font=font,fill="#c4d0dc")
    d.rectangle((70,140,1420,707),fill="#1b2b35",outline="#d0d9df",width=2)
    for zone in children(tree,"zone"):
        if children(zone,"keepout"):
            continue
        for fill in children(zone,"filled_polygon"):
            pts=[tuple(map(float,p[1:3])) for p in children(first(fill,"pts"),"xy")]
            geometry=Polygon(pts).buffer(0)
            polygons=list(geometry.geoms) if geometry.geom_type=="MultiPolygon" else [geometry]
            for poly in polygons:
                d.polygon([xy(*p) for p in poly.exterior.coords],fill="#3f927b")
                for ring in poly.interiors:
                    d.polygon([xy(*p) for p in ring.coords],fill="#1b2b35")
    numbers={str(n[1]):str(n[2]) for n in children(tree,"net")}
    from hardware.fabrication.route_nf_surface import shape
    pads=json.loads((PAD_SOURCE/"native-pad-capture.json").read_text())["objects"]
    for pad in pads:
        polygons=pad["layers"].get("In1.Cu",[])
        if polygons:
            geometry=shape(polygons)
            geoms=list(geometry.geoms) if geometry.geom_type=="MultiPolygon" else [geometry]
            for poly in geoms:
                d.polygon([xy(*p) for p in poly.exterior.coords],fill="#75bba6" if pad["net"]=="AGND" else "#d9ad62")
        if any(pad["drill_mm"]):
            px,py=xy(*pad["position_mm"])
            radius=max(pad["drill_mm"])*4.5
            d.ellipse((px-radius,py-radius,px+radius,py+radius),fill="#0b1118")
    for via in children(tree,"via"):
        px,py=xy(*map(float,first(via,"at")[1:3]))
        radius=float(first(via,"size")[1])*4.5
        d.ellipse((px-radius,py-radius,px+radius,py+radius),fill="#75bba6" if numbers[str(first(via,"net")[1])]=="AGND" else "#d9ad62")
        radius=float(first(via,"drill")[1])*4.5
        d.ellipse((px-radius,py-radius,px+radius,py+radius),fill="#0b1118")
    d.text((60,744),f"Reference copper area: {proof['ground_plane_area_mm2']:.2f} mm2  |  {proof['vias']} conventional vias total",font=font,fill="#c4d0dc")
    d.text((60,780),f"Native geometry/ERC: 0  |  Missing codec footprint: 1  |  Remaining open connections: {native['uncapped_open_connections']}",font=font,fill="#c4d0dc")
    d.text((60,815),"DEVELOPMENT REFERENCE / NOT FOR ORDER. This view does not qualify return impedance or analog performance.",font=font,fill="#f1b6a9")
    path=plots/"ground.png"
    im.save(path,optimize=True)
    receipts[path.name]=sha(path)
    # Actual In2 distribution, with all new and retained conventional vias.
    im=Image.new("RGB",(1510,850),"#101923")
    d=ImageDraw.Draw(im)
    d.text((60,25),"AC04 AUDIO MAIN / INNER 2 SUPPLY ROUTING",font=large,fill="#e5edf4")
    d.text((60,67),f"161/161 placed supply/sense pads connected to source  |  0.60 mm distribution  |  {native['uncapped_open_connections']} opens remain",font=font,fill="#c4d0dc")
    d.text((60,97),"Actual copper. Capacity, drop, return impedance, noise, fault/thermal and process qualification remain open.",font=font,fill="#c4d0dc")
    d.rectangle((70,140,1420,707),fill="#1b2b35",outline="#d0d9df",width=2)
    palette={"P12":"#66b5ff","N12":"#ed88c1","P19":"#e3be61","N19":"#b6a0ef","V5_REG":"#70cc96", "5V_DIG":"#f2946c","V3V3_IO":"#e5de8a","/CODEC/A3V3":"#64d3d7","/CODEC/A4V5":"#bdc7ce"}
    for zone in children(tree,"zone"):
        if not children(zone,"keepout"):
            continue
        layers=first(zone,"layers")[1:] if children(zone,"layers") else [first(zone,"layer")[1]]
        if "In2.Cu" in layers:
            points=[tuple(map(float,p[1:3])) for p in children(first(first(zone,"polygon"),"pts"),"xy")]
            d.polygon([xy(*p) for p in points],fill="#342b35",outline="#765461")
    for track in children(tree,"segment"):
        if first(track,"layer")[1]=="In2.Cu":
            net=numbers[str(first(track,"net")[1])]
            points=[xy(*map(float,first(track,k)[1:3])) for k in ("start","end")]
            d.line(points,fill=palette[net],width=max(1,round(float(first(track,"width")[1])*9)))
    for pad in pads:
        ps=pad["layers"].get("In2.Cu",[])
        if ps:
            geometry=shape(ps)
            geoms=list(geometry.geoms) if geometry.geom_type=="MultiPolygon" else [geometry]
            for poly in geoms:
                d.polygon([xy(*p) for p in poly.exterior.coords],fill=palette.get(pad["net"],"#71838e"))
        if any(pad["drill_mm"]):
            px,py=xy(*pad["position_mm"])
            r=max(pad["drill_mm"])*4.5
            d.ellipse((px-r,py-r,px+r,py+r),fill="#0b1118")
    for via in children(tree,"via"):
        px,py=xy(*map(float,first(via,"at")[1:3]))
        r=float(first(via,"size")[1])*4.5
        d.ellipse((px-r,py-r,px+r,py+r),fill=palette.get(numbers[str(first(via,"net")[1])],"#71838e"))
        r=float(first(via,"drill")[1])*4.5
        d.ellipse((px-r,py-r,px+r,py+r),fill="#0b1118")
    for i,(net,color) in enumerate(palette.items()):
        xx=65+(i%5)*285
        yy=730+(i//5)*33
        d.rectangle((xx,yy,xx+15,yy+15),fill=color)
        d.text((xx+22,yy-2),net,font=font,fill="#e5edf4")
    d.text((60,812),"PLACED RAILS CONNECTED / NOT FOR ORDER. Codec land, signal routing and installed power/return qualification remain open.",font=font,fill="#f1b6a9")
    path=plots/"supplies.png"
    im.save(path,optimize=True)
    receipts[path.name]=sha(path)
    inputs=[Path(__file__),pcb,OUT/"plan.json",OUT/"placement-native-review.json",OUT/"routing-handoff.json",PAD_SOURCE/"native-pad-capture.json",SOURCE/"expected-circuit.json"]
    (plots/"render-receipt.json").write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        artifact_sha256=receipts,images_show_actual_native_lands_courtyards_tracks_and_vias=True,
        CAM_mask_stencil_and_assembly_qualification_inferred=False,fabrication_released=False),indent=2)+"\n")
    print("Rendered actual top/bottom and inner ground; codec unplaced; 267 remaining opens")


if __name__=="__main__":
    run()
