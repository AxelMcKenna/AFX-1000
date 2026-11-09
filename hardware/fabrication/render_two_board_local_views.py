"""Render a square detail viewport without changing native SVG drawing content."""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--viewport', required=True, type=float, nargs=3, metavar=('X', 'Y', 'SIZE'))
    ap.add_argument('--layers', nargs='+', default=['front', 'back'])
    args = ap.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.source)
    assert set(args.layers) <= {'front', 'back', *[f'inner{i}' for i in range(1, 7)]}
    x, y, size = args.viewport
    assert size > 0
    plots = STAGING / args.source / 'plots'
    native = json.loads((plots / 'native-plots.json').read_text())
    sources = [Path(__file__), plots / 'native-plots.json']
    outputs = []
    with tempfile.TemporaryDirectory(prefix='afx-local-views-', dir='/private/tmp') as temp:
        for name in args.layers:
            src = plots / (name + '.svg')
            assert sha(src) == native['artifact_sha256'][src.name]
            sources.append(src)
            s = src.read_text()
            s, n = re.subn(r'viewBox="[^"]+"', f'viewBox="{x} {y} {size} {size}"', s, count=1)
            assert n == 1
            s = re.sub(r'width="[^"]+"', 'width="1600"', s, count=1)
            s = re.sub(r'height="[^"]+"', 'height="1600"', s, count=1)
            target = plots / ('local-' + name + '.svg')
            with target.open('x') as f:
                f.write(s)
            subprocess.run(['qlmanage', '-t', '-s', '1600', '-o', temp, str(target)],
                           check=True, capture_output=True, text=True, timeout=60)
            png = target.with_suffix('.png')
            assert not png.exists()
            with Image.open(Path(temp) / (target.name + '.png')) as im:
                assert im.size == (1600, 1600)
                im.convert('RGB').save(png)
            outputs.extend([target, png])
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  artifact_sha256={p.name: sha(p) for p in outputs},
                  viewport_native_svg=[x, y, size, size], only_canvas_and_viewbox_changed=True,
                  visual_inspection_pending=True, fabrication_released=False)
    with (plots / 'detail-render.json').open('x') as f:
        json.dump(record, f, indent=2)
        f.write('\n')
    print(f'Rendered {len(args.layers)} local copper views')


if __name__ == '__main__':
    run()
