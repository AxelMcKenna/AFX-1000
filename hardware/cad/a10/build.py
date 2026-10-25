"""Export and check the A10 print inventory, 3MF master and review images."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from generate import schedule

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = REPO / "build/artifacts/cad/a10"


def inventory():
    buttons, knobs = schedule()
    result = []

    def add(
        name,
        part,
        quantity=1,
        index=None,
        material="opaque",
        purpose="mechanical prototype",
    ):
        result.append(
            dict(
                name=name,
                part=part,
                quantity=quantity,
                index=index,
                material=material,
                purpose=purpose,
            )
        )

    for part in (
        "base",
        "panel",
        "rear_panel",
        "guide_plate",
        "lever_bracket",
        "lever_arm",
        "touch_backer",
    ):
        add(part, part)
    for i, b in enumerate(buttons):
        add("button-" + b[0], "button", index=i)
    groups = {}
    for i, b in enumerate(buttons):
        key = json.dumps(b[8])
        if key not in groups:
            groups[key] = [i, 0]
        groups[key][1] += 1
    for i, (index, count) in enumerate(groups.values()):
        add("switch-holder-" + str(i + 1), "holder", count, index)
    add("retaining-clip", "clip", len(buttons))
    groups = {}
    for i, k in enumerate(knobs):
        key = (k[3], k[4])
        if key not in groups:
            groups[key] = [i, 0]
        groups[key][1] += 1
    for (diameter, height), (index, count) in groups.items():
        add(f"knob-{diameter:g}x{height:g}", "knob", count, index)
    add("selector-cap", "selector_cap", 2)
    for name, quantity in [
        ("touch_lens", 1),
        ("ring_lens", 1),
        ("meter_lens", 2),
        ("bank_lens", 4),
        ("display_lens", 1),
    ]:
        add(name, name, quantity, material="transparent or translucent")
    add("panel-fit-coupon", "fit_coupon", purpose="fit test")
    add("shaft-fit-coupon", "shaft_coupon", purpose="fit test")
    return result


def native(
    executable,
    name,
    part,
    extension,
    extra=(),
    index=None,
    empty=False,
    backend="Manifold",
):
    target = OUT / "checks" if empty or part in ("all_holders", "all_keys") else OUT
    target.mkdir(parents=True, exist_ok=True)
    destination = target / (name + "." + extension)
    command = [executable, "--hardwarnings"]
    if extension == "stl":
        command += ["--backend", backend, "--export-format", "binstl"]
    command += ["-D", "part=" + json.dumps(part)]
    if index is not None:
        command += ["-D", f"index={index}"]
    command += list(extra) + ["-o", str(destination), str(ROOT / "assembly.scad")]
    result = subprocess.run(command, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (OUT / (name + ".log")).write_text(log)
    if empty:
        if result.returncode == 1 and "Current top level object is empty." in log:
            destination.unlink(missing_ok=True)
            return "empty intersection"
        if (
            result.returncode == 0
            and destination.exists()
            and name in ("chassis_collision", "optics_collision")
        ):
            return check_intended_contacts(destination, name)
        raise RuntimeError(
            name
            + " collision check failed; inspect "
            + str(destination)
            + " and "
            + str(OUT / (name + ".log"))
        )
    if result.returncode:
        raise RuntimeError(name + " failed:\n" + log[-4000:])
    return destination


def check_intended_contacts(path, name):
    """Accept only named mounting/lens seating planes, never a volume tolerance."""
    import numpy as np
    import trimesh

    if name == "chassis_collision":
        line = next(
            line
            for line in (ROOT / "generated/components.scad").read_text().splitlines()
            if line.startswith("board_mounts = ")
        )
        mounts = json.loads(line.split(" = ", 1)[1].removesuffix(";"))
        regions = []
        for m in mounts:
            if m[0] == "lever":
                continue
            diameter = 7.2 if m[0] in ("audio_carrier", "dsp_carrier", "led_driver", "input_power") else 6
            regions.append(
                (
                    m[0],
                    m[1] - diameter / 2,
                    m[2] - diameter / 2,
                    m[3],
                    diameter,
                    diameter,
                )
            )
    else:
        regions = [
            ("ring-seat", 218, 52, 38, 52, 52),
            ("display-flange", 147.2, 22.7, 38, 25.6, 16.6),
        ]
        regions += [("meter-flange", 42.6, y - 2, 36, 59.6, 4) for y in (21.25, 35.25)]
        regions += [("bank-flange", x - 2, 101, 36, 4, 4) for x in (82, 101, 120, 139)]
    mesh = trimesh.load_mesh(path, process=False)
    triangles = mesh.triangles
    covered = np.zeros(len(triangles), dtype=bool)
    matched = []
    maximum = 0.0
    tolerance = 1e-5
    for label, x, y, z, width, depth in regions:
        inside = np.all(
            (triangles[:, :, 0] >= x - tolerance)
            & (triangles[:, :, 0] <= x + width + tolerance)
            & (triangles[:, :, 1] >= y - tolerance)
            & (triangles[:, :, 1] <= y + depth + tolerance),
            axis=1,
        )
        deviation = np.max(np.abs(triangles[:, :, 2] - z), axis=1)
        hit = inside & (deviation <= tolerance)
        if np.any(hit):
            matched.append(label)
            maximum = max(maximum, float(np.max(deviation[hit])))
        covered |= hit
    if not len(triangles) or not np.all(covered):
        raise RuntimeError(name + ": intersection outside the named seating planes")
    return dict(
        result="intended planar seating contacts only",
        seats=matched,
        triangles=len(triangles),
        plane_tolerance_mm=tolerance,
        maximum_plane_deviation_mm=maximum,
    )


def components(mesh):
    parents = list(range(len(mesh.faces)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in mesh.face_adjacency:
        parents[root(int(a))] = root(int(b))
    return len({root(i) for i in range(len(parents))})


def check_mesh(path, expected=1):
    import trimesh

    mesh = trimesh.load_mesh(path)
    count = components(mesh)
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0 and count == expected):
        raise RuntimeError(
            f"{path.name}: bad mesh, connected parts={count}, expected={expected}, volume={mesh.volume}"
        )
    return mesh, dict(
        watertight=True,
        winding_consistent=True,
        connected_solids=count,
        triangles=len(mesh.faces),
        volume_mm3=round(float(mesh.volume), 3),
        size_mm=[round(float(x), 3) for x in mesh.extents],
    )


def write_3mf(parts, meshes):
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)

    def child(parent, name, attrs=None):
        return ET.SubElement(parent, "{" + ns + "}" + name, attrs or {})

    model = ET.Element(
        "{" + ns + "}model",
        {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"},
    )
    child(
        model, "metadata", {"name": "Title"}
    ).text = "RMX A10 full print inventory; rearrange on the actual printer bed"
    resources = child(model, "resources")
    build = child(model, "build")
    x = y = row_depth = 0.0
    for number, item in enumerate(parts, 1):
        mesh = meshes[item["name"]].copy()
        mesh.vertices -= mesh.bounds[0]
        obj = child(
            resources,
            "object",
            {"id": str(number), "type": "model", "name": item["name"]},
        )
        node = child(obj, "mesh")
        vertices = child(node, "vertices")
        triangles = child(node, "triangles")
        for v in mesh.vertices:
            child(
                vertices,
                "vertex",
                dict(zip(("x", "y", "z"), (f"{float(n):.7g}" for n in v))),
            )
        for face in mesh.faces:
            child(
                triangles,
                "triangle",
                dict(zip(("v1", "v2", "v3"), (str(int(n)) for n in face))),
            )
        w, d, _ = mesh.extents
        for _ in range(item["quantity"]):
            if x + w > 750:
                x = 0
                y += row_depth + 8
                row_depth = 0
            child(
                build,
                "item",
                {
                    "objectid": str(number),
                    "transform": f"1 0 0 0 1 0 0 0 1 {x:.5f} {y:.5f} 0",
                },
            )
            x += float(w) + 8
            row_depth = max(row_depth, float(d))
    model_data = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    target = OUT / "RMX-A10-complete-print-inventory.3mf"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        )
        archive.writestr("3D/3dmodel.model", model_data)
    with zipfile.ZipFile(target) as archive:
        parsed = ET.fromstring(archive.read("3D/3dmodel.model"))
        assert len(parsed.findall(".//{" + ns + "}object")) == len(parts)
        assert len(parsed.findall(".//{" + ns + "}item")) == sum(p["quantity"] for p in parts)
    return target


def make_package(parts, report):
    output = OUT / "RMX-A10-print-pack.zip"
    files = {}
    for item in parts:
        files["STL/" + item["name"] + ".stl"] = (OUT / (item["name"] + ".stl")).read_bytes()
    files["RMX-A10-complete-print-inventory.3mf"] = (
        OUT / "RMX-A10-complete-print-inventory.3mf"
    ).read_bytes()
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and path.suffix in (".scad", ".csv", ".json", ".md", ".py", ".txt")
            and "__pycache__" not in path.parts
        ):
            files["CAD/" + str(path.relative_to(ROOT))] = path.read_bytes()
    files["README.md"] = (ROOT / "PRINTING.md").read_bytes()
    files["parts.csv"] = (OUT / "parts.csv").read_bytes()
    files["validation.json"] = (OUT / "validation.json").read_bytes()
    files["cad-overview.png"] = (OUT / "overview.png").read_bytes()
    for name in ("assembled", "exploded", "button", "parts"):
        files["Review/" + name + ".png"] = (OUT / (name + ".png")).read_bytes()
    files["Electronics/UNQUALIFIED-power_supply.kicad_pcb"] = (
        REPO / "hardware/electronics/power_supply/routing/power_supply.kicad_pcb"
    ).read_bytes()
    files["Electronics/components.json"] = (
        REPO / "hardware/electronics/power_supply/components.json"
    ).read_bytes()
    files["Tests/a10_integration_tests.py"] = (REPO / "tests/a10_integration_tests.py").read_bytes()
    files["manifest.json"] = (
        json.dumps(
            {
                "revision": "A10",
                "units": "mm",
                "file_sha256": {
                    name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())
                },
            },
            indent=2,
        )
        + "\n"
    ).encode()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            archive.writestr("RMX-A10-print-pack/" + name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument(
        "--reuse-exports",
        action="store_true",
        help="Reuse STL exports only when their recorded source hash matches",
    )
    parser.add_argument("--update-previews", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "generate.py")], check=True)
    source_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(ROOT.rglob("*.scad"))
    }
    fingerprint = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    parts = inventory()
    meshes = {}
    report = {
        "revision": "A10",
        "source_sha256": source_hashes,
        "scope": "nominal printable mechanical parts and allocated electronics reserves; no physical validation",
        "physical_fit_verified": False,
        "power_integration": json.loads((ROOT / "generated/power-integration.json").read_text()),
        "solids": {},
        "checks": {},
    }
    if not args.preview_only:
        old = json.loads((OUT / "validation.json").read_text()) if (OUT / "validation.json").exists() else {}
        reuse = args.reuse_exports and old.get("geometry_fingerprint") == fingerprint
        if not reuse:

            def export(item):
                # Preserve the native binary coordinates. Re-triangulating or
                # translating an exported STL can destroy coplanar edge topology.
                backend = "CGAL" if item["part"] == "holder" else "Manifold"
                path = native(
                    args.openscad,
                    item["name"],
                    item["part"],
                    "stl",
                    index=item["index"],
                    backend=backend,
                )
                try:
                    check_mesh(path)
                except RuntimeError:
                    if backend == "CGAL":
                        raise
                    native(
                        args.openscad,
                        item["name"],
                        item["part"],
                        "stl",
                        index=item["index"],
                        backend="CGAL",
                    )
                    check_mesh(path)
                print("Exported " + item["name"], flush=True)

            with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
                list(pool.map(export, parts))
        for item in parts:
            mesh, evidence = check_mesh(OUT / (item["name"] + ".stl"))
            meshes[item["name"]] = mesh
            report["solids"][item["name"]] = evidence
        for name, count in [("all_holders", 29), ("all_keys", 29)]:
            path = native(args.openscad, name, name, "stl", backend="CGAL")
            _, evidence = check_mesh(path, count)
            report["checks"][name] = evidence
        for name in [
            "moving_collision",
            "fixed_collision",
            "lever_collision",
            "chassis_collision",
            "optics_collision",
            "power_margin_collision",
            "power_thermal_collision",
        ]:
            report["checks"][name] = native(args.openscad, name, name, "stl", empty=True)
        report["geometry_fingerprint"] = fingerprint
        report["unique_stl_files"] = len(parts)
        report["printed_copies"] = sum(p["quantity"] for p in parts)
        (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=["file", "quantity", "material", "purpose", "size_mm"])
        writer.writeheader()
        for item in parts:
            writer.writerow(
                dict(
                    file=item["name"] + ".stl",
                    quantity=item["quantity"],
                    material=item["material"],
                    purpose=item["purpose"],
                    size_mm=" x ".join(map(str, report["solids"][item["name"]]["size_mm"])),
                )
            )
        (OUT / "parts.csv").write_text(stream.getvalue())
        write_3mf(parts, meshes)
    if args.geometry_only:
        print("Verified geometry and 3MF; previews/package deferred", flush=True)
        return
    scenes = [
        ("assembled", "assembly", [], "440,-330,400,167,78,18"),
        (
            "exploded",
            "assembly",
            ["-D", "exploded=65", "-D", "show_internals=true"],
            "440,-330,400,167,78,38",
        ),
        ("button", "button_section", [], "-40,-55,32,0,0,-2"),
        ("parts", "print_layout", [], "850,-650,800,340,150,10"),
    ]

    def render(scene):
        name, part, defines, camera = scene
        native(
            args.openscad,
            name,
            part,
            "png",
            extra=[
                "--preview",
                "--imgsize",
                "2200,1450",
                "--camera",
                camera,
                "--autocenter",
                "--viewall",
                "--projection",
                "o",
                "--colorscheme",
                "Tomorrow",
                *defines,
            ],
        )
        print("Rendered " + name, flush=True)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(render, scenes))
    from review import compose

    compose(OUT)
    if not args.preview_only:
        package = make_package(parts, report)
        print("Created " + str(package), flush=True)
    if args.update_previews:
        (REPO / "docs/assets/hardware/cad-overview.png").write_bytes((OUT / "overview.png").read_bytes())


if __name__ == "__main__":
    main()
