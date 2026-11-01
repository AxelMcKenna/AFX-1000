"""Cubic Bezier certificates independent of sampled curvature.

Velocity is quadratic Bernstein, acceleration linear. Their cross product is
cubic Bernstein. Convex-hull norm upper bounds and distance-to-velocity-AABB
lower bounds enclose curvature on every recursively subdivided interval.
"""

import math
from decimal import Decimal, localcontext


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, k):
    return [x * k for x in a]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    return sum(x * x for x in a).sqrt()


def split(cp):
    half = Decimal(".5")
    a = [scale(add(x, y), half) for x, y in zip(cp, cp[1:])]
    b = [scale(add(x, y), half) for x, y in zip(a, a[1:])]
    c = scale(add(b[0], b[1]), half)
    return [cp[0], a[0], b[0], c], [c, b[1], a[2], cp[3]]


def certificate(control, required_radius=9.6393, max_depth=24):
    with localcontext() as ctx:
        ctx.prec = 70
        cp = [[Decimal(str(x)) for x in p] for p in control]
        guard = Decimal("1e-45")
        limit = 1 / Decimal(str(required_radius))
        leaves = []
        rejected = []
        pending = [(cp, Decimal(0), Decimal(1), 0)]
        while pending:
            p, lo, hi, depth = pending.pop()
            v = [scale(sub(y, x), Decimal(3)) for x, y in zip(p, p[1:])]
            a = [scale(sub(y, x), Decimal(2)) for x, y in zip(v, v[1:])]
            c = [
                cross(v[0], a[0]),
                scale(add(scale(cross(v[1], a[0]), Decimal(2)), cross(v[0], a[1])), Decimal(1) / 3),
                scale(add(cross(v[2], a[0]), scale(cross(v[1], a[1]), Decimal(2))), Decimal(1) / 3),
                cross(v[2], a[1]),
            ]
            upper = max(norm(x) for x in c) + guard
            nearest = []
            for axis in range(3):
                low = min(q[axis] for q in v)
                high = max(q[axis] for q in v)
                nearest.append(low if low > 0 else -high if high < 0 else Decimal(0))
            speed = max(Decimal(0), norm(nearest) - guard)
            bound = upper / speed**3 if speed > 0 else Decimal("Infinity")
            if bound < limit:
                leaves.append(
                    dict(
                        t0=str(lo),
                        t1=str(hi),
                        depth=depth,
                        kappa_upper_per_mm=math.nextafter(float(bound), math.inf),
                        speed_lower_local_parameter=math.nextafter(float(speed), 0),
                    )
                )
            elif depth >= max_depth:
                rejected.append(dict(t0=str(lo), t1=str(hi), depth=depth, kappa_upper_per_mm=str(bound)))
            else:
                left, right = split(p)
                mid = (lo + hi) / 2
                pending.extend([(right, mid, hi, depth + 1), (left, lo, mid, depth + 1)])
                if len(pending) + len(leaves) > 100000:
                    raise ValueError("Certificate subdivision budget exceeded")
        max_k = max((r["kappa_upper_per_mm"] for r in leaves), default=math.inf)
        velocity = [scale(sub(y, x), Decimal(3)) for x, y in zip(cp, cp[1:])]
        acceleration = [scale(sub(y, x), Decimal(2)) for x, y in zip(velocity, velocity[1:])]
        length_upper = sum(norm(sub(y, x)) for x, y in zip(cp, cp[1:])) + guard
        max_accel = max(norm(x) for x in acceleration) + guard
        return dict(
            method="70-digit Decimal Bernstein interval subdivision; velocity-AABB lower/cross-Bernstein norm upper",
            required_radius_mm=required_radius,
            decimal_operation_guard=str(guard),
            max_depth=max_depth,
            certified=not rejected and bool(leaves),
            radius_lower_mm=math.nextafter(1 / max_k, 0) if math.isfinite(max_k) and max_k > 0 else 0,
            curvature_upper_per_mm=max_k,
            control_polygon_length_upper_mm=math.nextafter(float(length_upper), math.inf),
            second_derivative_norm_upper=math.nextafter(float(max_accel), math.inf),
            leaves=leaves,
            rejected_intervals=rejected,
        )


def chord_contract(control, intervals):
    if intervals < 1:
        raise ValueError("Positive intervals required")
    v = [[3 * (b - a) for a, b in zip(x, y)] for x, y in zip(control, control[1:])]
    a = [[2 * (b - a) for a, b in zip(x, y)] for x, y in zip(v, v[1:])]
    accel = max(math.sqrt(sum(x * x for x in p)) for p in a) + 1e-10
    return dict(
        intervals=intervals,
        second_derivative_norm_upper=accel,
        chord_error_bound_mm=accel / (8 * intervals**2),
        maximum_parameter_speed_upper=max(math.sqrt(sum(x * x for x in p)) for p in v) + 1e-10,
        continuous_sample_cover_bound_mm=(max(math.sqrt(sum(x * x for x in p)) for p in v) + 1e-10)
        / (2 * intervals),
    )


def points(control, parameters):
    import numpy as np

    p = np.array(control, float)
    t = np.asarray(parameters)[:, None]
    u = 1 - t
    return u**3 * p[0] + 3 * u * u * t * p[1] + 3 * u * t * t * p[2] + t**3 * p[3]
