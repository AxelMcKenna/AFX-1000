"""Correct AC04 placement metadata and inherit the existing VSSOP land rule.

All poses, lands and pin nets remain exact. This does not assign the missing
codec footprint or approve the manufacturing process.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/"hardware/fabrication"
OLD=ROOT/"staging/audio-main-placement-01"
OUT=ROOT/"staging/audio-main-placement-02"
ADC=ROOT/"staging/adc-driver-native-01/adc_driver.kicad_pro"


def build():
    if OUT.exists():
        assert not (OUT/"construction.json").exists() and not (OUT/"placement-native-review.json").exists()
        assert all((OLD/p.relative_to(OUT)).is_file() and sha(p)==sha(OLD/p.relative_to(OUT))
                   for p in OUT.rglob("*") if p.is_file()), "Only untouched copies from an incomplete build may be resumed"
    old_review=json.loads((OLD/"placement-native-review.json").read_text())
    assert all(sha(REPO/p)==h for p,h in old_review["source_sha256"].items())
    adc=json.loads(ADC.read_text())
    assert adc["board"]["design_settings"]["rules"]["min_clearance"]==.15
    OUT.mkdir(exist_ok=True)
    for p in OLD.iterdir():
        if p.suffix in (".kicad_pcb",".kicad_sch",".kicad_pro",".kicad_sym") or p.name in ("plan.json","fp-lib-table","sym-lib-table","applied-placement.py.txt"):
            shutil.copyfile(p,OUT/p.name)
    shutil.copytree(OLD/"libraries",OUT/"libraries",dirs_exist_ok=True)
    parts,_=netlist(OLD/"native-netlist.xml")
    bom,properties={},{}
    for p in OUT.glob("*.kicad_sch"):
        for s in children(read_sexpr(p.read_text()),"symbol"):
            ref=next(v[2] for v in children(s,"property") if v[1]=="Reference")
            if ref in parts:
                bom[ref]=first(s,"in_bom")[1]=="yes"
                properties[ref]={v[1]:v[2] for v in children(s,"property")}
    tree=read_sexpr((OUT/"audio_core.kicad_pcb").read_text())
    metadata=[]
    for fp in children(tree,"footprint"):
        ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
        if ref not in parts:
            continue
        source=properties[ref]
        for prop in list(children(fp,"property")):
            if prop[1]=="MPN" and "MPN" not in source:
                metadata.append(dict(ref=ref,field="MPN",before=prop[2],after=None))
                fp.remove(prop)
        for name,wanted in source.items():
            if name in ("Reference","Value","Footprint"):
                continue
            existing=[p for p in children(fp,"property") if p[1]==name]
            if existing:
                prop=existing[0]
                if prop[2]!=wanted:
                    metadata.append(dict(ref=ref,field=name,before=prop[2],after=wanted))
                    prop[2]=wanted
            else:
                side=str(first(fp,"layer")[1]).split(".")[0]
                fp.append(read_sexpr(f'(property {json.dumps(name)} {json.dumps(wanted)} (at 0 0 0) (layer "{side}.Fab") (effects (font (size .8 .8)) (hide yes)))'))
                metadata.append(dict(ref=ref,field=name,before=None,after=wanted))
        attr=children(fp,"attr")
        if attr:
            old=a("exclude_from_bom") in attr[0]
            if old==bom[ref]:
                metadata.append(dict(ref=ref,field="exclude_from_bom",before=old,after=not bom[ref]))
                if bom[ref]:
                    attr[0].remove(a("exclude_from_bom"))
                else:
                    attr[0].append(a("exclude_from_bom"))
    assert metadata
    (OUT/"audio_core.kicad_pcb").write_text(sexpr(tree)+"\n")
    project=json.loads((OUT/"audio_core.kicad_pro").read_text())
    project["board"]["design_settings"]["rules"]["min_clearance"]=.15
    assert project["net_settings"]["classes"][0]["clearance"]==.2
    (OUT/"audio_core.kicad_pro").write_text(json.dumps(project,indent=2)+"\n")
    cases=" || ".join(f"(A.memberOfFootprint('{r}') && B.memberOfFootprint('{r}'))" for r in ("U101","U102","U105","U106"))
    rules='(version 1)\n(rule "General copper clearance" (constraint clearance (min 0.20mm)))\n'
    rules+='(rule "Inherited VSSOP adjacent stock lands"\n'
    rules+=' (condition "A.Type == \'Pad\' && B.Type == \'Pad\' && ('+cases+')")\n'
    rules+=' (constraint clearance (min 0.15mm)))\n'
    (OUT/"audio_core.kicad_dru").write_text(rules)
    paths=[Path(__file__),OLD/"audio_core.kicad_pcb",OLD/"audio_core.kicad_pro",OLD/"plan.json",OLD/"placement-native-review.json",ADC]
    record=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},metadata_corrections=metadata,
        old_placement_preserved_exactly=True,old_lands_and_pin_nets_preserved_exactly=True,
        inherited_ADC_minimum_pad_clearance_mm=.15,general_copper_and_routing_clearance_mm=.2,
        VSSOP_rule_only_between_pads_of_the_same_named_footprint=["U101","U102","U105","U106"],
        rule_file_sha256=sha(OUT/"audio_core.kicad_dru"),unplaced_refs=["U201"],
        testpads_BOM_attributes_match_existing_schematic=True,
        assembly_BOM_must_classify_bare_testpads_as_nonfitted_copper=True,
        full_connector_mates_wire_paths_and_manufacturing_process_accepted=False,fabrication_released=False)
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    shutil.copyfile(Path(__file__),OUT/"applied-finalization.py.txt")
    print(f"Preserved all 328 placements; corrected {len(metadata)} instance fields/attributes; inherited scoped 0.15 mm VSSOP pad rule")


def review():
    assert sys.platform=="linux", "Mac CAD remains disabled"
    from hardware.fabrication import audio_main_placement

    paths=[Path(__file__),OUT/"audio_core.kicad_dru",OUT/"construction.json"]
    hashes={str(p.relative_to(REPO)):sha(p) for p in paths}
    audio_main_placement.OUT=OUT
    audio_main_placement.review()
    assert all(sha(REPO/p)==h for p,h in hashes.items())
    record=dict(additional_input_sha256=hashes,
        native_receipt_sha256=sha(OUT/"placement-native-review.json"),
        rule_inputs_identical_before_and_after_native_commands=True,
        native_driver_keeps_every_DRC_and_ERC_category_enabled=True,fabrication_released=False)
    (OUT/"rule-bound-native-review.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","review"))
    args=parser.parse_args()
    (build if args.action=="build" else review)()
