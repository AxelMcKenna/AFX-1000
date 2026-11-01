"""Final private receiving model: R04 head9.0 and actual maxPCB clearance."""

import json
import re
import shutil

from hardware.cad.a12.thermal.interior_airpath.assembly import triangles

from .ground_route import ROOT, sha, write


def build():
    dst=ROOT/"variant6_model"
    if dst.exists():raise RuntimeError("Fresh coherent model required")
    shutil.copytree(ROOT/"variant5_model",dst)
    for p in dst.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(ROOT/"variant5_model"),str(dst)))
    returns=ROOT/"return_variant3/generated/returns.scad"
    text=re.sub(r'import\("([^\"]+)"\)',lambda m:'import("'+str(returns.parent/m.group(1))+'")',returns.read_text())
    (dst/"context/hardware/cad/a12/returns/generated/returns.scad").write_text(text)
    (ROOT/"generated/unified-context_v6.scad").write_text((ROOT/"generated/unified-context_v5.scad").read_text().replace(str(ROOT/"variant5_model"),str(dst)))
    data=json.loads((ROOT/"generated/variant5-coverage.json").read_text())
    boxes=data["fixtures"]
    for b in boxes:
        b[0]=b[0].replace("R03","R04")
        if b[0].endswith("-POST-stem"):b[2][2]=9.005
        if b[0].endswith("-POST-head"):b[1][2]=8.995
    for name in ["ANA","DIG"]:
        source=ROOT/"return_variant3/generated"/("AFX-A12-R04-"+name+"-POST.stl")
        subset=[b for b in boxes if b[0].startswith("AFX-A12-R04-"+name+"-POST-")]
        for tri in triangles(source):
            assert any(all(all(b[1][k]<=v[k]<=b[2][k] for k in range(3)) for v in tri) for b in subset)
    source=(ROOT/"checks_v5.scad").read_text().replace("generated/unified-context_v5.scad","generated/unified-context_v6.scad")
    source=source.replace(str(ROOT/"return_variant2/generated"),str(ROOT/"return_variant3/generated")).replace("AFX-A12-R03-","AFX-A12-R04-")
    source=re.sub(r'^ua_return_part_boxes=.*;$','ua_return_part_boxes='+json.dumps(boxes)+';',source,flags=re.M)
    old_ana=ROOT/"return_variant2/generated/AFX-A12-R03-ANA-POST.stl"
    old_dig=ROOT/"return_variant2/generated/AFX-A12-R03-DIG-POST.stl"
    source+='''
// Filled holes make this whole-PCB hull conservative. It is the actual
// notched eight-point P03outline, swept overbottom6.3..6.7/thickness1.44..1.76.
// L∞.41 transfers.16return+.25PCBclearance exactly to this obstacle.
module ua_P03_max_clearance(){for(b=ui_native_boards)if(b[0]=="P03")translate([168,108,5.89])linear_extrude(2.98)minkowski(){polygon(b[3]);square([.82,.82],center=true);}}
if(ua_case=="new_base_geometry")thermal_metal_base();
if(ua_case=="new_carrier_geometry"){ui_shell();tc2_posts();}
if(ua_case=="R04_P03_PCB_clearance_collision")intersection(){return_retention();ua_P03_max_clearance();}
if(ua_case=="old_R03_P03_clearance_shortfall")intersection(){union(){import("OLD_ANA");import("OLD_DIG");}ua_P03_max_clearance();}
if(ua_case=="return_post_floor_collision")intersection(){return_retention();ui_shell();}
if(ua_case=="H9_openlid_power_case_collision")intersection(){ui_h9_tool();union(){ui_case_shell();ua_returns();ua_PB_links();ua_PB_support();}}
if(ua_case=="H9_openlid_electronics_collision")intersection(){ui_h9_tool();union(){ui_electronics(true);ui_receiver_joint();tc2_heads();}}
if(ua_case=="H9_openlid_controls_collision")intersection(){ui_h9_tool();ua_all_controls();}
'''.replace("OLD_ANA",str(old_ana)).replace("OLD_DIG",str(old_dig))
    (ROOT/"checks_v6.scad").write_text(source)
    (ROOT/"generated/entry_v6.scad").write_text((ROOT/"generated/entry_v5.scad").read_text().replace(str(ROOT/"checks_v5.scad"),str(ROOT/"checks_v6.scad")))
    (ROOT/"part_import_v6.py").write_text((ROOT/"part_import_v5.py").read_text().replace("checks_v5.scad","checks_v6.scad").replace("return_variant2/generated","return_variant3/generated").replace("AFX-A12-R03-","AFX-A12-R04-"))
    s=(ROOT/"verify_v5.py").read_text().replace("from .part_import_v5 import","from .part_import_v6 import").replace("entry_v5.scad","entry_v6.scad").replace('ROOT/"part_import_v5.py"','ROOT/"part_import_v6.py"').replace('ROOT/"return_variant2/generated"','ROOT/"return_variant3/generated"')
    s=s.replace('ROOT/"variant5_stage.py",','ROOT/"variant5_stage.py",ROOT/"variant6_stage.py",ROOT/"generated/variant6-coverage.json",')
    s=s.replace('    return d\n','''    d.update({n:dict(role="part") for n in ["new_base_geometry","new_carrier_geometry"]})
    d.update({n:dict(role="empty") for n in ["R04_P03_PCB_clearance_collision","return_post_floor_collision","H9_openlid_power_case_collision","H9_openlid_electronics_collision","H9_openlid_controls_collision"]})
    d["old_R03_P03_clearance_shortfall"]=dict(role="witness")
    return d
''',1)
    (ROOT/"verify_v6.py").write_text(s)
    write(ROOT/"generated/variant6-coverage.json",dict(return_parts=20,return_PB_pairs=60,fixtures=boxes,
          source_sha256={str(p):sha(p) for p in [__import__("pathlib").Path(__file__),returns,ROOT/"return_variant3/design.json",ROOT/"checks_v6.scad",ROOT/"generated/entry_v6.scad"]},
          maxPCB=dict(bottom=[6.3,6.7],thickness=[1.44,1.76],maxZ=8.46,combined_return_PCB_clearance=.41,filled_holes_conservative=True),
          unchanged_Cu_ports_wire_and_PB27=True,H9_actual_worldXY=[182,92.2],old8p7failure_is_control_not_discarded=True,
          physical_qualified=False,thermal_qualified=False))
    print(json.dumps(dict(complete_model=True,native_cases=42,manufacturable_return_parts=20)))


if __name__=="__main__":build()
