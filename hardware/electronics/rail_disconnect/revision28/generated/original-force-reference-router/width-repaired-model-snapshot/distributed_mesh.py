"""Finite annular sheets with distributed cylindrical-wall connections.

No annular copper cells are shorted together. Equal angular wall sectors attach
to their nearest resolved physical copper cells at each actual layer. The wall
sectors retain finite longitudinal and circumferential conductance using a
cylindrical finite-volume wall model. This remains a diagnostic model.
Native pad approximation, finite grid and all process/contact assumptions remain
unqualified. This module does not change shared copper.Mesh or P03 behavior.
"""

import math

import numpy as np

from .copper import ALPHA, LAYERS, RHO20, RHO_BARREL20, STACKUP
from .native_mesh import NativePadMesh


class DistributedBarrelMesh(NativePadMesh):
    angular_sectors = 32

    def network(self, thickness=0.07, temp=85, plating=0.025):
        assert thickness > 0 and plating > 0
        count = int(np.count_nonzero(self.mask))
        ids = np.full(self.mask.shape, -1, dtype=np.int32 if count < 2**31 else np.int64)
        ids[self.mask] = np.arange(count)
        us = []
        vs = []
        gs = []
        rho = RHO20 * (1 + ALPHA * (temp - 20))
        sheet = thickness / rho
        for axis in (1, 2):
            one = [slice(None)] * 3
            two = [slice(None)] * 3
            one[axis] = slice(None, -1)
            two[axis] = slice(1, None)
            a, b = ids[tuple(one)], ids[tuple(two)]
            valid = (a >= 0) & (b >= 0)
            u, v = a[valid], b[valid]
            us.append(u)
            vs.append(v)
            gs.append(np.full(len(u), sheet))
        barrel_u = []
        barrel_v = []
        barrel_g = []
        rows = []
        seen = set()
        for xy, drill, radius in self.holes:
            identity = (tuple(xy), drill, radius)
            assert identity not in seen, "Duplicate physical hole would double wall conductance"
            seen.add(identity)
            ix = np.flatnonzero(abs(self.x - xy[0]) <= radius)
            iy = np.flatnonzero(abs(self.y - xy[1]) <= radius)
            assert len(ix) and len(iy), "Unresolved barrel; refine grid"
            xx, yy = np.meshgrid(self.x[ix], self.y[iy], indexing="ij")
            ring = (xx - xy[0]) ** 2 + (yy - xy[1]) ** 2 <= radius**2
            angles = np.arange(self.angular_sectors) * 2 * math.pi / self.angular_sectors
            wall_radius = drill / 2 + plating / 2
            targets = np.column_stack(
                (xy[0] + wall_radius * np.cos(angles), xy[1] + wall_radius * np.sin(angles))
            )
            terminals = []
            max_error = 0
            for layer in range(len(LAYERS)):
                physical = ring & self.mask[layer][np.ix_(ix, iy)]
                cx, cy = np.nonzero(physical)
                assert len(cx), "Unresolved physical annular layer; refine grid"
                positions = np.column_stack((self.x[ix[cx]], self.y[iy[cy]]))
                distances = np.sum((targets[:, None, :] - positions[None, :, :]) ** 2, axis=2)
                nearest = np.argmin(distances, axis=1)
                max_error = max(max_error, float(np.sqrt(distances[np.arange(len(targets)), nearest]).max()))
                terminals.append(ids[layer, ix[cx[nearest]], iy[cy[nearest]]])
            area = math.pi * ((drill / 2 + plating) ** 2 - (drill / 2) ** 2)
            depths = STACKUP["copper_center_nominal_depth_mm"]
            ratio = STACKUP["laminate_thickness_mm"]["maximum"] / STACKUP["laminate_thickness_mm"]["nominal"]
            barrel_rho = RHO_BARREL20 * (1 + ALPHA * (temp - 20))
            for layer in range(len(LAYERS) - 1):
                length = (depths[layer + 1] - depths[layer]) * ratio
                conductance = area / self.angular_sectors / (barrel_rho * length)
                barrel_u.extend(terminals[layer])
                barrel_v.extend(terminals[layer + 1])
                barrel_g.extend([conductance] * self.angular_sectors)
            lengths = np.diff(depths) * ratio
            heights = np.concatenate(([lengths[0] / 2], (lengths[:-1] + lengths[1:]) / 2, [lengths[-1] / 2]))
            arc_length = wall_radius * 2 * math.pi / self.angular_sectors
            for layer, height in enumerate(heights):
                u = terminals[layer]
                v = np.roll(u, -1)
                keep = u != v
                barrel_u.extend(u[keep])
                barrel_v.extend(v[keep])
                barrel_g.extend([plating * height / (barrel_rho * arc_length)] * int(keep.sum()))
            rows.append(
                dict(
                    center_mm=xy,
                    drill_mm=drill,
                    wall_mm=plating,
                    actual_land_radius_mm=radius,
                    wall_cross_section_mm2=area,
                    angular_sectors=self.angular_sectors,
                    max_attachment_displacement_mm=max_error,
                )
            )
        if barrel_u:
            us.append(np.asarray(barrel_u))
            vs.append(np.asarray(barrel_v))
            gs.append(np.asarray(barrel_g))

        def electrodes(pairs):
            pieces = []
            for ref, pin in pairs:
                for layer, region in self.pads[(ref, str(pin))].items():
                    pieces.append(ids[layer][region & self.mask[layer]])
            return np.concatenate(pieces) if pieces else np.array([], dtype=int)

        self.distributed_barrel_diagnostic = dict(
            within_layer_annuli_shorted=False,
            physical_holes=len(rows),
            barrels=rows,
            wall_circumferential_conduction_included=True,
            wall_attachment_and_grid_convergence_qualified=False,
            certified_resistance_upper_bound=False,
            physical_qualified=False,
        )
        return dict(
            u=np.concatenate(us), v=np.concatenate(vs), g=np.concatenate(gs), n=count, electrodes=electrodes
        )
