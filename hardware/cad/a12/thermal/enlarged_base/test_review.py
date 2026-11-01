"""EB01 regression/mutations exercise actual artifacts, not native downloads."""

import copy
import json
import shutil
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .assembly import NS
from .audit import assembly_errors, contract_errors, errors
from .stage import OUT, ROOT
from .verify import EMPTY, mesh, row_errors


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((OUT / "verification.json").read_text())
        cls.analysis = json.loads((OUT / "analysis.json").read_text())
        cls.design = json.loads((ROOT / "design.json").read_text())

    def test_whole_saved_packet_independently_replays(self):
        self.assertEqual(errors(), [])

    def test_missing_required_metal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "metal_geometry.log").write_text("Status: NoError\n")
            self.assertTrue(row_errors("metal_geometry", self.report["cases"]["metal_geometry"], p))

    def test_nonempty_actual_collision_cannot_be_forged_empty(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            name = EMPTY[0]
            shutil.copyfile(OUT / "front_material_positive_control.stl", p / (name + ".stl"))
            (p / (name + ".log")).write_text("Current top level object is empty.\n")
            self.assertTrue(row_errors(name, dict(returncode=1, statistics=None), p))

    def test_bad_boolean_log_is_rejected_even_for_closed_part(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            shutil.copyfile(OUT / "metal_geometry.stl", p / "metal_geometry.stl")
            (p / "metal_geometry.log").write_text("Status: NotManifold\n")
            self.assertTrue(row_errors("metal_geometry", self.report["cases"]["metal_geometry"], p))

    def test_saved_volume_cannot_replace_actual_mesh(self):
        row = copy.deepcopy(self.report["cases"]["metal_geometry"])
        row["statistics"]["volume_mm3"] += 100
        self.assertTrue(row_errors("metal_geometry", row))

    def test_reversed_real_face_breaks_oriented_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "flipped.stl"
            data = bytearray((OUT / "front_material_positive_control.stl").read_bytes())
            data[108:120], data[120:132] = data[120:132], data[108:120]
            p.write_bytes(data)
            self.assertFalse(mesh(p)["closed_oriented_boundary"])

    def test_degenerate_face_cannot_hide_behind_closed_remaining_shell(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            name = "metal_geometry"
            data = bytearray((OUT / (name + ".stl")).read_bytes())
            n = struct.unpack_from("<I", data, 80)[0]
            struct.pack_into("<I", data, 80, n + 1)
            data += struct.pack("<12fH", *([0.0] * 12), 0)
            (p / (name + ".stl")).write_bytes(data)
            (p / (name + ".log")).write_text("Status: NoError\n")
            row = dict(returncode=0, statistics=mesh(p / (name + ".stl")))
            self.assertTrue(row["statistics"]["closed_oriented_boundary"])
            self.assertTrue(row_errors(name, row, p))

    def test_old_foot_location_is_not_enlarged_contract(self):
        d = copy.deepcopy(self.design)
        d["feet"]["centres"][-1][1] = 137
        self.assertTrue(contract_errors(d, self.analysis))

    def test_missing_new_front_bolt_is_rejected(self):
        d = copy.deepcopy(self.design)
        d["shell_fasteners"].pop()
        self.assertTrue(contract_errors(d, self.analysis))

    def test_pin_in_actual_foot_keepout_is_rejected(self):
        a = copy.deepcopy(self.analysis)
        a["pins"]["centres"][0] = [19, 19]
        self.assertTrue(contract_errors(self.design, a))

    def test_no_unmeasured_qualification_flag(self):
        a = copy.deepcopy(self.analysis)
        a["thermal_qualified"] = True
        self.assertTrue(contract_errors(self.design, a))

    def test_component_assembly_missing_family_is_rejected(self):
        source = OUT / "EB01-whole-unit-component-review.3mf"
        manifest = json.loads((OUT / "assembly-manifest.json").read_text())
        with zipfile.ZipFile(source) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        model = ET.fromstring(entries["3D/3dmodel.model"])
        resources = model.find(f"{{{NS}}}resources")
        resources.remove(resources.find(f"{{{NS}}}object"))
        entries["3D/3dmodel.model"] = ET.tostring(model)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "missing-family.3mf"
            with zipfile.ZipFile(target, "w") as z:
                for n, b in entries.items():
                    z.writestr(n, b)
            self.assertTrue(assembly_errors(manifest, target))


if __name__ == "__main__":
    unittest.main()
