"""Functional placement of the original eight-window E13 circuit on a new PCB."""

import argparse
import json
import math
import re
import shutil
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.bypass_layout import mount

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1]/"hardware/electronics/rail_monitor"
STOCK = ROOT/"staging/rail-monitor-stock"
SIZE = (80,70)
FIXED = {"U1":(20,15,0),"U2":(50,15,0),"U3":(20,44,0),"U4":(50,44,0),
    "U5":(35,31,0),"U6":(38,60,0),"U7":(60,61,0),"U8":(59,31,0),
    "U9":(70,12,0),"U10":(70,27,0),"U11":(70,42,0),"U12":(70,57,0),
    "J1":(77,22,0),"J2":(4,16,0),"J3":(4,48,0),"J4":(64,66,90)}
MOUNTS = ((4,4),(76,4),(4,66),(76,66))
GAP = .25


def bounds(tree):
    points = []
    for item in tree:
        if not isinstance(item,list) or not item or not children(item,"layer") or first(item,"layer")[1] != "F.CrtYd":
            continue
        if item[0] == "fp_rect":
            points.extend(first(item,k)[1:3] for k in ("start","end"))
        elif item[0] == "fp_line":
            points.extend(first(item,k)[1:3] for k in ("start","end"))
    assert points,"Expected a stock rectangular courtyard"
    xy = [tuple(map(float,p)) for p in points]
    return min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)


def transform(box,pose):
    x,y,t = pose
    c,s = math.cos(math.radians(t)),math.sin(math.radians(t))
    pts = [(x+u*c+v*s,y-u*s+v*c) for u,v in ((box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3]))]
    return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)


def collide(a,b):
    return not (a[2]+GAP <= b[0] or b[2]+GAP <= a[0] or a[3]+GAP <= b[1] or b[3]+GAP <= a[1])


