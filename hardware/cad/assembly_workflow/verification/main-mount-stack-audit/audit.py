"""Audit the retained prototype BOM against its actual floor-pocket datums."""
import json,re
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    capture=w.ROOT/'hardware/cad/two_board_print_01/captured.scad'
    shell=w.ROOT/'hardware/cad/two_board_print_01/housing.scad'
    readme=w.ROOT/'hardware/cad/two_board_print_01/README.md'
    text=capture.read_text();source=shell.read_text();spec=readme.read_text()
    mounts=json.loads(re.search(r'^mounts\s*=\s*(.*?);',text,re.M).group(1))
    assert len(mounts)==24
    assert 'for(m=mounts) translate([m[1],m[2],-.1])' in source and 'nut(4.2,1.9)' in source
    assert 'M2 × 10 pan-head screws, 0.5 mm washers' in spec
    assert 'M2 nuts assumed here are AF4.0 × 1.6 mm' in spec
    assert '6 mm feet leave 0.8 mm nominal table clearance' in spec
    previous=H/'selected-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,parts,_,_=w.load_manifest(previous)
    heads=w.ROOT/parts['base_board_heads']['source']
    assert 'm[0]!="D_H2" && m[0]!="D_H5"' in heads.read_text()
    pocket_roof=-.1+1.9;nut_height=1.6;washer=.5;board=1.6;length=10;feet=6
    rows=[]
    for name,x,y,post,bore in mounts:
        seat=post+board+washer;tip=seat-length;bottom=pocket_roof-nut_height
        rows.append(dict(mount=name,xy=[x,y],post_top_z=post,pcb_bore_diameter=bore,
            underhead_seat_z=seat,screw_tip_z=tip,nut_roof_z=pocket_roof,nut_bottom_z=bottom,
            nominal_tip_past_nut_mm=bottom-tip,nominal_table_gap_mm=feet+tip,
            original_m2x8_tip_z=seat-8,original_m2x8_reaches_nut=seat-8<pocket_roof,
            illustrative_tip_allowance_mm=.4,illustrative_full_nut_margin_mm=bottom-tip-.4,
            current_generic_head_owner=name not in ['D_H2','D_H5']))
    active=[r for r in rows if r['current_generic_head_owner']]
    assert len(active)==22 and sum(r['post_top_z']==6.75 for r in active)==9 and sum(r['post_top_z']==7.9 for r in active)==13
    assert all(r['nominal_table_gap_mm']>0 for r in rows)
    assert all(not r['original_m2x8_reaches_nut'] for r in rows if r['post_top_z']==7.9)
    out=dict(original_mounts=24,current_generic_main_heads=22,sensor_owned_mounts=['D_H2','D_H5'],
             nominal_feet_height_mm=feet,feet_part_placement_compression_qualified=False,
             original_bom_length_mm=length,original_bom_washer_mm=washer,rows=rows,
             below_floor_tips_are_intentional=True,all_nominal_main_tips_clear_nominal_table=True,
             illustrative_thread_allowance_not_manufacturer_limit=True,exact_main_hardware_selected=False,
             physical_mount_qualified=False,fabrication_released=False,
             source_sha256={**data['_loaded_sources'],**{w.relative(p):w.sha(p) for p in [Path(__file__),capture,shell,readme,heads]}})
    (H/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Original24mounts/22genericheads; signal nominaltip-1.15, power0.0; six-mmfeet authority retained')
if __name__=='__main__':run()
