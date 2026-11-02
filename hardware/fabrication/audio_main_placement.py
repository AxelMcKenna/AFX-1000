"""Place the known AC04 parts inside AP01; leave the ESS land explicitly absent.

Plans use actual captured lands, local feedback/bypass constraints and the
declared upper-board receiving envelope. No unassigned codec pad is invented.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_layout import mount
from hardware.fabrication.digital_core_layout import pad_box

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/"hardware/fabrication"
SOURCE=ROOT/"staging/audio-main-integration-04b"
OUT=ROOT/"staging/audio-main-placement-01"
DATUM=(30,42,6.5)
MOUNTS=[(4,4),(146,4),(4,59),(146,59),(10,56),(82,56)]
CODEC_RESERVE=(54,22,70,38)
FILMS={"C107","C121","C321","C322","C401","C403",*[f"C{i}" for i in (501,502,503,504,513,514,515,516)]}
TALL_FILMS={f"C{i}" for i in (501,502,503,504,513,514,515,516)}
FIXED={
    "K601":(13,13,0,"F"),"K602":(25,12,0,"F"),"K401":(37,16,0,"F"),"K503":(128,29.5,0,"F"),
    "U401":(30,32,0,"F"),"U101":(45,24,0,"F"),"U102":(45,36,0,"F"),
    "U104":(43,50,90,"F"),"U107":(28,48,0,"F"),"U105":(38,5,0,"F"),"U106":(51,5,0,"F"),
    "U301":(78,25,0,"F"),"U302":(78,36,0,"F"),"U303":(102,31,0,"B"),
    "U304":(98,32,0,"F"),"U305":(98,42,0,"F"),"U501":(112.25,26,0,"F"),"U502":(109,37,0,"F"),
    "U602":(10,42,0,"F"),"U606":(69,44,0,"B"),"U608":(65,54,0,"F"),
    "Y201":(61,16,0,"F"),"U207":(74,6,0,"F"),
    "C107":(49,57.25,180,"F"),"C121":(37,42.75,0,"F"),"C401":(18,23,0,"F"),"C403":(18,33,0,"F"),
    "C321":(108,13,0,"F"),"C322":(108,44.75,0,"F"),
    "C501":(90,13,0,"F"),"C513":(99,13,0,"F"),"C502":(117,13,0,"F"),"C514":(126,13,0,"F"),
    "C503":(90,52,0,"F"),"C515":(99,52,0,"F"),"C504":(117,52,0,"F"),"C516":(126,52,0,"F"),
    "J203":(136.5,26.25,0,"F"),"J402":(145,50,90,"F"),"J403":(23,58,0,"F"),
    "J602":(3,38,0,"F"),"J603":(125,4,90,"F"),"J606":(17,49,90,"F"),
    "J607":(5,27,90,"F"),"J608":(5,33,90,"F"),"J701":(138,18.5,0,"F"),"J702":(18,40,0,"F"),
}
# C/ref, owning IC, supply pin. These are receiving/path construction limits.
BYPASS=[
    ("C113","U101","3"),("C114","U101","6"),("C127","U102","3"),("C128","U102","6"),
    ("C129","U103","8"),("C130","U103","4"),("C131","U104","4"),("C132","U104","11"),
    ("C135","U107","3"),("C136","U108","6"),
    *[(f"C{220+i}",f"U{204+i}","4" if i in (0,1,2,4) else "14" if i==3 else "5") for i in range(6)],
    ("C226","Y201","4"),("C230","U210","5"),("C231","U211","5"),("C232","U212","5"),
    *[(f"C{311+2*i}",f"U{301+i}","8") for i in range(4)],
    *[(f"C{312+2*i}",f"U{301+i}","4") for i in range(4)],
    ("C323","U305","8"),("C324","U305","4"),("C405","U401","8"),("C406","U401","4"),
    ("C505","U501","8"),("C506","U501","4"),("C507","U502","8"),("C508","U502","4"),
    ("C602","U601","5"),("C603","U602","14"),("C604","U603","8"),("C605","U604","6"),
    ("C606","U605","6"),("C610","U606","14"),("C611","U607","5"),("C612","U608","14"),
]
FEEDBACK=[
    *[(f"R{r}","U101",4.0) for r in (101,102,103,104,105,106)],
    *[(f"R{r}","U102",4.0) for r in (117,118,119,120,121,122)],
    *[(r,"U101" if r in ("C101","C102") else "U102",3.0) for r in ("C101","C102","C115","C116")],
    *[(r,"U301",4.0) for r in ("R301","R302","C301","C302")],
    *[(r,"U302",4.0) for r in ("R313","R314","C306","C307")],
    *[(r,"U303",4.0) for r in ("R307","R319","C303","C308")],
    *[(r,"U304",4.0) for r in ("R310","R322","C304","C309")],
    *[(r,"U401",4.0) for r in ("R405","R406","R412","R413")],
    *[(r,"U501",4.0) for r in ("R501","R502","R505","R506")],
    *[(r,"U502",4.0) for r in ("R509","R510","R513","R514")],
    ("C108","U105",4.0),("C122","U106",4.0),
    ("C109","U105",5.0),("C110","U105",5.0),("C123","U106",5.0),("C124","U106",5.0),
    ("C107","U104",6.0),("C121","U104",6.0),("R112","U104",4.0),("R128","U104",4.0),
    ("R213","Y201",3.5),
]


def overlap(a,b,gap=0):
    return a[0]<b[2]+gap-1e-8 and a[2]>b[0]-gap+1e-8 and a[1]<b[3]+gap-1e-8 and a[3]>b[1]-gap+1e-8


class Space:
    def __init__(self):
        self.bins=defaultdict(list)

    @staticmethod
    def keys(bbox):
        return [(x,y) for x in range(math.floor(bbox[0]/5),math.floor(bbox[2]/5)+1)
                for y in range(math.floor(bbox[1]/5),math.floor(bbox[3]/5)+1)]

    def add(self,side,bbox,gap,ref):
        item=(bbox,gap,ref)
        expanded=[bbox[0]-gap,bbox[1]-gap,bbox[2]+gap,bbox[3]+gap]
        for key in self.keys(expanded):
            self.bins[(side,*key)].append(item)

    def clear(self,side,bbox):
        for key in self.keys(bbox):
            for b,gap,_ in self.bins.get((side,*key),[]):
                if overlap(bbox,b,gap):
                    return False
        return True

    def remove(self,ref):
        for key,items in list(self.bins.items()):
            self.bins[key]=[p for p in items if p[2]!=ref and not p[2].startswith(ref+" ")]


def allocated_height(ref):
    if ref in TALL_FILMS:
        return 19.0
    if ref in FILMS:
        return 14.5
    if ref.startswith("J"):
        return 13.5
    if ref.startswith("K"):
        return 5.6
    if ref in ("C509","C510","C511","C512"):
        return 3.0
    return 2.5


def plan():
    from hardware.fabrication.audit_audio_main import HANDOFF, check

    assert check()==json.loads(HANDOFF.read_text())
    assert not OUT.exists()
    parts,pins=netlist(SOURCE/"netlist.xml")
    components={r:dict(ref=r,value=p.findtext("value"),footprint=p.findtext("footprint"),nets=pins[r],
                       source=p.findtext("datasheet") or "",mpn=p.findtext("value")) for r,p in parts.items() if r!="U201"}
    assert len(components)==328 and not parts["U201"].findtext("footprint")
    nets={n:i+1 for i,n in enumerate(sorted({n for ps in pins.values() for n in ps.values()}))}
    features={}
    for ref,part in components.items():
        lib,name=part["footprint"].split(":")
        path=SOURCE/"libraries"/(lib+".pretty")/(name+".kicad_mod")
        for side in ("F","B"):
            for angle in (0,90,180,270):
                fp=placed_footprint(part,(0,0,angle,side),path,nets,origin=(0,0),namespace="AFX:AC04:placement:")
                b=courtyard(fp,side+".CrtYd")
                extra=.5 if ref in FILMS or ref.startswith("J") else 0
                b=[b[0]-extra,b[1]-extra,b[2]+extra,b[3]+extra]
                padcoords={str(p[1]):transform(fp,first(p,"at")[1:3]) for p in children(fp,"pad") if str(p[1])}
                holes=[pad_box(fp,p,.5) for p in children(fp,"pad") if p[2] in ("thru_hole","np_thru_hole")]
                features[(ref,side,angle)]=(b,padcoords,holes)
    space=Space()
    for side in ("F","B"):
        space.add(side,list(CODEC_RESERVE),.5,"U201 missing-land reserve")
        for x,y in MOUNTS:
            space.add(side,[x-3.6,y-3.6,x+3.6,y+3.6],.15,"mount")
    # Current E13 THT solder reserves above the main board.
    scope=json.loads((ROOT/"scope.json").read_text())
    monitor=(REPO/next(r["source"] for r in scope["roles"] if r["role"]=="rail_monitor")).with_suffix(".kicad_pcb")
    upper=read_sexpr(monitor.read_text())
    assert all(first(fp,"layer")[1]=="F.Cu" for fp in children(upper,"footprint"))
    tails=[]
    for fp in children(upper,"footprint"):
        for p in children(fp,"pad"):
            if p[2]=="thru_hole":
                b=pad_box(fp,p,.5)
                tails.append([b[0]+6,b[1]-10,b[2]+6,b[3]-10])
    poses,bounds,cells={},{},[]

    def legal(ref,side,b,holes):
        if b[0]<.5-1e-8 or b[1]<.5-1e-8 or b[2]>149.5+1e-8 or b[3]>62.5+1e-8:
            return False
        h=allocated_height(ref)
        if side=="B" and (h>2.5 or DATUM[2]-.2-h<3.3):
            return False
        if side=="F":
            top=DATUM[2]+.2+1.76+h
            if top+.3>23.8 and overlap(b,[6,-10,86,60]):
                return False
            if top+.3>21.8 and any(overlap(b,t) for t in tails):
                return False
        if not space.clear(side,b):
            return False
        other="B" if side=="F" else "F"
        return all(space.clear(other,hole) for hole in holes)

    def install(ref,pose):
        x,y,angle,side=pose
        b,_,holes=features[(ref,side,angle)]
        b=[b[0]+x,b[1]+y,b[2]+x,b[3]+y]
        holes=[[v[0]+x,v[1]+y,v[2]+x,v[3]+y] for v in holes]
        assert legal(ref,side,b,holes),("Illegal fixed placement",ref,pose,b)
        poses[ref]=list(pose)
        bounds[ref]=b
        space.add(side,b,.3,ref)
        other="B" if side=="F" else "F"
        for hole in holes:
            space.add(other,hole,0,ref+" THT/plastic-tail reserve")

    for ref,pose in sorted(FIXED.items(),key=lambda item:item[1][3]=="B"):
        install(ref,pose)

    def search(ref,target,side_options,anchors=None,limit=None,cell_margin=0):
        choices=[]
        for side in side_options:
            for angle in (0,90,180,270):
                b,padcoords,holes=features[(ref,side,angle)]
                step=.25 if anchors else .5
                radius=(limit+5) if anchors else 200
                xmin,xmax=max(1,target[0]-radius),min(149,target[0]+radius)
                ymin,ymax=max(1,target[1]-radius),min(62,target[1]+radius)
                for ix in range(math.floor(xmin/step),math.ceil(xmax/step)+1):
                    x=ix*step
                    for iy in range(math.floor(ymin/step),math.ceil(ymax/step)+1):
                        y=iy*step
                        if anchors:
                            distances=[math.dist((x+padcoords[p][0],y+padcoords[p][1]),xy) for p,xy in anchors]
                            if max(distances)>limit+1e-8:
                                continue
                            score=max(distances)+.15*sum(distances)
                        else:
                            score=math.dist((x+(b[0]+b[2])/2,y+(b[1]+b[3])/2),target)
                        score+=.75 if side=="B" else 0
                        choices.append((score,x,y,angle,side))
        for _,x,y,angle,side in sorted(choices):
            b,_,holes=features[(ref,side,angle)]
            bb=[b[0]+x,b[1]+y,b[2]+x,b[3]+y]
            hh=[[v[0]+x,v[1]+y,v[2]+x,v[3]+y] for v in holes]
            reserve=[bb[0]-cell_margin,bb[1]-cell_margin,bb[2]+cell_margin,bb[3]+cell_margin]
            if legal(ref,side,reserve,hh):
                install(ref,(x,y,angle,side))
                return
        nearby={r:poses[r] for r,b in bounds.items() if math.dist(((b[0]+b[2])/2,(b[1]+b[3])/2),target)<9}
        raise AssertionError(("No placement with declared constraints",ref,target,limit,nearby))

    # Place all remaining ICs before their local passive networks.
    targets={"ADC":(36,41),"CODEC":(74,14),"DAC":(85,33),"INPUT":(25,29),"OUTPUT":(118,34),"BYPASS":(18,44)}
    expected=json.loads((SOURCE/"expected-circuit.json").read_text())
    remaining=[r for r in components if r not in poses and r.startswith("U")]
    remaining.sort(key=lambda r:-(features[(r,"F",0)][0][2]-features[(r,"F",0)][0][0])*(features[(r,"F",0)][0][3]-features[(r,"F",0)][0][1]))
    for ref in remaining:
        search(ref,targets[expected[ref]["source_domain"]],("F",),cell_margin=2.5)

    critical=[]
    for ref,owner,limit in FEEDBACK:
        owner_pose=poses[owner]
        xy=features[(owner,owner_pose[3],owner_pose[2])][1]
        anchors=[]
        for p,n in pins[ref].items():
            if n=="AGND":
                continue
            matches=[op for op,on in pins[owner].items() if on==n]
            if matches:
                op=matches[0]
                anchors.append((p,(xy[op][0]+owner_pose[0],xy[op][1]+owner_pose[1])))
        assert anchors,(ref,owner)
        side=owner_pose[3]
        kind="servo_integrator" if ref in ("C107","C121","R112","R128") else "clock_series" if ref=="R213" else "feedback_or_pump"
        critical.append((ref,owner,side,anchors,limit,kind))
    for ref,owner,pin in BYPASS:
        owner_pose=poses[owner]
        px,py=features[(owner,owner_pose[3],owner_pose[2])][1][pin]
        assert pins[ref]["1"]==pins[owner][pin],("Wrong local bypass owner",ref,owner,pin)
        critical.append((ref,owner,owner_pose[3],[("1",(px+owner_pose[0],py+owner_pose[1]))],3.5,"supply_bypass"))
    # Solve each complete local network jointly. The closest position for one
    # parallel part can leave its peer without a legal position.
    groups=defaultdict(list)
    for spec in critical:
        groups[spec[1]].append(spec)
    search_stats={}
    for owner,specs in sorted(groups.items(),key=lambda item:(-sum(v[0] not in poses for v in item[1]),item[0])):
        options={}
        for ref,_,side,anchors,limit,_ in specs:
            if ref in poses:
                continue
            target=[sum(p[i] for _,p in anchors)/len(anchors) for i in (0,1)]
            choices=[]
            for angle in (0,90,180,270):
                b,pc,holes=features[(ref,side,angle)]
                for ix in range(max(2,math.floor((target[0]-limit-5)*4)),min(598,math.ceil((target[0]+limit+5)*4))+1):
                    x=ix/4
                    for iy in range(max(2,math.floor((target[1]-limit-5)*4)),min(250,math.ceil((target[1]+limit+5)*4))+1):
                        y=iy/4
                        ds=[math.dist((x+pc[p][0],y+pc[p][1]),xy) for p,xy in anchors]
                        if max(ds)>limit+1e-8:
                            continue
                        bb=[b[0]+x,b[1]+y,b[2]+x,b[3]+y]
                        hh=[[v[0]+x,v[1]+y,v[2]+x,v[3]+y] for v in holes]
                        if legal(ref,side,bb,hh):
                            choices.append((max(ds)+.15*sum(ds),(x,y,angle,side),bb,hh))
            options[ref]=sorted(choices,key=lambda v:(v[0],v[1]))
        stats=dict(candidate_trials=0,maximum_depth=0,candidate_counts={r:len(v) for r,v in options.items()})

        def pack(pending,depth=0):
            stats["maximum_depth"]=max(depth,stats["maximum_depth"])
            if not pending:
                return True
            available={r:[c for c in options[r] if legal(r,c[1][3],c[2],c[3])] for r in pending}
            ref=min(pending,key=lambda r:(len(available[r]),r))
            if not available[ref]:
                return False
            for _,pose,_,_ in available[ref]:
                stats["candidate_trials"]+=1
                assert stats["candidate_trials"]<=100000,("Local search budget",owner,stats)
                install(ref,pose)
                if pack(pending-{ref},depth+1):
                    return True
                space.remove(ref)
                del poses[ref],bounds[ref]
            return False

        assert pack(set(options)),("No joint local placement with unchanged limits",owner,stats)
        search_stats[owner]=stats
    for ref,owner,side,anchors,limit,kind in critical:
        pose=poses[ref]
        coords=features[(ref,pose[3],pose[2])][1]
        assert pose[3]==side
        assert all(math.dist((coords[p][0]+pose[0],coords[p][1]+pose[1]),xy)<=limit+1e-8 for p,xy in anchors)
        cells.append(dict(ref=ref,owner=owner,kind=kind,side=side,limit_mm=limit,
            terminals=[dict(part_pin=p,owner_position_mm=xy,actual_displacement_mm=math.dist((coords[p][0]+pose[0],coords[p][1]+pose[1]),xy)) for p,xy in anchors]))
    for ref in sorted(set(components)-poses.keys(),key=lambda r:-(features[(r,"F",0)][0][2]-features[(r,"F",0)][0][0])*(features[(r,"F",0)][0][3]-features[(r,"F",0)][0][1])):
        weight=[]
        for other,p in poses.items():
            shared=set(pins[ref].values())&set(pins[other].values())
            shared-={"AGND","P19","N19","P12","N12","V5_REG","5V_DIG","V3V3_IO"}
            if shared:
                b=bounds[other]
                weight.append(((b[0]+b[2])/2,(b[1]+b[3])/2,len(shared)))
        target=targets[expected[ref]["source_domain"]]
        if weight:
            target=[sum(w[i]*w[2] for w in weight)/sum(w[2] for w in weight) for i in (0,1)]
        sides=("F",) if ref.startswith(("J","K","Q")) or allocated_height(ref)>2.5 else ("F","B")
        search(ref,target,sides)
    paths=[Path(__file__),HANDOFF,SOURCE/"netlist.xml",SOURCE/"expected-circuit.json",monitor]
    OUT.mkdir()
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        electrical_parts_in_schematic=329,placed_electrical_parts=328,unplaced_refs=["U201"],
        case_datum_mm=DATUM,board_size_mm=[150,63,1.6],codec_missing_land_reserve_mm=CODEC_RESERVE,
        mount_centres_mm=MOUNTS,poses=poses,expanded_receiving_bounds_mm=bounds,local_cells=cells,
        joint_local_search=search_stats,
        declared_receiving_height_mm={r:allocated_height(r) for r in poses},
        pcb_Z_tolerance_mm=.2,pcb_thickness_interval_mm=[1.44,1.76],upper_monitor_PCB_min_Z_mm=23.8,
        upper_monitor_THT_tail_min_Z_mm=21.8,opposite_face_solder_XY_expansion_mm=.5,
        component_same_face_gap_mm=.3,film_and_header_secondary_XY_clearance_mm=.5,
        full_connector_mates_and_wire_bends_included=False,
        all_height_mating_and_process_limits_are_unapproved_requirements=True,
        codec_pad_dependent_passives_must_be_repositioned_after_approved_land=True,
        codec_land_assigned=False,physical_ADC_force_sense_stars_verified=False,
        feedback_path_return_parasitic_stability_and_noise_qualified=False,routed=False,fabrication_released=False)
    (OUT/"plan.json").write_text(json.dumps(record,indent=2)+"\n")
    print(f"Planned {len(poses)} parts and {len(cells)} local cells; U201 deliberately unplaced")


def build():
    record=json.loads((OUT/"plan.json").read_text())
    assert all(sha(REPO/p)==h for p,h in record["source_sha256"].items())
    assert not (OUT/"audio_core.kicad_pcb").exists()
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_pro",".kicad_sch",".kicad_sym") or p.name in ("sym-lib-table","fp-lib-table"):
            shutil.copyfile(p,OUT/p.name)
    shutil.copytree(SOURCE/"libraries",OUT/"libraries")
    own=OUT/"libraries/AFX_Audio_Main.pretty"
    own.mkdir()
    (own/"M2_Clearance.kicad_mod").write_text(sexpr(mount())+"\n")
    table=read_sexpr((OUT/"fp-lib-table").read_text())
    table.append(read_sexpr('(lib (name "AFX_Audio_Main") (type "KiCad") (uri "${KIPRJMOD}/libraries/AFX_Audio_Main.pretty") (options "") (descr "Proposed shared supports"))'))
    (OUT/"fp-lib-table").write_text(sexpr(table)+"\n")
    parts,pins=netlist(SOURCE/"netlist.xml")
    raw={n.attrib["name"].lstrip("/"):n.attrib["name"] for n in ET.parse(SOURCE/"netlist.xml").findall("nets/net")}
    nets={n:i+1 for i,n in enumerate(sorted(raw))}
    board=read_sexpr('''(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
       (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
       (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (44 "Edge.Cuts" user)
       (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 ""))''')
    board.extend([a("net"),code,raw[name]] for name,code in nets.items())
    for ref,pose in record["poses"].items():
        part=dict(ref=ref,value=parts[ref].findtext("value"),footprint=parts[ref].findtext("footprint"),nets=pins[ref],source="",mpn=parts[ref].findtext("value"))
        lib,name=part["footprint"].split(":")
        fp=placed_footprint(part,pose,OUT/"libraries"/(lib+".pretty")/(name+".kicad_mod"),nets,origin=(0,0),namespace="AFX:AC04:placement:")
        for p in children(fp,"pad"):
            for n in children(p,"net"):
                n[2]=raw[str(n[2]).lstrip("/")]
        board.append(fp)
    for i,(x,y) in enumerate(MOUNTS,1):
        part=dict(ref="H"+str(i),value="M2_SHARED_SUPPORT" if i>4 else "M2_CLEARANCE",nets={},footprint="AFX_Audio_Main:M2_Clearance",source="",mpn="")
        board.append(placed_footprint(part,(x,y,0,"F"),own/"M2_Clearance.kicad_mod",nets,origin=(0,0),namespace="AFX:AC04:placement:"))
    points=[(0,0),(150,0),(150,63),(0,63)]
    for start,end in zip(points,points[1:]+points[:1]):
        board.append(read_sexpr(f'(gr_line (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'))
    x,y,xx,yy=CODEC_RESERVE
    board.append(read_sexpr(f'''(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu")
      (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .2)
      (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints not_allowed))
      (fill (thermal_gap .5) (thermal_bridge_width .5))
      (polygon (pts (xy {x} {y}) (xy {xx} {y}) (xy {xx} {yy}) (xy {x} {yy}))))'''))
    board.append(read_sexpr('(gr_text "U201 DATA HOLD - NO LAND" (at 62 30 0) (layer "Dwgs.User") (effects (font (size 1 1))))'))
    (OUT/"audio_core.kicad_pcb").write_text(sexpr(board)+"\n")
    profile=json.loads((SOURCE/"audio_core.kicad_pro").read_text())
    profile.update(board=dict(design_settings=dict(rules=dict(min_clearance=.2,min_track_width=.2,
        min_copper_edge_clearance=.5,min_hole_clearance=.25,min_through_hole_diameter=.3,min_via_annular_width=.15),
        rule_severities={k:"error" for k in ("missing_courtyard","track_not_centered_on_via","tuning_profile_track_geometries","footprint_filters_mismatch","footprint_type_mismatch")})),
        net_settings=dict(classes=[dict(name="Default",clearance=.2,track_width=.2,via_diameter=.65,via_drill=.3)]))
    (OUT/"audio_core.kicad_pro").write_text(json.dumps(profile,indent=2)+"\n")
    (OUT/"applied-placement.py.txt").write_text(Path(__file__).read_text())
    print("Built partial audio main PCB; 328 original electrical parts / six mounts; codec footprint missing")


def review():
    assert sys.platform=="linux", "Mac CAD remains disabled"
    assert not (OUT/"placement-native-review.json").exists()
    inputs=[p for p in OUT.iterdir() if p.suffix in (".kicad_pcb",".kicad_sch",".kicad_sym",".kicad_pro") or p.name in ("plan.json","sym-lib-table","fp-lib-table")]
    hashes={str(p.relative_to(REPO)):sha(p) for p in inputs}
    commands=[]
    for label,options in (
        ("netlist",["sch","export","netlist","--format","kicadxml","-o",str(OUT/"native-netlist.xml"),str(OUT/"audio_core.kicad_sch")]),
        ("erc",["sch","erc","--severity-all","--format","json","-o",str(OUT/"erc.json"),str(OUT/"audio_core.kicad_sch")]),
        ("drc",["pcb","drc","--all-track-errors","--schematic-parity","--severity-all","--format","json","-o",str(OUT/"drc.json"),str(OUT/"audio_core.kicad_pcb")]),
    ):
        cmd=["kicad-cli",*options]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        (OUT/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=cmd,returncode=p.returncode))
        assert p.returncode==0,(label,p.stdout,p.stderr)
    import pcbnew

    b=pcbnew.LoadBoard(str(OUT/"audio_core.kicad_pcb"))
    b.BuildConnectivity()
    b.GetConnectivity().RecalculateRatsnest()
    drc,erc=[json.loads((OUT/p).read_text()) for p in ("drc.json","erc.json")]
    assert all(sha(REPO/p)==h for p,h in hashes.items())
    record=dict(source_sha256=hashes,complete_native_commands=commands,native_version=pcbnew.GetBuildVersion(),
        DRC_geometry_findings=len(drc["violations"]),schematic_parity_findings=len(drc["schematic_parity"]),
        uncapped_open_connections=b.GetConnectivity().GetUnconnectedCount(False),
        ERC_findings=sum(len(s["violations"]) for s in erc["sheets"]),
        DRC_ignored_checks=drc["ignored_checks"],ERC_ignored_checks=erc["ignored_checks"],
        raw_report_sha256={p:sha(OUT/p) for p in ("drc.json","erc.json","native-netlist.xml")},
        unplaced_refs=["U201"],routed=False,receiving_approved=False,fabrication_released=False)
    (OUT/"placement-native-review.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in ("source_sha256","complete_native_commands","raw_report_sha256")}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("plan","build","review"))
    args=parser.parse_args()
    {"plan":plan,"build":build,"review":review}[args.action]()
