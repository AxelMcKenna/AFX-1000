"""Derive quantities for the selected nominal main mounts, excluding sensor mounts."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

H = Path(__file__).resolve().parent
budget_path = H.parent / 'main-fasteners-r1/budget.json'
budget = json.loads(budget_path.read_text())
copper_path = H / 'copper-review.json'
copper = json.loads(copper_path.read_text())
mounts = {k: sorted(v['minimum_conservative_gap_mm']) for k, v in copper['boards'].items()}
assert len(mounts['signal']) == 9 and len(mounts['power']) == 13
assert not set(mounts['signal']) & set(mounts['power'])
assert not {'D_H2', 'D_H5'} & set(sum(mounts.values(), []))
rows = [dict(part=budget['parts']['signal_screw'], quantity=9, role='signal main-board screw', mounts=mounts['signal']),
        dict(part=budget['parts']['power_screw'], quantity=13, role='power main-board screw', mounts=mounts['power']),
        dict(part=budget['parts']['washer'], quantity=22, role='main-board washer', mounts=sorted(sum(mounts.values(), []))),
        dict(part=budget['parts']['nut'], quantity=22, role='main-board nut', mounts=sorted(sum(mounts.values(), [])))]
out = dict(scope='Selected nominal22main-board mounts only; sensor-owned D_H2/D_H5 and unselected touch cradle excluded',
    items=rows, physical_receiving_qualified=False,
    receiving_budget=w.relative(budget_path),
    source_sha256={w.relative(p): w.sha(p) for p in [Path(__file__), budget_path, copper_path]})
(H / 'bill-of-materials.json').write_text(json.dumps(out, indent=2) + '\n')
print('Nominal BOM:9signal screws,13power screws,22washers,22nuts; no sensor duplication')
