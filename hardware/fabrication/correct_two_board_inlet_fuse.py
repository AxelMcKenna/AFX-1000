"""Replace the unsupported inlet fuse MPN in a new, geometry-identical revision."""
import json
import shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha

BASE = STAGING / 'two-board-power-input-tvs-native-01'
OUT = STAGING / 'two-board-power-inlet-fuse-01'
OLD = '0451006.MRL 6A 125V'
NEW = '045106.3MRL 6.3A 125V'
MPN = '045106.3MRL'


def run():
    assert not OUT.exists()
    prior = STAGING / 'two-board-fabrication-status-34/status.json'
    for name, digest in json.loads(prior.read_text())['source_sha256'].items():
        assert sha(REPO / name) == digest, name
    # Copy only the editable CAD and its circuit contract, not stale reports,
    # previews or temporary native-zone export projects.
    OUT.mkdir()
    copied = []
    for p in BASE.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(BASE)
        keep = (rel.parts[0] in ['libraries', 'symbols'] or
                (len(rel.parts) == 1 and (p.suffix == '.kicad_sch' or
                 p.name in ['power_protection.kicad_pcb', 'power_protection.kicad_pro',
                            'power_protection.kicad_dru', 'fp-lib-table', 'sym-lib-table',
                            'expected-circuit.json', 'symbol-paths.json'])))
        if keep:
            target = OUT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            copied.append(p)
    changed = []
    for p in [OUT/'I_rear_inlet.kicad_sch', OUT/'symbols/TBP01_I_RMX_E23I2.kicad_sym']:
        text = p.read_text()
        count = text.count(OLD)
        assert count > 0
        p.write_text(text.replace(OLD, NEW))
        changed.append(dict(path=str(p.relative_to(OUT)), replacements=count))
    p = OUT/'power_protection.kicad_pcb'
    board = read_sexpr(p.read_text())
    fuse = next(f for f in children(board, 'footprint') if prop(f, 'Reference')[2] == 'I_F1')
    assert prop(fuse, 'Value')[2] == prop(fuse, 'MPN')[2] == OLD
    prop(fuse, 'Value')[2] = NEW
    prop(fuse, 'MPN')[2] = MPN
    p.write_text(sexpr(board)+'\n')
    p = OUT/'expected-circuit.json'
    contract = json.loads(p.read_text())
    assert contract['I_F1']['value'] == OLD
    contract['I_F1']['value'] = NEW
    p.write_text(json.dumps(contract, indent=2)+'\n')
    p = OUT/'power_protection.kicad_sch'
    root = read_sexpr(p.read_text())
    first(first(root, 'title_block'), 'rev')[1] = 'TBP35'
    p.write_text(sexpr(root)+'\n')
    sources = [Path(__file__), prior, REPO/'hardware/fabrication/parts/inlet-fuse-01/README.md', *copied]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  ref='I_F1', old_value=OLD, new_value=NEW, new_MPN=MPN,
                  changed_symbol_files=changed, geometry_changes=0, pin_net_changes=0,
                  current_rating_a=6.3, nominal_cold_resistance_ohm=.0096,
                  conditional_4a_cold_drop_v=4*.0096, conditional_4a_cold_loss_w=16*.0096,
                  continuous_25C_allocation_a=6.3*.75,
                  minimum_temperature_multiplier_for_4a=4/(6.3*.75),
                  hot_resistance_bounded=False, fuse_adapter_TVS_fault_coordination_qualified=False,
                  native_and_independent_review_pending=True, fabrication_released=False)
    (OUT/'inlet-fuse-change.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(ref='I_F1', value=NEW, geometry_changes=0)))


if __name__ == '__main__':
    run()
