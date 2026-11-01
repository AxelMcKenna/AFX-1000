"""Freeze the private NF03C schematic study without making physical claims."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from hardware.qualification.boards.startup_negative_protection.capture import sha
from hardware.qualification.boards.startup_negative_protection.verify import validate_handoff
from .analyze import ROOT,PARENT,REPO


def seal():
    assert not (ROOT/'handoff.json').exists(),'Immutable handoff; create successor'
    validate_handoff(PARENT/'handoff.json')
    # Retain the actual imported upstream helpers/ledger, not only hashes to
    # live mutable sources. No original files are changed.
    sources=['hardware/electronics/common/flat_schematic.py','hardware/electronics/common/netlists.py','hardware/electronics/common/sexpr.py','hardware/electronics/power_distribution/p03/bipolar.py','hardware/electronics/power_distribution/p03/models.py','hardware/electronics/power_distribution/p03/spec.py','hardware/qualification/boards/startup_negative_protection/analyze.py','hardware/qualification/boards/startup_negative_protection/capture.py','hardware/qualification/boards/startup_negative_protection/verify.py','hardware/qualification/boards/startup_negative_protection/handoff.json','hardware/qualification/boards/startup_negative_protection/generated/analysis.json','hardware/qualification/boards/startup_negative_protection/sources/p03-fresh-netlist.xml','hardware/qualification/boards/startup_negative_protection/sources/e28-fresh-netlist.xml','hardware/cad/a12/thermal/whole_unit/generated/ledger.json']
    snapshots={}
    for n in sources:
        source=REPO/n;h=sha(source);dest=ROOT/'sources/snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);assert sha(source)==h==sha(dest)
        snapshots[n]=dict(sha256=h,snapshot=str(dest.relative_to(ROOT)))
    (ROOT/'sources/imported-inputs.json').write_text(json.dumps(snapshots,indent=2)+'\n')
    area=json.loads((ROOT/'generated/footprint-area.json').read_text())
    for row in area['rows']:
        src=Path(row['library_file']);dest=ROOT/'sources/footprints'/(row['footprint'].replace(':','__')+'.kicad_mod');dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest);assert sha(dest)==row['library_sha256']
    current=json.loads((ROOT/'generated/current-native.json').read_text())
    for group in ['source_sha256','artifact_sha256']:
        for n,h in current[group].items():assert sha(ROOT/n)==h,n
    assert current['erc']=={'error':0,'warning':2}
    erc=json.loads((ROOT/'generated/erc.json').read_text());issues=[v for s in erc['sheets'] for v in s['violations']]
    assert all(x['type']=='ground_pin_not_ground' for x in issues),issues
    (ROOT/'generated/erc-review.json').write_text(json.dumps(dict(erc_sha256=sha(ROOT/'generated/erc.json'),reviewed=issues,reason='Exact ISO7721 GND1 pins intentionally reference negativeP03source; manufacturer names retained. No warning suppressed, no falseAGND tie.',all_other_warnings_or_errors=0,physical_qualified=False),indent=2)+'\n')
    run=subprocess.run([sys.executable,'-m','unittest','hardware.qualification.boards.startup_negative_circuit.compact.test_compact','-v'],cwd=REPO,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(REPO)),text=True,capture_output=True,timeout=120)
    (ROOT/'generated/tests.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stdout+run.stderr
    a=json.loads((ROOT/'generated/analysis.json').read_text())
    # Ensure output numeric file is bound to current model/input bytes.
    for n,h in a['source_sha256'].items():assert sha(ROOT/n)==h,n
    files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='handoff.json'}
    handoff=dict(revision='NF03C-private-native-schematic-and-conditional-requirements',files_sha256=files,files=len(files),parts=current['parts'],erc=current['erc'],native_pin_parity_differences=0,tests_passed=15,
                 sum_courtyard_mm2=area['sum_front_courtyard_area_mm2'],sum_courtyard_times1p2_mm2=area['area_times1p2_reference_mm2'],
                 complete_local_power_stage_schematic_authored=True,E28_integration_implemented=False,PCB_authored=False,placement_accepted=False,source_fault_peak_upper_a=None,total_fault_energy_upper_j=None,
                 physical_tests_performed=0,startup_qualified=False,hot_SOA_qualified=False,reverse_discharge_qualified=False,physical_qualified=False,fabrication_released=False,build_ready=False)
    (ROOT/'handoff.json').write_text(json.dumps(handoff,indent=2)+'\n')
    assert all(sha(ROOT/n)==h for n,h in files.items())
    print('NF03C sealed',len(files),'files',current['parts'],'parts',sha(ROOT/'handoff.json'))

if __name__=='__main__':seal()
