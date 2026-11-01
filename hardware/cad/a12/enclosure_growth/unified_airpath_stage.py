"""Capture a NEW coherent partial-routing unit before native integration.

This entry point captures physical inputs only. The sealed32 E28 is expressly
not the latest development, and no old wire/thermal/PDN passes are inherited.
"""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from hardware.cad.a12.repaired import packet

A12=Path(__file__).resolve().parents[1]
REPO=A12.parents[2]
ROOT=A12/"enclosure_growth/unified_airpath"
AP=A12/"thermal/interior_airpath_meter318"
PB=A12/"positive_links/proposals/dig-leg-y121p3"
R1=A12/"harness/proposals/processor-awg18-ear-fanout-j29-central-r1"
P03=REPO/"hardware/electronics/power_distribution/p03/candidates/aux-u10-combined"
E28=REPO/"hardware/electronics/rail_disconnect/revision28/generated/u28-return-dual-plane-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2)+"\n")


def sealed(p):
    h=json.loads((p/"handoff.json").read_text())
    for n,v in h["files_sha256"].items():
        if sha(p/n)!=v:
            raise RuntimeError("Stale sealed input: "+str(p/n))
    return h


def capture():
    if ROOT.exists():
        raise RuntimeError("NEW unified capture only; refuse existing destination")
    parents={}
    for name,p in [("AP03",AP),("PB02_WR01",PB),("R1",R1),("R1_PDN",R1.parent/(R1.name+"-pdn"))]:
        h=sealed(p)
        parents[name]=dict(path=str(p),handoff_sha256=sha(p/"handoff.json"),files=len(h["files_sha256"]))
    ehpath=E28/"generated/handoff.json"
    eh=json.loads(ehpath.read_text())
    assert sha(ehpath)=="a3993a5767bcad3c748d23cd35cab7f927ef5a43b18303354cf16f942e4b364f"
    assert sha(E28/"rail_disconnect.kicad_pcb")==eh["exact_PCB_sha256"]=="dd6a6f5adab873526234818c1b4274925e8c8e75b9cfe34be1ca9f258753e5ec"
    archive=REPO/eh["archive_path"]
    assert sha(archive)==eh["archive_sha256"]
    expected=dict(eh["source_sha256"],**eh["artifact_sha256"])
    with tarfile.open(archive,"r:gz") as tf:
        members={m.name:m for m in tf.getmembers() if m.isfile()}
        assert len(members)==eh["archive_members"]
        for n,m in members.items():
            assert not Path(n).is_absolute() and ".." not in Path(n).parts
            blob=tf.extractfile(m).read()
            if n in expected:
                assert hashlib.sha256(blob).hexdigest()==expected[n],n
    assert sha(P03/"power_p03.kicad_pcb")=="db83a26f98e3638d7b1a723be5d54f71c4e3aaa5418021e5b9003afea810283d"
    assert sha(R1/"processor_carrier.kicad_pcb")=="dc559bd94d0decdb89ee647cde00709f15463304e051497bf8b7dacc719194c8"
    physical=packet(board_overrides={"P03":P03,"E28":E28})
    assert len(physical["component_records"])==507 and not physical["same_board_component_overlap_candidates"]
    ROOT.mkdir()
    sources={}
    for name,p in [("P03",P03),("E28",E28),("R1",R1)]:
        dst=ROOT/"inputs"/name
        shutil.copytree(p,dst,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
        sources.update({str(x):sha(x) for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts and x.suffix!=".pyc"})
    shutil.copytree(AP/"model",ROOT/"model")
    for p in (ROOT/"model").rglob("*.scad"):
        p.write_text(p.read_text().replace(str(AP),str(ROOT)))
    for name in ["checks.scad","current-checks.scad","source-tray.scad","nominal-frame-land.stl","nominal-common-land.stl","analysis.json"]:
        p=AP/"generated"/name
        dst=ROOT/"generated"/name
        dst.parent.mkdir(exist_ok=True)
        if p.suffix==".scad":dst.write_text(p.read_text().replace(str(AP),str(ROOT)))
        else:shutil.copyfile(p,dst)
    shutil.copyfile(AP/"channel_checks.scad",ROOT/"channel_checks.scad")
    shutil.copytree(PB/"generated",ROOT/"inputs/PB02-generated")
    for p in [PB/"design.json",PB/"wire-raise-1mm/plan.json",PB/"native/gauge-derived.scad"]:
        dst=ROOT/"inputs/PB02"/p.relative_to(PB)
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dst)
        sources[str(p)]=sha(p)
    for p in [Path(__file__),A12/"returns/design.json",A12/"returns/generate.py"]:
        dst=ROOT/"inputs/repository"/p.relative_to(REPO)
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dst)
        sources[str(p)]=sha(p)
    for n,h in physical["source_sha256"].items():
        p=REPO/n
        assert sha(p)==h
        sources[str(p)]=h
        dst=ROOT/"inputs/repository"/n
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():shutil.copyfile(p,dst)
    write(ROOT/"generated/actual-native-boards.json",physical)
    write(ROOT/"capture.json",dict(parents=parents,source_sha256=sources,
        copied_input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"inputs").rglob("*") if p.is_file()},
        AP03_source_model_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"model").rglob("*") if p.is_file()},
        sealed32_E28_handoff_sha256=sha(ehpath),sealed32_archive_sha256=sha(archive),
        sealed32_archive_members_verified=len(members),native_E28_opens=32,
        checkpoint_is_latest_development=False,authoritative_P03_owner_confirmed_db83=True,
        source_ground_mm=[161,129.5,6.62],old_ground_mm=[161,126.5,6.62],receiver_ground_mm=[188,104,8.1],
        new_groundroute_required=True,new_ANA_return_bar_required=True,
        actual_NF03_board_adopted=False,actual_FH_board_adopted=False,
        native_geometry_executed=False,physical_qualified=False,thermal_qualified=False,fabrication_released=False))
    print(json.dumps(dict(captured=True,source_files=len(sources),physical_component_records=507,E28_opens=32)))


if __name__=="__main__":
    capture()
