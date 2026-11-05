import unittest
from tools.audio.performance import rmx_performance_path as path


class PerformancePathTests(unittest.TestCase):
    def test_coverage_and_pairing(self):
        cases=path.recipe('fresh')
        self.assertEqual(len(cases),54)
        self.assertEqual({c['effect'] for c in cases},set(path.SCENE))
        self.assertEqual({c['isolate_mode'] for c in cases if c['family']=='isolate'},{1,2,3})
        self.assertEqual({c['release_type'] for c in cases if c['family']=='release'},{0,1,2})
        for c in cases:
            with self.subTest(case=c['name']):
                control=path.control_case(c)
                performance=set('HRTXFLPQAOMDZ')
                self.assertEqual([e for e in c['changes'] if e['type'] in performance],control['changes'])
                self.assertEqual(c['source'],control['source'])
                self.assertEqual([e['frame'] for e in c['changes']],sorted(e['frame'] for e in c['changes']))
                self.assertTrue(all(0<=e['frame']<path.FRAMES for e in c['changes']))
                lines=path.schedule(c).splitlines()
                self.assertEqual(lines[0],'RMX_DRUM_PERFORMANCE 4')
                self.assertEqual(len(lines),6+len(c['changes']))

    def test_holdouts_are_distinct(self):
        first=path.recipe('fresh');second=path.recipe('fresh2')
        self.assertTrue(all(a['changes']!=b['changes'] for a,b in zip(first,second,strict=True)))
        with self.assertRaises(ValueError):path.recipe('unknown')


if __name__=='__main__':unittest.main()
