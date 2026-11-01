import hashlib,json
from pathlib import Path
R=Path(__file__).parent;P=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/electronics/power_distribution/p03/candidates/strict-native-centering');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
h=json.loads((P/'handoff.json').read_text());bad=[p for p,v in h['files_sha256'].items() if sha(P/p)!=v];assert not bad,bad
old=json.loads((P/'power_p03.kicad_pro').read_text());new=json.loads((R/'p03-erc-audit/power_p03.kicad_pro').read_text());keys=['single_global_label','four_way_junction','simulation_model_issue','footprint_filter'];expected=json.loads(json.dumps(old))
for k in keys:expected.setdefault('erc',{}).setdefault('rule_severities',{})[k]='error'
assert new==expected
for f in ['power_p03.kicad_sch','RMX_P03.kicad_sym','sym-lib-table','fp-lib-table']:assert (P/f).read_bytes()==(R/'p03-erc-audit'/f).read_bytes()
d=json.loads((R/'p03-strict-erc.json').read_text());assert d['ignored_checks']==[] and all(not s['violations'] for s in d['sheets'])
inputs={str(p):sha(p) for p in [P/'handoff.json',P/'power_p03.kicad_pcb',P/'power_p03.kicad_pro',P/'power_p03.kicad_sch',R/'p03-erc-audit/power_p03.kicad_pro',R/'p03-erc-audit/power_p03.kicad_sch',R/'p03-strict-erc.json',R/'p03-strict-erc.log',Path(__file__)]}
r=dict(status='READ_ONLY_ALL_ERC_CHECK_COVERAGE_AUDIT_PASS',source_pcb_sha256=sha(P/'power_p03.kicad_pcb'),parent_sealed_files_verified=len(h['files_sha256']),parent_files_changed=[],only_project_change={k:'error' for k in keys},fresh_ERC_violations=0,fresh_ERC_ignored_checks=[],no_board_or_schematic_change=True,all_P03_frozen_files_untouched=True,source_artifact_sha256=inputs,fresh_PCB_DRC_rerun_claimed=False,physical_qualification=False)
(R/'p03-erc-audit.json').write_text(json.dumps(r,indent=2)+'\n');print('P03 strict ERC PASS, parent',len(h['files_sha256']),'files verified unchanged')
