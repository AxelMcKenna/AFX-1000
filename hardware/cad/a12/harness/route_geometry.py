"""Analytic tangent-continuous straight/circular wire paths with bounded chords."""

import math


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def scale(a, s):
    return [x * s for x in a]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


class Route:
    def __init__(self, point, tangent, minimum_radius):
        assert len(point) == len(tangent) == 3
        assert all(math.isfinite(v) for v in [*point, *tangent, minimum_radius])
        assert minimum_radius > 0 and math.isclose(math.sqrt(sum(v * v for v in tangent)), 1, abs_tol=1e-12)
        self.point, self.tangent = list(point), list(tangent)
        self.minimum_radius = minimum_radius
        self.pieces = []

    def line(self, length):
        assert math.isfinite(length) and length >= 0
        if length:
            self.pieces.append(
                dict(kind="line", start=list(self.point), tangent=list(self.tangent), length_mm=length)
            )
            self.point = add(self.point, scale(self.tangent, length))

    def arc(self, radius, axis, angle):
        assert all(math.isfinite(v) for v in [radius, *axis, angle])
        assert radius >= self.minimum_radius and 0 < abs(angle) <= math.pi
        assert math.isclose(sum(v * v for v in axis), 1, abs_tol=1e-12)
        assert abs(sum(a * b for a, b in zip(axis, self.tangent))) < 1e-12
        normal = scale(axis, 1 if angle > 0 else -1)
        transverse = cross(normal, self.tangent)
        angle = abs(angle)
        self.pieces.append(
            dict(
                kind="arc",
                start=list(self.point),
                tangent=list(self.tangent),
                transverse=transverse,
                radius_mm=radius,
                angle_rad=angle,
                length_mm=radius * angle,
            )
        )
        self.point = add(
            self.point,
            add(
                scale(self.tangent, radius * math.sin(angle)),
                scale(transverse, radius * (1 - math.cos(angle))),
            ),
        )
        self.tangent = add(scale(self.tangent, math.cos(angle)), scale(transverse, math.sin(angle)))

    def lift(self, height, radius):
        assert self.tangent[2] == 0 or abs(self.tangent[2]) < 1e-12
        assert 0 < height < 2 * radius
        axis = cross(self.tangent, [0, 0, 1])
        angle = math.acos(1 - height / (2 * radius))
        self.arc(radius, axis, angle)
        self.arc(radius, axis, -angle)

    def samples(self, spacing=0.04):
        points = []
        chord_bound = 0
        for piece in self.pieces:
            count = max(1, math.ceil(piece["length_mm"] / spacing))
            for i in range(count):
                u = i / count
                if piece["kind"] == "line":
                    p = add(piece["start"], scale(piece["tangent"], u * piece["length_mm"]))
                else:
                    angle = u * piece["angle_rad"]
                    r = piece["radius_mm"]
                    p = add(
                        piece["start"],
                        add(
                            scale(piece["tangent"], r * math.sin(angle)),
                            scale(piece["transverse"], r * (1 - math.cos(angle))),
                        ),
                    )
                    chord_bound = max(chord_bound, r * (piece["angle_rad"] / count) ** 2 / 8)
                points.append(p)
        points.append(list(self.point))
        return points, dict(
            maximum_centerline_sample_cover_mm=spacing / 2,
            maximum_native_chord_error_bound_mm=chord_bound,
            exact_centerline_length_mm=sum(p["length_mm"] for p in self.pieces),
            minimum_arc_radius_mm=min(
                (p["radius_mm"] for p in self.pieces if p["kind"] == "arc"), default=None
            ),
        )