def owner(part):
    note = part.get("note","")
    local = re.search(r"Local bypass for (U\d+)",note)
    if local:
        return local.group(1)
    nets = {p["net"] for p in part["pins"] if p.get("net")}
    if any(n.endswith("_FB") for n in nets):
        return "U5"
    for prefix,which in (("NBIAS_L_","U3"),("NBIAS_R_","U3"),("P19_","U1"),("N19_","U1"),
                         ("P12_","U2"),("N12_","U2"),("V5_REG_","U4"),("5V_DIG_","U4")):
        if any(n.startswith(prefix) for n in nets):
            return which
    if "STARTUP_CT" in nets or "V5_COARSE_SENSE" in nets:
        return "U7"
    if "LOCAL_RAIL_OK" in nets:
        return "U8"
    if "PRE_ANALOG_OK" in nets:
        return "U12"
    return "U6"


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label",default="rail-monitor-placement-01")
    args = parser.parse_args()
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    output = ROOT/"staging"/args.label
    assert not output.exists()
    parts = json.loads((SOURCE/"components.json").read_text())
    by_ref = {p["ref"]:p for p in parts}
    assert len(parts) == 181 and set(FIXED) <= set(by_ref)
    _,pins = netlist(SOURCE/"generated/netlist.xml")
    libraries,boxes = {},{}
    for part in parts:
        library,name = part["footprint"].split(":")
        path = STOCK/(library+".pretty")/(name+".kicad_mod")
        libraries[part["ref"]] = path
        boxes[part["ref"]] = bounds(read_sexpr(path.read_text()))
    poses = dict(FIXED)
    occupied = [transform(boxes[r],pose) for r,pose in poses.items()]
    occupied += [(x-2.75,y-2.75,x+2.75,y+2.75) for x,y in MOUNTS]
    assert not any(collide(a,b) for i,a in enumerate(occupied) for b in occupied[i+1:]),"Fixed reservations overlap"
    grid = [(x*.5,y*.5) for x in range(6,155) for y in range(6,135)]
    rows = []
    passives = [p for p in parts if p["ref"] not in poses]
    passives.sort(key=lambda p:(0 if "Local bypass for" in p.get("note","") else 1,
        0 if any((n.get("net") or "").endswith("_FB") for n in p["pins"]) else 1,
        int(owner(p)[1:]),p["ref"][0],int(p["ref"][1:])))
    for part in passives:
        ref = part["ref"]
        target = owner(part)
        tx,ty,_ = poses[target]
        if "Local bypass for" in part.get("note",""):
            # The actual power pad, rather than the package centre, anchors
            # the bypass placement target. No loop qualification is inferred.
            chip = read_sexpr(libraries[target].read_text())
            number = next(p["number"] for p in by_ref[target]["pins"] if p.get("kind") == "power_in" and p.get("net") in ("V5_REG","V3V3_IO"))
            pad = next(p for p in children(chip,"pad") if str(p[1]) == number)
            px,py = map(float,first(pad,"at")[1:3])
            tx,ty = tx+px,ty+py
        choices = sorted(grid,key=lambda xy:((xy[0]-tx)**2+(xy[1]-ty)**2,xy))
        selected = None
        for x,y in choices:
            for angle in (0,90,180):
                pose = (x,y,angle)
                region = transform(boxes[ref],pose)
                if region[0] < .75 or region[1] < .75 or region[2] > SIZE[0]-.75 or region[3] > SIZE[1]-.75:
                    continue
                if not any(collide(region,other) for other in occupied):
                    selected = pose,region
                    break
            if selected:
                break
        assert selected,ref
        pose,region = selected
        poses[ref] = pose
        occupied.append(region)
        rows.append(dict(ref=ref,owner=target,target_mm=[tx,ty],pose=pose,courtyard_bbox_mm=region,
                         centre_to_target_mm=math.dist(pose[:2],(tx,ty))))
    assert set(poses) == set(by_ref)
    output.mkdir()
    shutil.copytree(STOCK,output/"libraries")
    (output/"libraries/capture.json").unlink()
    local = output/"libraries/AFX_Package.pretty"
    local.mkdir()
    (local/"M2_Clearance.kicad_mod").write_text(sexpr(mount())+"\n")
    fpt = read_sexpr((SOURCE/"fp-lib-table").read_text())
    for lib in children(fpt,"lib"):
        first(lib,"uri")[1] = "${KIPRJMOD}/libraries/"+str(first(lib,"name")[1])+".pretty"
    fpt.append(read_sexpr('(lib (name "AFX_Package") (type "KiCad") (uri "${KIPRJMOD}/libraries/AFX_Package.pretty") (options "") (descr "Own M2 clearance only"))'))
    (output/"fp-lib-table").write_text(sexpr(fpt)+"\n")
    sym = read_sexpr((SOURCE/"sym-lib-table").read_text())
    inputs = [SOURCE/p for p in ("components.json","rail_monitor.kicad_sch","generated/netlist.xml","fp-lib-table","sym-lib-table")]
    for lib in children(sym,"lib"):
        path = Path(str(first(lib,"uri")[1]).replace("${KIPRJMOD}",str(SOURCE)))
        shutil.copyfile(path,output/"libraries"/path.name)
        inputs.append(path)
        first(lib,"uri")[1] = "${KIPRJMOD}/libraries/"+path.name
    (output/"sym-lib-table").write_text(sexpr(sym)+"\n")
    for name in ("rail_monitor.kicad_sch","generated/netlist.xml"):
        shutil.copyfile(SOURCE/name,output/Path(name).name)
    board = read_sexpr('''(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
      (35 "F.Paste" user) (34 "B.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
      (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user)
      (48 "B.Fab" user) (49 "F.Fab" user)) (setup (pad_to_mask_clearance 0)) (net 0 ""))''')
    nets = {n:i+1 for i,n in enumerate(sorted({n for p in pins.values() for n in p.values()}))}
    board.extend([a("net"),i,n if n.startswith("unconnected-") else "/"+n] for n,i in nets.items())
    for part in parts:
        ref = part["ref"]
        actual = dict(part,value=part["part"],mpn=part["part"],source=part.get("source",""),nets=pins[ref])
        fp = placed_footprint(actual,(*poses[ref],"F"),libraries[ref],nets,origin=(0,0),namespace="AFX:E13:PCB01:")
        for pad in children(fp,"pad"):
            if children(pad,"net") and str(first(pad,"net")[-1]).startswith("/unconnected-"):
                first(pad,"net")[-1] = str(first(pad,"net")[-1])[1:]
        board.append(fp)
    for i,(x,y) in enumerate(MOUNTS,1):
        fp = mount()
        fp.append([a("at"),x,y])
        next(p for p in children(fp,"property") if p[1] == "Reference")[2] = "H"+str(i)
        board.append(fp)
    for start,end in (((0,0),(80,0)),((80,0),(80,70)),((80,70),(0,70)),((0,70),(0,0))):
        board.append(read_sexpr(f'(gr_line (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'))
    for layer,net,rect in (("In1.Cu","AGND",(.5,.5,79.5,69.5)),("In2.Cu","V5_REG",(.5,.5,62.5,69.5)),("In2.Cu","V3V3_IO",(63.5,.5,79.5,69.5))):
        x,y,u,v = rect
        board.append(read_sexpr(f'''(zone (net {nets[net]}) (net_name "/{net}") (layer "{layer}") (hatch edge .5)
          (connect_pads (clearance .2)) (min_thickness .2) (fill yes (thermal_gap .25) (thermal_bridge_width .3))
          (polygon (pts (xy {x} {y}) (xy {u} {y}) (xy {u} {v}) (xy {x} {v}))))'''))
    (output/"rail_monitor.kicad_pcb").write_text(sexpr(board)+"\n")
    profile = dict(meta=dict(filename="rail_monitor.kicad_pro",version=1),board=dict(design_settings=dict(rules=dict(
        min_clearance=.2,min_track_width=.2,min_copper_edge_clearance=.5,min_hole_clearance=.25,min_through_hole_diameter=.3,min_via_annular_width=.15))),
        net_settings=dict(classes=[dict(name="Default",clearance=.2,track_width=.2,via_diameter=.65,via_drill=.3)]))
    (output/"rail_monitor.kicad_pro").write_text(json.dumps(profile,indent=2)+"\n")
    (output/"construction.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        recipe_sha256=sha(Path(__file__)),board_size_mm=[80,70,1.6],poses=poses,passive_placement=rows,
        four_original_headers_and_all181_original_parts=True,all_pin_nets_values_and_FPID_unchanged=True,
        local_bypass_loops_and_full_sense_geometry_qualified=False,precision_parts_selected=False,
        native_checks_pending=True,mechanical_allocation_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Placed181 circuit parts and4 mounts on80x70mm; native circuit/geometry checks pending")


if __name__ == "__main__":
    run()
