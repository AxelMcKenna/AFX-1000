"""Render a source-bound XY receiving-envelope comparison, not a fit verdict."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from hardware.cad.assembly_workflow import workflow as w

H = Path(__file__).resolve().parent
old_path = w.HERE / 'pcb_updates/r62/capture.json'
new_path = H / 'capture.json'
im = Image.new('RGB', (1320, 730), '#f5f7fa')
d = ImageDraw.Draw(im)
font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
font = ImageFont.truetype(font_path, 17)
small = ImageFont.truetype(font_path, 13)
title = ImageFont.truetype(font_path, 25)
d.text((28, 20), 'D101 receiving envelope: exact rigid move on signal-board underside', font=title, fill='#182b40')
for i, (path, label, color) in enumerate([(old_path, 'Before: (75, 66), native 0°', '#3a76bb'), (new_path, 'Candidate: (75.8, 65.2), native 90°', '#14866a')]):
    data = json.loads(path.read_text())
    left, top, scale = 40 + i * 650, 100, 35
    d.text((left, 65), label, font=font, fill=color)
    def xy(x, y):
        return left + (x - 68) * scale, top + (y - 59) * scale
    d.rectangle((left, top, left + 560, top + 560), fill='white', outline='#d6dde5')
    for value in range(68, 85, 2):
        x, _ = xy(value, 59)
        d.line((x, top, x, top + 560), fill='#e9edf2')
        d.text((x - 8, top + 565), str(value), font=small, fill='#617184')
    for value in range(59, 76, 2):
        _, y = xy(68, value)
        d.line((left, y, left + 560, y), fill='#e9edf2')
        d.text((left - 25, y - 7), str(value), font=small, fill='#617184')
    rows = [r for r in data['component_envelopes'] if r[1][0] >= 68 and r[1][2] <= 84 and r[1][1] >= 59 and r[1][3] <= 75 and r[2][0] < 6.95 and r[2][1] > 4.05]
    for ref, bounds, z in sorted(rows, key=lambda r: r[0] == 'A_D101'):
        x0, y0, x1, y1 = bounds
        special = ref == 'A_D101'
        d.rectangle((*xy(x0, y0), *xy(x1, y1)), fill='#d6eee6' if special else '#f0f2f5', outline=color if special else '#98a5b3', width=3 if special else 1)
        d.text(xy(x0 + .08, y0 + .08), ref, font=small, fill=color if special else '#617184')
    moved = next(r for r in data['component_envelopes'] if r[0] == 'A_D101')
    d.text((left, 695), f'XY {moved[1]}   Z {moved[2]} mm', font=small, fill='#33465b')
d.text((28, 45), 'Neighbors shown overlap D101’s height range. Full source-bound 3D checks determine clearance.', font=small, fill='#617184')
im.save(H / 'preview.png')
(H / 'preview.json').write_text(json.dumps(dict(view='XY receiving envelopes overlapping D101 Z range', not_a_fit_verdict=True,
    sources={w.relative(p): w.sha(p) for p in [old_path, new_path, Path(__file__)]},
    image_sha256=w.sha(H / 'preview.png')), indent=2) + '\n')
