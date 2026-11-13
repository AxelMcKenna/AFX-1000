"""Source-bound section schematic of the two conditional mounting stacks."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from hardware.cad.assembly_workflow import workflow as w

H = Path(__file__).resolve().parent
source = H.parent / 'main-fasteners-r1'
budget = json.loads((source / 'budget.json').read_text())
im = Image.new('RGB', (1320, 760), '#f5f7fa')
d = ImageDraw.Draw(im)
font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
title = ImageFont.truetype(font_path, 25)
font = ImageFont.truetype(font_path, 17)
small = ImageFont.truetype(font_path, 14)
d.text((25, 18), 'Main-board mounting stacks — conditional section schematic', font=title, fill='#182b40')
d.text((25, 52), 'Threads, drive sockets and underhead fillets omitted. Physical seating, retention and loaded feet clearance require qualification.', font=small, fill='#617184')
for index, kind in enumerate(['signal', 'power']):
    b = budget['budgets'][kind]
    cx = 205 + index * 650
    post = sum(b['post_seat_z_mm']) / 2
    length = 10 if kind == 'signal' else 12
    underhead = post + 1.6 + .3
    tip = underhead - length
    def xy(x, z):
        return cx + 24 * x, 520 - 28 * z
    def rect(x0, z0, x1, z1, fill):
        d.rectangle((*xy(x0, z1), *xy(x1, z0)), fill=fill, outline='#45576a')
    d.text((cx - 170, 88), f'{kind.title()} board: M2 × {length} mm', font=font, fill='#182b40')
    # Plastic support shown through opposing nut flats; the floor is datum Z0.
    for sign in [-1, 1]:
        x0, x1 = sorted([sign * 1.2, sign * 3.6])
        rect(x0, 1.8, x1, post, '#d5dee7')
        x0, x1 = sorted([sign * 2.1, sign * 3.6])
        rect(x0, 0, x1, 1.8, '#d5dee7')
        x0, x1 = sorted([sign * 1.2, sign * 4.5])
        rect(x0, post, x1, post + 1.6, '#91b6de')
        x0, x1 = sorted([sign * 1.1, sign * 2.25])
        rect(x0, post + 1.6, x1, underhead, '#c3b47c')
        x0, x1 = sorted([sign * 1., sign * 2.])
        rect(x0, .2, x1, 1.8, '#c3b47c')
    rect(-1, tip, 1, underhead, '#72808e')
    rect(-1.9, underhead, 1.9, underhead + 2, '#72808e')
    for z, label in [(post + .8, 'PCB: 1.6 mm nominal'), (underhead + 1, 'Cap head + washer'), (1.8, 'Nut seats at Z1.8'), (tip, f'Nominal tip: Z{tip:.2f}')]:
        x, y = xy(4.7, z)
        d.line((cx + 50, y, x, y), fill='#738396')
        d.text((x + 7, y - 9), label, font=small, fill='#33465b')
    for z, color in [(0, '#8a96a4'), (-6, '#b18736')]:
        x0, y = xy(-5.2, z)
        x1, _ = xy(5.2, z)
        for x in range(int(x0), int(x1), 10):
            d.line((x, y, min(x + 5, x1), y), fill=color)
    d.text((cx - 155, 530), 'Floor datum Z0', font=small, fill='#617184')
    d.text((cx - 155, 620), f'Minimum tip/table gap: {b["table_gap_min_mm"]:.2f} mm', font=font, fill='#805f24')
    d.text((cx - 155, 691), 'Table only if loaded floor clearance ≥6 mm', font=small, fill='#805f24')
    d.text((cx - 155, 719), f'Minimum full thread beyond nut: {b["full_thread_beyond_nut_min_mm"]:.2f} mm', font=small, fill='#33465b')
im.save(H / 'preview.png')
(H / 'preview.json').write_text(json.dumps(dict(view='Nominal section schematic with conditional receiving minima',
    underhead_fillets_and_threads_omitted=True, physical_fit_qualified=False,
    source_sha256={w.relative(p): w.sha(p) for p in [Path(__file__), source / 'parts.scad', source / 'budget.json']},
    image_sha256=w.sha(H / 'preview.png')), indent=2) + '\n')
