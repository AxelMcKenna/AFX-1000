"""Receiving-only stack budget; sourced nominal parts do not imply physical qualification."""
import json,math,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def calc(board, length=None, washer=(.25,.35), feet=6., mount=None):
    assert board in ('signal','power')
    assert mount not in ('D_H2','D_H5'),'Sensor-owned mount'
    post=(6.65,6.85) if board=='signal' else (7.8,8.)
    # Receiving requirements informed by js15 table, not an Accu length guarantee.
    length=length or ((9.71,10.29) if board=='signal' else (11.65,12.35))
    pcb=(1.5,1.7)
    seat=(post[0]+pcb[0]+washer[0],post[1]+pcb[1]+washer[1])
    tip=(seat[0]-length[1],seat[1]-length[0])
    minimum_nut_bottom=1.7-1.6
    full=minimum_nut_bottom-tip[1]-.4
    table=feet+tip[0]
    bore=(2.35-2.)/2-.1
    angle=math.radians(.5)
    hex_gap=(4.15-4.*(math.cos(angle)+math.sin(angle)/math.sqrt(3)))/2-.05
    assert full>=.5 and table>=1. and bore>0 and hex_gap>0
    return dict(post_seat_z_mm=post,pcb_thickness_mm=pcb,washer_thickness_mm=washer,
                receiving_screw_length_mm=length,underhead_z_mm=seat,tip_z_mm=tip,
                full_thread_beyond_nut_min_mm=full,table_gap_min_mm=table,
                shank_bore_radial_gap_min_mm=bore,nut_hex_gap_min_mm=hex_gap,
                head_top_max_mm=seat[1]+2.,board_top_min_mm=post[0]+pcb[0],
                required_loaded_floor_to_table_mm=feet)
def run():
    rows={b:calc(b) for b in ['signal','power']}
    parts={'signal_screw':'SSCF-M2-10-A2','power_screw':'SSCF-M2-12-A2','washer':'HRDW-M2-A4-BL','nut':'HPN-M2-A2'}
    sources=[Path(__file__),H/'parts.scad',*sorted((H/'sources').glob('*.pdf')),R/'hardware/cad/two_board_installation_06/r26_touch_mount/sources/HPN-M2-A2.pdf',R/'hardware/cad/two_board_installation_06/r26_touch_mount/sources/unbrako-engguide.pdf']
    out=dict(status='CONDITIONAL_STACK_NOT_SELECTED',parts=parts,budgets=rows,
        receiving_conditions={'nut_roof_z_mm':[1.7,1.9],'printed_hex_AF_min_mm':4.15,'nut_center_registration_max_mm':.05,'nut_flat_alignment_max_degrees':.5,'screw_center_registration_max_mm':.1,'washer_to_screw_registration_max_mm':.05,'washer_to_mount_registration_max_mm':.15,'incomplete_thread_tip_max_mm':.4,'washer_outer_max_mm':4.5},
        underhead_fillet_washer_mating_qualified=False,physical_qualified=False,
        open=['Confirm delivered screw length and incomplete-tip allowance','Verify underhead transition fits actual washer without lifting its seat','Inspect washer and nut registration; clearance alone does not constrain centering','Qualify nut bearing, torque, printed strength and loaded feet/fixture clearance','Repair D_H4 copper contact before selecting hardware'],
        source_sha256={str(p.relative_to(R)):sha(p) for p in sources})
    (H/'budget.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':run()
