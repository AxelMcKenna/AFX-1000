"""Inventory the full unselected power-board mechanical handoff without waivers."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge
from hardware.electronics.common import sexpr as sx
from hardware.fabrication import assembly_layout

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'hardware/fabrication/staging/two-board-power-aux-local-distribution-native-03/power_protection.kicad_pcb'
CANDIDATE = ROOT / 'hardware/qualification/two_board_aux_current_08/reference_fix/inputs-reference-09/power_protection.kicad_pcb'

def main():
    before, after = bridge.snapshot(BASE), bridge.snapshot(CANDIDATE)
    delta = bridge.compare(before, after)
    additions = [d['ref'] for d in delta if d['field'] == 'presence' and d['before'] is None]
    removals = [d['ref'] for d in delta if d['field'] == 'presence' and d['after'] is None]
    poses = [d for d in delta if d['field'] == 'pose']
    order_only, unresolved = [], []
    for d in delta:
        if d['field'] != 'physical':
            continue
        # Exact child multisets: no semantic normalization or equivalence waiver.
        key = lambda v: Counter(json.dumps(x, sort_keys=True) for x in v)
        (order_only if key(d['before']) == key(d['after']) else unresolved).append(d['ref'])
    parts = []
    for ref in additions:
        fp = after['footprints'][ref]
        parts.append(dict(ref=ref, pose=fp['pose'], footprint=fp['library'], properties=fp['properties'],
                          supplier_height_verified=False, installed_envelope_qualified=False))
    sources = [Path(__file__), BASE, CANDIDATE, Path(bridge.__file__), Path(sx.__file__), Path(assembly_layout.__file__)]
    report = dict(selected=False, physical_qualified=False,
                  baseline=str(BASE.relative_to(ROOT)), candidate=str(CANDIDATE.relative_to(ROOT)),
                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  baseline_footprints=len(before['footprints']), candidate_footprints=len(after['footprints']),
                  counts_by_field=dict(Counter(d['field'] for d in delta)),
                  added_parts=parts, removed_parts=removals, pose_changes=poses,
                  exact_physical_child_order_only=order_only,
                  unresolved_physical_changes=unresolved,
                  property_changes=[d for d in delta if d['field']=='properties'],
                  differences=delta,
                  required_gates=['Source supplier maximum heights and installed tolerances for all added/changed parts',
                                  'Prove every residual physical-field difference against native geometry',
                                  'Update cumulative capture and screen the complete selected assembly',
                                  'Retain independent electrical, return-path, thermal and fabrication gates'])
    destination=HERE/'audit.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['baseline_footprints','candidate_footprints','counts_by_field']}))
    print('Added:', ', '.join(additions), 'Moved:', ', '.join(d['ref'] for d in poses))
    print('Exact child reorder:',len(order_only),'Unresolved physical:',len(unresolved))

if __name__ == '__main__':
    main()
