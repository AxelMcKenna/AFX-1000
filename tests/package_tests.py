#!/usr/bin/env python3
"""Portable package checks. No signing, network, app launch or Mac tools."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("package_macos", Path(__file__).resolve().parents[1] / "tools/package_macos.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def test_digest_matches_standard_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a"
            path.write_bytes(b"RMX\0" * 300000)
            self.assertEqual(package.digest(path), hashlib.sha256(path.read_bytes()).hexdigest())

    def test_cache_values_keep_colons_and_equals(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            (build / "CMakeCache.txt").write_text("# comment\n// help\nCMAKE_BUILD_TYPE:STRING=Release\nROOT:PATH=/tmp/a:b=c\nRMX_BUILD_PLUGINS:BOOL=ON\n")
            values = package.cache(build)
            self.assertEqual(values["CMAKE_BUILD_TYPE"], "Release")
            self.assertEqual(values["ROOT"], "/tmp/a:b=c")
            self.assertEqual(values["RMX_BUILD_PLUGINS"], "ON")

    def test_source_inventory_excludes_build_cache_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("CMakeLists.txt", "README.md", "THIRD_PARTY_NOTICES.md", "src/main.cpp",
                         "pyproject.toml", "uv.lock", ".python-version", ".venv/lib/private.py",
                         "firmware/daisy/Makefile", "firmware/daisy/build/secret.cpp",
                         "tools/__pycache__/private.py", "docs/build/private.md",
                         "assets/panel.png", "prototypes/web/app.js", "src/macos/Info.plist",
                         "build/src/private.cpp", "docs/.DS_Store"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(path)
            (root / "src/link.cpp").symlink_to(root / "README.md")
            with mock.patch.object(package, "ROOT", root):
                names = [p.relative_to(root).as_posix() for p in package.source_files()]
            self.assertEqual(names, sorted(["CMakeLists.txt", "README.md", "THIRD_PARTY_NOTICES.md",
                                          "assets/panel.png", "firmware/daisy/Makefile", "src/main.cpp",
                                          "pyproject.toml", "uv.lock", ".python-version",
                                          "prototypes/web/app.js", "src/macos/Info.plist"]))

    def test_archive_hash_manifest_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [root / "README.md", root / "build-app.sh", root / "THIRD_PARTY_NOTICES.md"]
            for path in files:
                path.write_text(path.name + "\n")
            (root / "build-app.sh").chmod(0o755)
            destination = root / "source.zip"
            with mock.patch.object(package, "ROOT", root):
                hashes = package.source_zip(destination, files, b"third-party notices\n")
            with zipfile.ZipFile(destination) as archive:
                manifest = json.loads(archive.read("RMX-source/source-manifest.json"))
                self.assertEqual(manifest, hashes)
                for path in files:
                    data = archive.read("RMX-source/" + path.name)
                    self.assertEqual(hashlib.sha256(data).hexdigest(), manifest[path.name])
                executable = archive.getinfo("RMX-source/build-app.sh")
                self.assertTrue((executable.external_attr >> 16) & 0o111)
            with mock.patch.object(package, "ROOT", root):
                with self.assertRaises(FileExistsError):
                    package.source_zip(destination, files, b"notices")

    def test_all_source_entries_have_fixed_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text("Source snapshot\n")
            with mock.patch.object(package, "ROOT", root):
                package.source_zip(root / "a.zip", [source], b"notices\n")
                os.utime(source, (1234567890, 1234567890))
                package.source_zip(root / "b.zip", [source], b"notices\n")
            with zipfile.ZipFile(root / "a.zip") as archive:
                for entry in archive.infolist():
                    self.assertEqual(entry.date_time, (2026, 1, 1, 0, 0, 0), entry.filename)
            self.assertEqual((root / "a.zip").read_bytes(), (root / "b.zip").read_bytes())


if __name__ == "__main__":
    unittest.main()
