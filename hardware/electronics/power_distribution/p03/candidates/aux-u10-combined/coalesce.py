"""Merge only exactly touching collinear copper of identical net/layer/width.

The copper union is unchanged. This prevents native dangling-tail cleanup from
peeling hundreds of0.125mm fragments one refill at a time. Gaps are not bridged,
widths/nets/layers are never combined, and non-axis-aligned segments stay intact.
"""

import json

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import OUT, ROOT, coded, named


def merge(tree):
    groups = {}
    for track in children(tree, "segment"):
        x0, y0 = map(float, first(track, "start")[1:3])
        x1, y1 = map(float, first(track, "end")[1:3])
        if y0 == y1:
            axis, fixed, ends = "h", y0, sorted((x0, x1))
        elif x0 == x1:
            axis, fixed, ends = "v", x0, sorted((y0, y1))
        else:
            continue
        key = (
            str(first(track, "net")[1]),
            str(first(track, "layer")[1]),
            float(first(track, "width")[1]),
            axis,
            fixed,
        )
        groups.setdefault(key, []).append((ends[0], ends[1], track))
    removed = 0
    added = 0
    for (net, layer, width, axis, fixed), rows in groups.items():
        rows.sort(key=lambda r: (r[0], r[1]))
        batches = []
        for lo, hi, obj in rows:
            if batches and lo <= batches[-1][1]:
                batches[-1][1] = max(batches[-1][1], hi)
                batches[-1][2].append(obj)
            else:
                batches.append([lo, hi, [obj]])
        for lo, hi, objects in batches:
            if len(objects) < 2:
                continue
            for obj in objects:
                tree.remove(obj)
                removed += 1
            start, end = ((lo, fixed), (hi, fixed)) if axis == "h" else ((fixed, lo), (fixed, hi))
            tree.append(
                read_sexpr(
                    f'(segment(start {start[0]} {start[1]})(end {end[0]} {end[1]})(width {width})(layer "{layer}")(net {net}))'
                )
            )
            added += 1
    return dict(
        original_segments_removed=removed,
        exact_union_segments_added=added,
        net_layer_width_or_gap_changed=False,
    )


def implement():
    p = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(p.read_text()))
    r = merge(tree)
    p.write_text(sexpr(named(tree)) + "\n")
    (OUT / "collinear-copper-cleanup.json").write_text(json.dumps(r, indent=2) + "\n")
    print(r)


if __name__ == "__main__":
    implement()
