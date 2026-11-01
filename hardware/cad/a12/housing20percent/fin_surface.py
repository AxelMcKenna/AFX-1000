"""Actual captured FF02 triangle-surface projection, parameterized grid extent."""

import math
import re


def clip_polygon(poly, rect):
    x0, y0, x1, y1 = rect
    for axis, boundary, sign in [(0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)]:
        if not poly:
            break
        result = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            inside_a = sign * (a[axis] - boundary) >= 0
            inside_b = sign * (b[axis] - boundary) >= 0
            if inside_a:
                result.append(a)
            if inside_a != inside_b:
                t = (boundary - a[axis]) / (b[axis] - a[axis])
                p = [a[i] + t * (b[i] - a[i]) for i in range(2)]
                result.append(p)
        poly = result
    return (
        abs(math.fsum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2
        if poly
        else 0
    )


def line_fraction(a, b, rect):
    lo, hi = 0.0, 1.0
    for axis, lower, upper in [(0, rect[0], rect[2]), (1, rect[1], rect[3])]:
        delta = b[axis] - a[axis]
        if abs(delta) < 1e-12:
            if a[axis] < lower - 1e-9 or a[axis] > upper + 1e-9:
                return 0.0
        else:
            u, v = (lower - a[axis]) / delta, (upper - a[axis]) / delta
            lo = max(lo, min(u, v))
            hi = min(hi, max(u, v))
    return max(0, hi - lo)


def extract(grid, path, width_mm=334, depth_mm=157):
    import numpy as np

    nx, ny = grid
    dx, dy = width_mm / nx, depth_mm / ny
    pts = [[float(v) for v in row] for row in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", path.read_text())]
    vertical = np.zeros((ny, nx))
    root = np.zeros((ny, nx))
    sum_vertical = 0
    sum_root = 0
    for off in range(0, len(pts), 3):
        tri = pts[off : off + 3]
        a, b, c = tri
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
        area = math.sqrt(sum(x * x for x in cross)) / 2
        xy = [p[:2] for p in tri]
        is_top = all(abs(p[2] - 56) < 1e-8 for p in tri)
        is_vertical = abs(cross[2]) < 1e-10
        if not is_top and not is_vertical:
            continue
        if is_top:
            sum_root += area
        else:
            sum_vertical += area
        x0, y0 = min(p[0] for p in tri), min(p[1] for p in tri)
        x1, y1 = max(p[0] for p in tri), max(p[1] for p in tri)
        ii = range(max(0, int(x0 / dx)), min(nx - 1, int(x1 / dx)) + 1)
        jj = range(max(0, int(y0 / dy)), min(ny - 1, int(y1 / dy)) + 1)
        pair = max(((p, q) for p in xy for q in xy), key=lambda pq: math.dist(*pq))
        for j in jj:
            for i in ii:
                rect = [i * dx, j * dy, (i + 1) * dx, (j + 1) * dy]
                if is_top:
                    root[j, i] += clip_polygon(xy, rect)
                else:
                    vertical[j, i] += area * line_fraction(*pair, rect)
    # Root area becomes unavailable for flat-lid convection/radiation; no fin radiation added.
    return (
        vertical * 1e-6,
        root / (dx * dy),
        dict(
            native_vertical_area_m2=sum_vertical * 1e-6,
            native_root_area_m2=sum_root * 1e-6,
            distributed_vertical_area_m2=float(vertical.sum() * 1e-6),
            distributed_root_area_m2=float(root.sum() * 1e-6),
            vertical_area_residual_m2=float((vertical.sum() - sum_vertical) * 1e-6),
            root_area_residual_m2=float((root.sum() - sum_root) * 1e-6),
        ),
    )
