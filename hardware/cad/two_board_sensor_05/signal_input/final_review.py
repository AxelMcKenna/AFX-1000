"""Seal selected native, reference, transition, fidelity and analog review evidence."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
files=['native-r7/review.json','reference-review-r7.json','transitions-r7.json','fidelity-r7.json','analog-review.json']
reports={}
for name in files:
 d=json.loads((R/name).read_text());reports[name]=d
 for p,h in d['source_sha256'].items():
  path=Path(p)if Path(p).is_absolute()else REPO/p
  assert hashlib.sha256(path.read_bytes()).hexdigest()==h,p
native=reports[files[0]];ref=reports[files[1]];assert native['native_opens']==230 and not native['native_geometry'] and native['exact_all_netlist_partitions']and native['old_objects_unchanged'];assert len(ref['new_reference_cases'])==28 and all(x['uncovered_mm2']<1e-6 for x in ref['new_reference_cases']);assert ref['maximum_retained_loss_mm2']<1e-6;assert len(reports[files[2]]['transitions'])==15 and reports[files[3]]['pass']
paths=[R/p for p in files]+[Path(__file__),R/'README.md',R/'SELF-REVIEW.md',R/'preview_r7.py',R/'preview-r7.png']
result={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'new_paths':28,'retained_reference_cases':len(ref['retained_reference_cases']),'local_returns':15,'fidelity_cases':len(reports[files[3]]['cases']),'all_selected_checks_pass':True,'analog_noise_stability_qualified':False,'fabrication_released':False}
(R/'final-review.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items()if k!='source_sha256'})
