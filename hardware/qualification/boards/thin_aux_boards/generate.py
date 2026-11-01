"""Stage 1.2mm auxiliary-board candidates and explicit edge-shim receiving parts.

These remove the PH connector thickness-range conflict in the proposed
receiving specification. Fabricator stackup, shim manufacture, stiffness,
assembly receiving and all new physical checks remain unaccepted.
"""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
BOARDS=ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    out=ROOT/"generated"
    out.mkdir(exist_ok=False)
    cases=[("NF",BOARDS/"startup_negative_circuit/physical_layout/routing/receiving-continuation-repair-01/output.kicad_pcb",
            BOARDS/"startup_negative_circuit/physical_layout/receiving_repair","negative_startup_physical"),
           ("FPC",BOARDS/"fan_health/composite_nf_branch/fan_power_health.kicad_pcb",
            BOARDS/"fan_health/composite_nf_branch","fan_power_health")]
    records=[]
    for ident,source,project,name in cases:
        target=out/ident
        target.mkdir()
        captured={str(source):sha(source)}
        for p in project.iterdir():
            if p.is_dir() and p.suffix==".pretty":
                shutil.copytree(p,target/p.name)
                captured.update({str(f):sha(f) for f in p.rglob("*") if f.is_file()})
            elif p.is_file() and (p.suffix in (".kicad_sch",".kicad_pro",".kicad_sym",".kicad_dru")
                or p.name in ("fp-lib-table","sym-lib-table","components.json","bom.csv")):
                shutil.copyfile(p,target/p.name)
                captured[str(p)]=sha(p)
        if ident=="NF":
            # The receiving-repair PCB/schematic use the physical parent's
            # external library; capture it explicitly in this portable copy.
            for library in ("RMX_NF06P.kicad_sym","sym-lib-table"):
                p=project.parent/library
                if not (target/library).exists():
                    shutil.copyfile(p,target/library)
                    captured[str(p)]=sha(p)
        tree=read_sexpr(source.read_text())
        original_geometry=[sexpr(n) for n in tree if isinstance(n,list) and n and n[0] not in ("general","setup")]
        first(first(tree,"general"),"thickness")[1]=a(1.2)
        setup=first(tree,"setup")
        stack=children(setup,"stackup")
        stack_changes=[]
        if ident=="FPC":
            assert len(stack)==1
            core=next(n for n in children(stack[0],"layer") if n[1]=="dielectric 2")
            assert float(first(core,"thickness")[1])==1.06
            first(core,"thickness")[1]=a(.66)
            stack_changes.append(dict(layer="dielectric 2",before_mm=1.06,after_mm=.66))
            total=sum(Decimal(str(first(n,"thickness")[1])) for n in children(stack[0],"layer") if children(n,"thickness"))
            assert total==Decimal("1.2")
        else:
            assert not stack,"Inspect any newly added NF stackup rather than silently rescaling it"
        assert [sexpr(n) for n in tree if isinstance(n,list) and n and n[0] not in ("general","setup")]==original_geometry
        pcb=target/(name+".kicad_pcb")
        pcb.write_text(sexpr(tree)+"\n")
        assert all(sha(Path(p))==h for p,h in captured.items())
        records.append(dict(board=ident,source_sha256=captured,candidate_pcb=str(pcb),candidate_sha256=sha(pcb),
            nominal_finished_thickness_mm=1.2,finished_thickness_receiving_mm=[1.08,1.32],
            stackup_changes=stack_changes,all_XY_footprints_tracks_vias_holes_rule_areas_and_outlines_exact=True,
            manufacturer_stackup_accepted=False,native_checks_pending=True,physical_qualified=False,fabrication_released=False))
    d=Decimal
    pcb_min,pcb_max=d("1.08"),d("1.32")
    shim_min,shim_max=d(".36"),d(".44")
    assert pcb_min>=d(".8")*d("1.2")
    assert pcb_max*d("1.2")<=d("1.6")
    assert pcb_min+shim_min==d("1.44") and pcb_max+shim_max==d("1.76")
    shims=[["NF",210,42.5],["NF",310,42.5],["FPC",31,41.5],["FPC",68.5,41.5]]
    (out/"edge-shims.scad").write_text('// RECEIVING PROPOSAL ONLY: custom FR4 shims, material/process unaccepted.\n'
        'shims='+json.dumps(shims)+';\n'
        'module thin_edge_shims(){for(p=shims)for(z=[3.5,p[2]-1.2])\n'
        'translate([p[1]-3,181.7,z])cube([6,.4,1.2]);}\n'
        'thin_edge_shims();\n')
    record=dict(revision="TA01-1p2mm-aux-boards",recipe_sha256=sha(Path(__file__)),boards=records,
        PH_catalog_applicable_board_mm=[.8,1.6],lower_bound_ratio=1.35,upper_bound_ratio=1.6/1.32,
        margin_factor_required=1.2,thickness_catalog_margin_met_by_proposed_specification=True,
        PCB_fabrication_tolerance_fraction=.1,source_for_6layer_thickness_capability="https://jlcpcb.com/resources/6-layer-pcbs",
        shim_nominal_mm=.4,shim_receiving_mm=[.36,.44],shim_material="custom FR4, exact grade unselected",
        shim_manufacturing_tolerance_is_a_receiving_requirement_not_a_supplier_guarantee=True,
        combined_PCB_shim_receiving_mm=[1.44,1.76],original_mount_stack_receiving_mm=[1.44,1.76],
        original_front_board_datum_y_mm=180.5,nominal_board_stiffness_ratio_same_material=(1.2/1.6)**3,
        stiffness_vibration_and_mounting_qualification_required=True,
        back_side_components_must_use_new_board_surface_datum=True,
        lead_tail_trim_requirement_from_actual_backside_max_mm=1.5,
        untrimmed_manufacturer_lead_projection_not_reduced_automatically=True,
        old_enclosure_receiving_results_inherited=False,shim_placement_full_assembly_pending=True,
        source_regulators_P03_and_E28_thickness_unchanged=True,native_Mac_apps_launched=0,
        physical_qualified=False,fabrication_released=False)
    (out/"proposal.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Staged two editable1.2mm candidates and eight receiving edge shims; all sources unchanged")


if __name__=="__main__":
    run()
