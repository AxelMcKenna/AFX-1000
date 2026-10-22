"""Build provenance must reject missing or stale translation units."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('firmware_checker', Path(__file__).resolve().parents[1] / 'tools/check_firmware.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class Dependencies(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / 'build'
        self.build.mkdir()
        self.source = self.root / 'main.cpp'
        self.header = self.root / 'header with space.h'
        self.makefile = self.root / 'Makefile'
        self.obj = self.build / 'main.o'
        self.dep = self.build / 'main.d'
        self.elf = self.build / 'firmware.elf'
        for path in (self.source, self.header, self.makefile, self.obj, self.elf):
            path.write_text(path.name)
        self.dep.write_text('build/main.o: main.cpp \\\n header\\ with\\ space.h\nheader\\ with\\ space.h:\n')
        # Deterministic times avoid sleeps and filesystem timestamp granularity.
        for path in (self.source, self.header, self.makefile, self.dep):
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
        os.utime(self.obj, ns=(2_000_000_000, 2_000_000_000))
        os.utime(self.elf, ns=(3_000_000_000, 3_000_000_000))

    def inspect(self):
        return checker.translation_unit(self.source, self.build, self.root, self.elf, [self.makefile])

    def test_current_and_content_fingerprint(self):
        before = self.inspect()
        self.assertEqual(before['dependency_count'], 3)
        self.header.write_text('changed despite preserved mtime')
        os.utime(self.header, ns=(1_000_000_000, 1_000_000_000))
        self.assertNotEqual(before['dependencies_sha256'], self.inspect()['dependencies_sha256'])

    def test_header_and_makefile_edits_require_recompile(self):
        for path in (self.header, self.makefile):
            with self.subTest(path=path.name):
                os.utime(path, ns=(4_000_000_000, 4_000_000_000))
                with self.assertRaisesRegex(ValueError, 'Stale object'):
                    self.inspect()
                os.utime(path, ns=(1_000_000_000, 1_000_000_000))

    def test_object_requires_relink(self):
        os.utime(self.obj, ns=(4_000_000_000, 4_000_000_000))
        with self.assertRaisesRegex(ValueError, 'has not linked'):
            self.inspect()

    def test_missing_dependencies_are_rejected(self):
        self.dep.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing object/header'):
            self.inspect()

    def test_empty_dependency_file(self):
        self.dep.write_text('')
        with self.assertRaisesRegex(ValueError, 'Empty dependency file'):
            self.inspect()

    def test_wrong_target_and_missing_source(self):
        self.dep.write_text('build/other.o: main.cpp\n')
        with self.assertRaisesRegex(ValueError, 'Unexpected dependency target'):
            self.inspect()
        self.dep.write_text('build/main.o: Makefile\n')
        with self.assertRaisesRegex(ValueError, 'omits its source'):
            self.inspect()


if __name__ == '__main__':
    unittest.main()
