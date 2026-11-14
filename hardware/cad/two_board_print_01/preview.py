"""Render native exported mesh projections without a host CAD application."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("revision")
    args = parser.parse_args()
    folder = ROOT / "generated" / args.revision
    capture = json.loads((ROOT / "capture.json").read_text())
    image = Image.new("RGB", (1800, 1200), "#f5f6f8")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 19)
    draw.text((55, 30), "Two-board housing | native STL geometry", fill="#17232c", font=font)
    draw.text((55, 70), "338 x 192.4 x 45.6 mm housing body | dimensions in mm | mechanical fit prototype", fill="#475764", font=small)
    camera = np.array([.25, -.58, .775]); camera /= np.linalg.norm(camera)
    right = np.cross([0, 0, 1], camera); right /= np.linalg.norm(right)
    up = np.cross(camera, right)
    basis = np.array([right, up, camera]).T

    def render(mesh, viewport, color):
        points = np.asarray(mesh.vertices) @ basis
        low, high = points.min(axis=0), points.max(axis=0)
        scale = min(viewport[2]/(high[0]-low[0]), viewport[3]/(high[1]-low[1]))
        points[:, 0] = viewport[0] + scale * (points[:, 0]-low[0])
        points[:, 1] = viewport[1] + scale * (high[1]-points[:, 1])
        light = np.array([.4, -.25, .88]); light /= np.linalg.norm(light)
        shades = .58 + .42 * np.maximum(0, mesh.face_normals @ light)
        order = np.argsort(np.mean(points[mesh.faces, 2], axis=1))
        for i in order:
            if mesh.face_normals[i] @ camera <= 0:
                continue
            rgb = tuple(int(c * shades[i]) for c in color)
            draw.polygon([tuple(p[:2]) for p in points[mesh.faces[i]]], fill=rgb)

    shell = trimesh.load_mesh(folder / "shell/shell.stl")
    render(shell, (55, 140, 800, 440), (167, 184, 197))
    draw.text((55, 625), "Shell: current mounting posts and removable rear-panel seat", fill="#17232c", font=small)

    # Top plan is a literal orthographic projection of the actual shell STL.
    sx, sy, scale = 940, 130, 2.25
    for face in shell.faces:
        draw.polygon([(sx + scale * p[0], sy + scale * p[1]) for p in shell.vertices[face]], fill="#bac7d1")
    colors = {"signal": "#82c5b0", "power": "#91aecf"}
    for board in capture["boards"]:
        draw.polygon([(sx + scale * x, sy + scale * y) for x, y in board["outline"]],
                     fill=colors[board["id"]], outline="#1d4751", width=2)
        for x, y, d in board["holes"]:
            r = max(2.5, d * scale / 2)
            px, py = sx + scale*x, sy + scale*y
            draw.ellipse((px-r, py-r, px+r, py+r), fill="#f5f6f8", outline="#1d4751")
    draw.text((940, 625), "Actual two-board outlines and mounting holes (top view)", fill="#17232c", font=small)

    lid = trimesh.load_mesh(folder / "lid/lid.stl")
    render(lid, (55, 720, 800, 370), (184, 195, 205))
    draw.text((55, 1140), "Lid in print orientation; control apertures retained", fill="#17232c", font=small)
    draw.text((940, 725), "Print choices", fill="#17232c", font=font)
    for index, line in enumerate([
        "One-piece shell and lid: 338 x 192.4 mm footprint",
        "Split shell, lid, guide and rear plate supplied separately",
        "Print the fit coupons before the full housing",
        "Board models show placement, not electrical completion",
        "Material, slicer settings and physical fit need confirmation",
        "See README for hardware and assembly sequence",
    ]):
        draw.text((940, 775+index*44), line, fill="#475764", font=small)
    target = ROOT / ("preview-" + args.revision + ".png")
    assert not target.exists(), "Keep completed previews immutable"
    image.save(target)
    print(target)


if __name__ == "__main__":
    main()
