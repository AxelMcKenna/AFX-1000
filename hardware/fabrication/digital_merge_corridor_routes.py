"""Combine independently screened additive SD and LED escapes from one baseline."""
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def run():
    base = ROOT/'staging/digital-corridor-native-02/digital_core.kicad_pcb'
    original = read_sexpr(base.read_text())
    board = read_sexpr(base.read_text())
    ids = {first(n, 'uuid')[1] for tag in ('segment', 'via') for n in children(board, tag)}
    inputs = [base, Path(__file__)]
    rows = []
    for label in ('digital-sd-matched-routes-01', 'digital-led-fanout-02'):
        folder = ROOT/'staging'/label
        receipt = folder/'construction.json'
        record = json.loads(receipt.read_text())
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
        assert record['source_sha256'][str(base)] == sha(base)
        pcb = folder/base.name
        assert record['candidate_PCB_sha256'] == sha(pcb)
        candidate = read_sexpr(pcb.read_text())
        assert sexpr(candidate[:len(original)]) == sexpr(original)
        additions = candidate[len(original):]
        assert all(n[0] in ('segment', 'via') for n in additions)
        for node in additions:
            uid = first(node, 'uuid')[1]
            assert uid not in ids
            ids.add(uid)
            board.append(node)
        rows.append(dict(source=label, added_objects=len(additions)))
        inputs += [receipt, pcb]
    out = ROOT/'staging/digital-coordinated-routes-01'
    out.mkdir(exist_ok=False)
    pcb = out/base.name
    pcb.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(pcb),
        additions=rows, all_baseline_geometry_exact=True, native_checks_pending=True,
        fabrication_released=False), indent=2)+'\n')
    print(rows)


if __name__ == '__main__':
    run()
