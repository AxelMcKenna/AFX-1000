"""AP01: source-bound physical partition and conditional receiving screen.

This fixes allocations for subsequent PCB work. It is not a complete native
assembly renewal or a supplier/process acceptance. All dimensions are mm.
"""

import argparse
import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize

from hardware.cad.a11.generate import schedule
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
OUT = ROOT / "staging/assembly-layout-01"
DIGITAL = ROOT / "staging/digital-core-placement-03"
SCENE = REPO / "hardware/cad/a12/enclosure_growth/integration/generated/scene.json"
GROUPS = {
    "audio_main": ["input_range", "adc_driver", "converter", "dac_receiver", "output_stage", "sequenced_bypass"],
    "digital_core": ["processor_carrier", "control_inputs", "led_driver"],
    **{r: [r] for r in ("power_supply", "input_protection", "rail_disconnect", "rail_monitor", "negative_startup_protection", "fan_health_protection")},
}
POSES = {"power_supply": [168,108,6.5], "input_protection": [248,1.4,7.9],
         "rail_disconnect": [8,108.5,5], "rail_monitor": [36,32,24],
         "negative_startup_protection": [172,180.5,3.5], "fan_health_protection": [14,180.5,3.5]}


def outline(path):
    tree = read_sexpr(path.read_text())
    assert not any(first(n,"layer")[1] == "Edge.Cuts" for tag in ("gr_arc","gr_circle","gr_rect","gr_poly") for n in children(tree,tag))
    lines = [LineString([tuple(map(float,first(n,k)[1:3])) for k in ("start","end")])
             for n in children(tree,"gr_line") if first(n,"layer")[1] == "Edge.Cuts"]
    polygons = list(polygonize(lines))
    assert len(polygons) == 1 and polygons[0].is_valid and not polygons[0].interiors
    return tree, polygons[0]


def intersects(a,b):
    return all(a[i] < b[i]+b[i+3]-1e-8 and b[i] < a[i]+a[i+3]-1e-8 for i in range(3))


def component_boxes(tree, datum, digital):
    boxes = []
    for fp in children(tree,"footprint"):
        ref = next(p[2] for p in children(fp,"property") if p[1] == "Reference")
        side = str(first(fp,"layer")[1]).split(".")[0]
        x,y,xx,yy = courtyard(fp,side+".CrtYd")
        # Explicit installed receiving limits, not manufacturer guarantees.
        height = (17.2 if ref == "U1001" else 13.5 if ref.startswith("J") else
                  2.31 if ref.startswith("H") else 3.2 if digital else 2.5 if ref == "C50" else 2.0)
        z = datum[2]-.2-height if side == "B" else datum[2]-.2+1.44
        dz = height+.4 if side == "B" else height+.4+.32
        boxes.append([ref, x+datum[0],y+datum[1],z,xx-x,yy-y,dz,side,height])
    return boxes


