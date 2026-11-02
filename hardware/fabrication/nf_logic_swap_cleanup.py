"""Remove nonfunctional logic leaves after routing, preserving pad connectivity.

This produces a separate candidate and an exact removal inventory. Native
refill, DRC/ERC, and independent before/after connectivity capture remain required.
"""
import argparse
import json
from pathlib import Path
from hardware.fabrication.nf_logic_swap_leaf_finish import prune_leaves
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v)
               for v in (args.capture, args.label))
    cp = ROOT/'staging'/args.capture/'capture.json'
    capture = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    prep = ROOT/'staging/nf-logic-swap-reserved-01/construction.json'
    nets = set(json.loads(prep.read_text())['affected_nets'])
    _, removed, partitions = prune_leaves(capture, nets)
    ids = {r['object']['uuid'] for r in removed}
    nodes = [n for n in children(board, 'segment')+children(board, 'via')
             if first(n, 'uuid')[1] in ids]
    assert len(nodes) == len(ids) and ids
    for node in nodes:
        board.remove(node)
    out = ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    pcb = out/source.name
    pcb.write_text(sexpr(board)+'\n')
    inputs = [source, cp, prep, Path(__file__), ROOT/'nf_logic_swap_leaf_finish.py',
              ROOT/'nf_logic_swap_prepare.py', ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(pcb),
        removed_objects=nodes, removal_reasons=removed,
        protected_pad_partitions=partitions, host_pad_partitions_preserved=True,
        native_checks_pending=True, physical_qualified=False, fabrication_released=False
    ), indent=2)+'\n')
    print('Removed nonfunctional leaves:', len(nodes))


if __name__ == '__main__':
    run()
