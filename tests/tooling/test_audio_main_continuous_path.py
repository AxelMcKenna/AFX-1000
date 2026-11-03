"""Continuous routing must respect real clearance through narrow or blocked passages."""
import unittest

from shapely.geometry import box

from hardware.fabrication.audio_main_continuous_path import route
from hardware.fabrication.audio_main_global_controls import SignalScreen


def polygon(geometry):
    return [dict(outer=list(geometry.exterior.coords),holes=[])]


def screen(obstacles):
    objects = [dict(uuid=str(i),net='OTHER',kind='PCB_TRACK',position_mm=[0,0],
                    layers={'B.Cu':polygon(p)}) for i,p in enumerate(obstacles)]
    return SignalScreen(dict(objects=objects,outline=polygon(box(0,0,10,10)),zones=[]))


class ContinuousPath(unittest.TestCase):
    def test_routes_around_foreign_copper(self):
        context = screen([box(4,2,6,7)])
        result = route(context,'CONTROL','B.Cu',[2,4],[8,4],[0,0,10,10])
        self.assertIsNotNone(result)
        self.assertEqual(result['points_mm'][0],[2,4])
        self.assertEqual(result['points_mm'][-1],[8,4])
        self.assertTrue(context.legal('CONTROL','B.Cu',result['points_mm']))
        self.assertGreater(result['length_mm'],6)

    def test_legal_passage_between_grid_rows_is_preserved(self):
        context = screen([box(4,0,6,4.5),box(4,5.2,6,10)])
        result = route(context,'CONTROL','B.Cu',[2,4.85],[8,4.85],[0,0,10,10])
        self.assertIsNotNone(result)
        self.assertTrue(context.legal('CONTROL','B.Cu',result['points_mm']))
        self.assertAlmostEqual(result['length_mm'],6,places=6)

    def test_insufficient_clearance_cannot_be_crossed(self):
        context = screen([box(4,0,6,4.5),box(4,5.05,6,10)])
        self.assertIsNone(route(context,'CONTROL','B.Cu',[2,4.85],[8,4.85],[0,0,10,10]))


if __name__=='__main__':
    unittest.main()
