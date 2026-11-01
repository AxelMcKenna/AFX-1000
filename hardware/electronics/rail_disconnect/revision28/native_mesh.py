"""Source-hashed native pad polygons adapted to the finite sheet/barrel mesh.

Physical pad shapes and duplicate logical lands are retained. Material, contact,
annular-spreading and mesh assumptions remain explicit and unqualified.
"""

import numpy as np

from .copper import LAYERS, Mesh, children, first


def require_domain_coverage(tree, net, bounds, geometry=None):
    """Reject clipped physical copper before any cell-centre rasterization."""
    assert len(bounds) == 2 and all(np.isfinite(v) and v > 0 for v in bounds)

    def covered(points, label, radius=0):
        for px, py in points:
            x, y = float(px) - 100, float(py) - 100
            assert (
                -1e-6 <= x - radius
                and x + radius <= bounds[0] + 1e-6
                and -1e-6 <= y - radius
                and y + radius <= bounds[1] + 1e-6
            ), ("Copper outside extraction domain", label, (x, y), radius, bounds)

    def same_net(node):
        return children(node, "net") and str(first(node, "net")[-1]).lstrip("/") == net

    for zone in children(tree, "zone"):
        if same_net(zone):
            for polygon in children(zone, "filled_polygon"):
                covered([p[1:3] for p in first(polygon, "pts")[1:]], "filled polygon")
    for segment in children(tree, "segment"):
        if same_net(segment):
            covered(
                [first(segment, end)[1:3] for end in ("start", "end")],
                "track including round caps",
                float(first(segment, "width")[1]) / 2,
            )
    for via in children(tree, "via"):
        if same_net(via):
            covered([first(via, "at")[1:3]], "via land", float(first(via, "size")[1]) / 2)
    if geometry is not None:
        for pad in geometry["pad_polygons"]:
            if pad["net"] == net:
                for polygons in pad["layers"].values():
                    for polygon in polygons:
                        covered(polygon["outer"], (pad["ref"], pad["pin"]))
    return dict(
        bounds_mm=list(bounds),
        full_native_pad_coverage_checked=geometry is not None,
        physical_copper_clipping_detected=False,
    )


class NativePadMesh(Mesh):
    def __init__(self, tree, net, step, geometry, bounds=(156, 45.25)):
        # Existing tracks, native fills and finite barrels use the original
        # engine. Every pad is then restored from actual native polygons.
        self.domain_coverage = require_domain_coverage(tree, net, bounds, geometry)
        bare = [node for node in tree if not (isinstance(node, list) and node and node[0] == "footprint")]
        super().__init__(bare, net, step, bounds=bounds)
        for pad in geometry["pad_polygons"]:
            if pad["net"] != net:
                continue
            terminal = self.pads.setdefault((pad["ref"], str(pad["pin"])), {})
            for layername, polygons in pad["layers"].items():
                layer = LAYERS.index(layername)
                region = np.zeros((len(self.x), len(self.y)), bool)
                for polygon in polygons:
                    raster = Mesh.__new__(Mesh)
                    raster.x, raster.y = self.x, self.y
                    raster.mask = np.zeros((1, len(self.x), len(self.y)), bool)
                    raster.polygon(0, [(x - 100, y - 100) for x, y in polygon["outer"]])
                    outer = raster.mask[0].copy()
                    for hole in polygon["holes"]:
                        raster.mask[:] = False
                        raster.polygon(0, [(x - 100, y - 100) for x, y in hole])
                        outer &= ~raster.mask[0]
                    region |= outer
                self.mask[layer] |= region
                terminal[layer] = terminal.get(layer, np.zeros_like(region)) | region
            dx, dy = pad["drill_mm"]
            if dx or dy:
                assert abs(dx - dy) < 1e-9, "Slotted plated-hole wall extraction is not implemented"
                xy = tuple(value - 100 for value in pad["position_mm"])
                self.holes.append((xy, dx, min(pad["nominal_size_mm"]) / 2))
        # Restoring a pad must never fill the actual drills of overlapping VIP
        # structures. These are finite cylindrical plated walls, not solid vias.
        for xy, drill, _ in self.holes:
            hole = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 < drill**2 / 4
            self.mask[:, hole] = False
