"""Protect checked, actually filled force pours during a signal-routing pass.

The raster is a conservative planning aid. Native filled-polygon subtraction,
DRC and finite copper extraction are still required after the pass.
"""

import numpy as np
from scipy.ndimage import distance_transform_edt

from ...common.sexpr import children, first
from ..revision26.layout import POWER_NETS
from .copper import LAYERS, Mesh


class ForceGuard:
    def __init__(self, tree, router, step):
        self.step = step
        self.distances = {}
        for net in sorted(POWER_NETS):
            raster = Mesh.__new__(Mesh)
            raster.x = router.xx[:, 0]
            raster.y = router.yy[0, :]
            raster.mask = np.zeros((6, router.nx, router.ny), dtype=bool)
            for zone in children(tree, "zone"):
                name = (
                    str(first(zone, "net_name")[1])
                    if children(zone, "net_name")
                    else str(first(zone, "net")[-1]) if children(zone, "net") else ""
                )
                if name.lstrip("/") != net:
                    continue
                for poly in children(zone, "filled_polygon"):
                    points = [
                        (float(point[1]) - 100, float(point[2]) - 100) for point in first(poly, "pts")[1:]
                    ]
                    raster.polygon(LAYERS.index(str(first(poly, "layer")[1])), points)
            for layer in range(6):
                if raster.mask[layer].any():
                    self.distances[(net, layer)] = distance_transform_edt(
                        ~raster.mask[layer], sampling=step
                    ).astype(np.float32)
        assert self.distances, "No native filled force polygons found"

    def apply(self, net, blocked, drills, width, clearance=0.2):
        # Include one full diagonal cell beyond the required clearance, rather
        # than treating cell-centre sampling as exact polygon separation.
        guard = self.step * 1.415 + 0.02
        for (other, layer), distance in self.distances.items():
            if other == net:
                continue
            blocked[layer] |= distance <= clearance + width / 2 + guard
            drills |= distance <= clearance + 0.3 + guard
        return blocked, drills
