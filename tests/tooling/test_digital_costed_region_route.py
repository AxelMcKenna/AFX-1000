import math
import unittest
from hardware.fabrication.digital_costed_region_route import shortest_path


class CostedRegionGraphTests(unittest.TestCase):
    def test_measured_detour_replaced_by_extra_layer_transitions(self):
        nodes=[('F',0,(0,0)),('F',0,(10,0)),('F',0,(1,0)),('B',0,(1,0)),('B',0,(9,0)),('F',0,(9,0))]
        members={('F',0):[0,1,2,5],('B',0):[3,4]}
        cross={2:[(3,2)],3:[(2,2)],4:[(5,2)],5:[(4,2)]}
        measured={(0,1):100,(0,5):99,(1,2):99,(2,5):98}
        self.assertEqual(shortest_path(nodes,members,cross,{0},{1},measured),[0,2,3,4,5,1])

    def test_blocked_measured_edge_is_not_used(self):
        nodes=[('F',0,(0,0)),('F',0,(1,0))]
        self.assertIsNone(shortest_path(nodes,{('F',0):[0,1]}, {},{0},{1},{(0,1):math.inf}))

    def test_terminal_existing_via_accepts_any_available_face(self):
        nodes=[('F',0,(0,0)),('B',0,(0,0)),('B',0,(3,0))]
        self.assertEqual(shortest_path(nodes,{('F',0):[0],('B',0):[1,2]}, {},{0,1},{2},{}),[1,2])

    def test_rejected_via_candidate_cannot_reappear(self):
        nodes=[('F',0,(0,0)),('F',0,(1,0)),('B',0,(1,0)),('B',0,(2,0))]
        self.assertIsNone(shortest_path(nodes,{('F',0):[0,1],('B',0):[2,3]}, {1:[(2,2)],2:[(1,2)]},{0},{3},{},forbidden={1,2}))


if __name__=='__main__':
    unittest.main()
