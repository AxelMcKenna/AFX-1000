"""Run the surface-routing gate against the signal PCB actually selected by CAD."""
import argparse
import hashlib
import json
from pathlib import Path

from hardware.cad.signal_completion.review_routes import audit

ROOT = Path(__file__).resolve().parents[3]


def selected_pcb(selected):
    pcb = (ROOT / selected['boards']['signal']).resolve()
    assert pcb.is_relative_to(ROOT)
    assert pcb.parent.parent == Path(__file__).resolve().parent, 'Selected PCB requires its own qualified gate'
    assert pcb.name == 'signal_main.kicad_pcb', 'Selected PCB is not the board checked by the native gate'
    return pcb


def run(output):
    path = ROOT / 'hardware/cad/assembly_workflow/current.json'
    before = path.read_bytes()
    selected = json.loads(before)
    pcb = selected_pcb(selected)
    native = pcb.parent
    native_report = json.loads((native / 'native-review.json').read_text())
    manifests = [ROOT / name for name in native_report['source_sha256'] if name.endswith('/routing.json')]
    assert len(manifests) == 1, 'Ambiguous native routing contract'
    candidate = manifests[0].parent.resolve()
    assert candidate.is_relative_to(ROOT)
    routing = json.loads(manifests[0].read_text())
    assert routing['baseline_opens'] == 162 and not routing['new_vias'], 'Selected PCB exceeds this surface gate scope'
    audit(candidate, native, output)
    assert path.read_bytes() == before, 'Assembly selection changed during verification'
    print(json.dumps({'selected_signal_pcb': str(pcb.relative_to(ROOT)),
                      'selected_signal_sha256': hashlib.sha256(pcb.read_bytes()).hexdigest(),
                      'selected_manifest_sha256': hashlib.sha256(before).hexdigest(),
                      'native_opens': native_report['native_opens'], 'fabrication_released': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.output)
