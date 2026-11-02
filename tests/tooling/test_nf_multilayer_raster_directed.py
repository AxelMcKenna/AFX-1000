"""Exact clearance routing must recover legal corridors without crossing barriers."""
import time
from shapely.geometry import box
from tests.tooling import test_nf_multilayer_raster as base
from hardware.fabrication.nf_multilayer_raster_directed import route_multi, LAYERS


class DirectedLayerChanges(base.LayerChanges):
    def run_route(self, board):
        a = dict(point=(1, 4), runs=[], vias=[], cost=0, group='a', layers=['In2.Cu'])
        b = dict(point=(9, 4), runs=[], vias=[], cost=0, group='b')
        return route_multi(board, 'signal', [a], {'In2.Cu': [b]},
                           time.monotonic() + 5, max_visits=100000)

    def corridor(self, half_width):
        board = base.LayerBoard()
        walls = [box(-1, -1, 11, 4-half_width), box(-1, 4+half_width, 11, 9)]
        board.geometry = {layer: [('other', wall, .281) for wall in walls]
                          for layer in LAYERS}
        board.via_geometry = [(None, board.outline, 'KEEPOUT')]
        return board

    def test_legal_corridor_inside_conservative_raster_halo(self):
        board = self.corridor(.30)
        route = self.run_route(board)
        self.assertIsNotNone(route)
        self.assertEqual(route['vias'], [])
        for layer, points in route['runs']:
            self.assertTrue(board.legal('signal', layer, points))

    def test_corridor_below_required_clearance_is_rejected(self):
        self.assertIsNone(self.run_route(self.corridor(.27)))