def calculate():
    scope = json.loads((ROOT/"scope.json").read_text())
    roles = {r["role"]:r for r in scope["roles"]}
    members = [r for group in GROUPS.values() for r in group]
    assert len(members) == len(set(members)) == 15 and set(members) == set(roles)
    paths = [Path(__file__),SCENE,DIGITAL/"construction.json",DIGITAL/"digital_core.kicad_pcb",
             DIGITAL/"placement-native-review.json",REPO/"hardware/cad/a12/trill_front_bay/README.md",
             REPO/"hardware/cad/a11/generated/controls.csv",REPO/"hardware/cad/a11/mechanisms.scad"]
    digital = json.loads((DIGITAL/"construction.json").read_text())
    native = json.loads((DIGITAL/"placement-native-review.json").read_text())
    assert all(sha(REPO/p)==h for p,h in digital["source_sha256"].items())
    assert all(sha(REPO/p)==h for p,h in native["source_sha256"].items())
    assert all(sha(DIGITAL/p)==h for p,h in native["raw_report_sha256"].items())
    assert native["DRC_geometry_findings"] == native["schematic_parity_findings"] == native["ERC_findings"] == 0
    assert native["DRC_ignored_checks"] == native["ERC_ignored_checks"] == []
    boards = [dict(id="audio_main", roles=GROUPS["audio_main"], datum=[30,42,6.5],
                   polygon=[[30,42],[180,42],[180,105],[30,105]], thickness=1.6,
                   source=None, state="allocation; six-role schematic integration and placement unfinished"),
              dict(id="digital_core",roles=GROUPS["digital_core"],datum=digital["enclosure_datum_mm"],
                   polygon=[[x+184,y+44] for x,y in digital["outlines_local_mm"]],thickness=1.6,
                   source=str((DIGITAL/"digital_core.kicad_pcb").relative_to(REPO)),state="138 parts placed; unrouted")]
    trees = {}
    for role, datum in POSES.items():
        path = (REPO/roles[role]["source"]).with_suffix(".kicad_pcb")
        paths.append(path)
        tree, poly = outline(path)
        trees[role] = tree
        x0,y0,x1,y1 = poly.bounds
        vertical = role in ("negative_startup_protection","fan_health_protection")
        thickness = float(first(first(tree,"general"),"thickness")[1])
        projected = ([[datum[0],datum[1]-thickness],[datum[0]+x1-x0,datum[1]-thickness],
                      [datum[0]+x1-x0,datum[1]],[datum[0],datum[1]]]
                     if vertical else [[x-x0+datum[0],y-y0+datum[1]] for x,y in list(poly.exterior.coords)[:-1]])
        boards.append(dict(id=role,roles=[role],datum=datum,polygon=projected,thickness=thickness,
                           vertical=vertical,vertical_height=(y1-y0 if vertical else None),
                           source=str(path.relative_to(REPO)),state="current profile captured; whole-board installed renewal pending"))
    scene = json.loads(SCENE.read_text())
    # Retain controls and rear receiving context; explicitly remove superseded electronics.
    retained = [r for r in scene["inherited_envelopes"] if not any(r[0].startswith(p) for p in ("e19_","e20_","e18_","e06_"))]
    for b in schedule()[0]:
        angle = math.radians(b[7])
        half = 5*(abs(math.cos(angle))+abs(math.sin(angle)))
        retained.append(["switch_"+b[0],b[5]-half,b[6]-half,30.3,2*half,2*half,9])
        for i,(dx,dy) in enumerate(b[8]):
            x = b[5]+dx*math.cos(angle)-dy*math.sin(angle)
            y = b[6]+dx*math.sin(angle)+dy*math.cos(angle)
            retained.append([f"holder_{b[0]}_{i}",x-2.1,y-2.1,33.2,4.2,4.2,9])
    # Includes removal of the previous carrier/LED/hub bosses as a new floor requirement.
    retained.append(["release_bracket_and_motion_XY_keepout",303,66,0,26,39,45.6])
    digital_tree = read_sexpr((DIGITAL/"digital_core.kicad_pcb").read_text())
    boxes = {"digital_core":component_boxes(digital_tree,[184,44,7],True),
             "rail_monitor":component_boxes(trees["rail_monitor"],[36,32,24],False)}
    collisions = [[group,b[0],o[0]] for group,rows in boxes.items() for b in rows for o in retained if intersects(b[1:7],o[1:7])]
    floor_hits = [[group,b[0]] for group,rows in boxes.items() for b in rows if b[3]<2.8]
    # Re-evaluate actual E28 outline, not its 156x60 bounding rectangle.
    e28 = Polygon(next(b["polygon"] for b in boards if b["id"]=="rail_disconnect"))
    post_clearances = [dict(centre=[x,y],nominal_radius=3.6,
                            nominal_edge_gap_to_current_E28=Point(x,y).distance(e28)-3.6)
                       for x,y in ((130.0871,168.922),(93.0871,168.9352))]
    assert not collisions and not floor_hits
    assert all(p["nominal_edge_gap_to_current_E28"]>0 for p in post_clearances)
    return dict(revision="AP01",source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        case_outer_mm=[334,188.4,45.6], functional_roles=15,functional_PCB_allocations=8,
        allocation_groups=GROUPS,boards=boards,
        additional_panel_PCBS=[r for r in scene["other_boards"] if r[0] in ("meter_board","bpm_board","settings_board","release_select_board")],
        panel_LED_emitter_PCB_layout_and_final_board_count_unfinished=True,
        touch_module=dict(datum=[82,158,20],size=[53.848,21.844,1.6],component_height_allocation=6.4,tail_allocation=3),
        declared_component_boxes=boxes,retained_context_boxes=retained,
        conditional_component_context_collisions=collisions,conditional_floor_collisions=floor_hits,
        source_matched_digital_parts=138,digital_open_connections=native["uncapped_open_connections"],
        current_E28_touch_post_nominal_clearances=post_clearances,
        digital_receive_limits=dict(pcb_Z_tolerance=.2,pcb_thickness=[1.44,1.76],seed_above_face=17.2,
            header_wire_mating_above_face=13.5,other_component_installed_height=3.2,
            THT_tail_including_solder_below_face=3.2,
            all_limits_are_unapproved_receiving_requirements=True),
        monitor_receive_limits=dict(datum=[36,32,24],pcb_Z_tolerance=.2,pcb_thickness=[1.44,1.76],
            header_mating_above_face=13.5,C50_above_face=2.5,other_parts_above_face=2.0,
            THT_tail_limit=2,all_limits_are_unapproved_receiving_requirements=True),
        audio_requirements=dict(size=[150,63,1.6],datum=[30,42,6.5],parts_before_six_role_port_consolidation=342,
            upper_monitor_projection=[36,32,116,102],shared_monitor_support_centres=[[40,98],[112,98]],
            shared_support_clearance_holes_and_copper_keepouts_required=True,
            parts_over_13_mm_under_monitor_header_tails_prohibited=True,
            tall_output_films_and_connectors_outside_upper_monitor_projection=True),
        rejected_digital_trials={"01":"global net slash spelling; 199 parity findings; five categories default-ignored",
                                "02":"native geometry/parity clean; J3005 overlaps retained inlet J2 mate reserve"},
        next_required_work=["Consolidate six audio roles and place their actual components in the allocation",
            "Route combined digital board and renew native/parity checks",
            "Rebuild floor bosses, monitor supports and full native assembly using all current sources",
            "Design actual harness/strain relief, qualify receiving limits and renew power/thermal/return analysis"],
        role_partition_for_layout=True,complete_physical_partition_and_receiving=False,
        entire_current_assembly_collision_free=False,manufacturing_process_accepted=False,fabrication_released=False)


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
    text(35,55,"AP01 · current source profiles · placement allocation, not fabrication approval")
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
        "Monitor: 80 × 70 mm above audio", "", "Digital: 138 parts placed", "466 open connections; no routing", "", "Digital geometry / parity / ERC: 0",
        "All native categories enabled", "", "Purple outlines: underside parts", "Pale outlines: top-side parts", "", "Height limits are conditional.", "Complete assembly fit remains open."]):
        text(1065,100+28*i,line)
    text(35,695,"Fixed for layout: audio on the left; combined digital on the right; touch module keeps the front bay.")
    text(35,729,"Next: complete the six-role audio integration, route digital, then rebuild the floor/supports and renew the full assembly.")
    text(35,774,"NOT FOR ORDER · Full current-component, harness, process and thermal acceptance remains unfinished.")
    svg.append('</svg>')
    im.save(OUT/"arrangement.png")
    (OUT/"arrangement.svg").write_text("\n".join(svg)+"\n")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=calculate()
    if args.check:
        assert result==json.loads((OUT/"allocation.json").read_text())
    else:
        OUT.mkdir(exist_ok=False)
        (OUT/"allocation.json").write_text(json.dumps(result,indent=2)+"\n")
        render(result)
    print("AP01: 15 roles in eight functional PCB allocations; digital/monitor conditional control-context screen clear; complete fit/release remains open")
