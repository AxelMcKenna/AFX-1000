"""NEW orthogonal ANA26 positive link; preserve source wires/failed variants."""

import json
import re
import shutil

from .ground_route import ROOT, sha, write


def build():
    dst=ROOT/"variant4_model"
    if dst.exists():raise RuntimeError("Fresh variant destination required")
    positive=ROOT/"positive_variant26/generated"
    proof=json.loads((positive/"geometry.json").read_text())
    assert len(proof["parts"])==32 and proof["source_and_destination_ports_unchanged"]
    shutil.copytree(ROOT/"variant2_model",dst)
    for p in dst.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(ROOT/"variant2_model"),str(dst)).replace(str(ROOT/"inputs/PB02-generated/positive-links.stl"),str(positive/"positive-links.stl")))
    context=(ROOT/"generated/unified-context_v2.scad").read_text().replace(str(ROOT/"variant2_model"),str(dst))
    (ROOT/"generated/unified-context_v4.scad").write_text(context)
    # Actual DIGCu is the union of five source-defined convex segment lofts
    # and four disks before the internal holes. PrimitiveAABB union contains
    # ALL filled Cu material, and filling holes makes it conservative.
    text=(ROOT/"return_variant2/generated/returns.scad").read_text()
    line=next(l for l in text.splitlines() if l.startswith("module return_dig_bar"))
    segments=json.loads(re.search(r'for\(v=(\[.*?\])\)polyhedron',line).group(1))
    circles=json.loads(re.search(r'for\(q=(\[.*?\])\)translate',line).group(1))
    small=[]
    for i,vertices in enumerate(segments):
        small.append(["DIG-segment"+str(i),[min(p[k] for p in vertices)-.005 for k in range(3)],[max(p[k] for p in vertices)+.005 for k in range(3)]])
    for i,(x,y,z,d,h) in enumerate(circles):
        small.append(["DIG-disk"+str(i),[x-d/2-.005,y-d/2-.005,z-.005],[x+d/2+.005,y+d/2+.005,z+h+.005]])
    cov=json.loads((ROOT/"generated/variant2-coverage.json").read_text())
    boxes=[[p["name"],p["low"],p["high"]] for p in cov["parts"] if p["name"]!="AFX-A12-R03-DIG-BAR"]+small
    assert len(segments)==5 and len(circles)==4 and len(boxes)==28
    source=(ROOT/"checks_v3.scad").read_text().replace("generated/unified-context_v2.scad","generated/unified-context_v4.scad")
    source=re.sub(r'^ua_return_part_boxes=.*;$','ua_return_part_boxes='+json.dumps(boxes)+';',source,flags=re.M)
    source+='''
module ua_power_bodies(){ui_boxes([for(b=ui_native_boxes)if(!in_list(b[0],["P03_J24","P03_J23","E28_J10","E28_J11"]))b]);ui_source_joint();ui_cylinders();ui_boxes(ui_inherited_envelopes);ui_rear_bodies();tc2_components();}
if(ua_case=="PB26_components_collision")intersection(){ua_expand(.35){ua_PB_links();ua_PB_support();}union(){ui_PCBS();ua_power_bodies();}}
if(ua_case=="PB26_controls_collision")intersection(){ua_expand(.35){ua_PB_links();ua_PB_support();}ua_all_controls();}
if(ua_case=="PB26_case_collision")intersection(){union(){ua_expand(.35)ua_PB_links();intersection(){ua_expand(.35)ua_PB_support();translate([-100,-100,2.80002])cube([600,600,200]);}}union(){ui_shell();ui_lid();rear_panel();}}
if(ua_case=="PB26_return_control")intersection(){ua_pb("ANA-CU");translate([170.9,133.0,26.3])cube([.2,.2,.2]);}
'''
    (ROOT/"checks_v4.scad").write_text(source)
    entry=(ROOT/"generated/entry_v3.scad").read_text().replace(str(ROOT/"checks_v3.scad"),str(ROOT/"checks_v4.scad")).replace(str(ROOT/"inputs/PB02-generated"),str(positive))
    (ROOT/"generated/entry_v4.scad").write_text(entry)
    write(ROOT/"generated/variant4-coverage.json",dict(source_sha256={str(p):sha(p) for p in [__import__("pathlib").Path(__file__),ROOT/"return_variant2/generated/returns.scad",positive/"geometry.json",ROOT/"checks_v4.scad",ROOT/"generated/entry_v4.scad"]},
        actual_return_parts=20,source_pairs=60,native_union_cases=3,source_DIG_segments=segments,source_DIG_disks=circles,
        actual_fixture_boxes=boxes,omitted_material=False,internal_holes_conservatively_filled=True,
        additional_geometry_reserve_mm=.005,combined_margin_preserved_mm=.51,
        positive_port_endpoints_and_groundwire_unchanged=True,all_previous_failure_evidence_unchanged=True,
        physical_qualified=False,thermal_qualified=False))
    s=(ROOT/"part_import.py").read_text().replace("checks_v3.scad","checks_v4.scad")
    (ROOT/"part_import_v4.py").write_text(s)
    s=(ROOT/"verify_v3.py").read_text().replace('from .part_import import','from .part_import_v4 import').replace('entry_v3.scad','entry_v4.scad').replace('ROOT/"part_import.py"','ROOT/"part_import_v4.py"')
    s=s.replace('ROOT/"variant2_stage.py",','ROOT/"variant2_stage.py",ROOT/"variant4_stage.py",ROOT/"generated/variant4-coverage.json",')
    s=s.replace('ROOT/"inputs/PB02-generated"','ROOT/"positive_variant26/generated"')
    s=s.replace('    return d\n','    d.update({n:dict(role="empty") for n in ["PB26_components_collision","PB26_controls_collision","PB26_case_collision"]})\n    d["PB26_return_control"]=dict(role="control",expected_volume=.008)\n    return d\n',1)
    (ROOT/"verify_v4.py").write_text(s)
    print(json.dumps(dict(derived=True,return_fixture_boxes=28,source_pairs=60,groundmodel_unchanged=True)))


if __name__=="__main__":build()
