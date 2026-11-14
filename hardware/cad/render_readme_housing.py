"""Render README views from the delivered r6 STL triangles, without CAD launches."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / 'hardware/cad/two_board_print_01/print-package-r6'
OUTPUT = REPO / 'docs/assets/hardware'


def main():
    paths = {name: PACKAGE / 'print/single-piece' / (name + '.stl')
             for name in ['shell', 'lid', 'rear_plate']}
    meshes = {name: trimesh.load_mesh(path, process=False) for name, path in paths.items()}
    # Invert the documented print transforms and restore installed coordinates.
    lid_transform = np.diag([1., -1., -1., 1.])
    lid_transform[:3, 3] = [0, 192.4, 45.6]
    meshes['lid'].apply_transform(lid_transform)
    rear_transform = np.array([[1, 0, 0, 12], [0, 0, 1, -1.6],
                               [0, -1, 0, 43.6], [0, 0, 0, 1.]])
    meshes['rear_plate'].apply_transform(rear_transform)
    colors = {'shell': (128, 154, 173), 'lid': (196, 208, 216),
              'rear_plate': (160, 181, 196)}
    views = [
        ('front', 'Assembled housing', 'Front and control-panel apertures', [.65, 1., .85], ['shell', 'lid', 'rear_plate']),
        ('rear', 'Rear connector panel', 'Removable rear plate and connector apertures', [-.65, -1., .65], ['shell', 'lid', 'rear_plate']),
        ('open', 'Open housing', 'PCB supports and mounting features; lid removed', [.45, -.8, 1.2], ['shell', 'rear_plate']),
    ]
    outputs = []
    for name, title, subtitle, direction, parts in views:
        scale_px = 2
        canvas = Image.new('RGB', (1500 * scale_px, 900 * scale_px), '#f4f6f8')
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32 * scale_px)
        small = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 21 * scale_px)
        draw.text((55 * scale_px, 32 * scale_px), title, font=font, fill='#17232c')
        draw.text((55 * scale_px, 82 * scale_px), subtitle, font=small, fill='#475764')
        camera = np.array(direction); camera /= np.linalg.norm(camera)
        right = np.cross([0, 0, 1], camera); right /= np.linalg.norm(right)
        up = np.cross(camera, right)
        basis = np.array([right, up, camera]).T
        projected = {part: meshes[part].vertices @ basis for part in parts}
        points = np.concatenate(list(projected.values()))
        lo, hi = points.min(0), points.max(0)
        factor = min(1380 / (hi[0] - lo[0]), 640 / (hi[1] - lo[1]))
        offset_x = (1500 - factor * (hi[0] - lo[0])) / 2
        offset_y = 150 + (640 - factor * (hi[1] - lo[1])) / 2
        light = .35 * right + .45 * up + .82 * camera
        light /= np.linalg.norm(light)
        faces = []
        for part in parts:
            mesh, p = meshes[part], projected[part].copy()
            p[:, 0] = (offset_x + (p[:, 0] - lo[0]) * factor) * scale_px
            p[:, 1] = (offset_y + (hi[1] - p[:, 1]) * factor) * scale_px
            shade = .48 + .52 * np.maximum(0, mesh.face_normals @ light)
            for i, face in enumerate(mesh.faces):
                if mesh.face_normals[i] @ camera > 0:
                    faces.append((p[face, 2].mean(), p[face],
                                  tuple(int(c * shade[i]) for c in colors[part])))
        # Per-pixel depth avoids painter-order artifacts on long wall triangles.
        pixels = np.array(canvas)
        depth = np.full(pixels.shape[:2], -np.inf, dtype=np.float32)
        for _, triangle, color in faces:
            left, top = np.floor(triangle[:, :2].min(0)).astype(int)
            right_edge, bottom = np.ceil(triangle[:, :2].max(0)).astype(int)
            left, top = max(0, left), max(0, top)
            right_edge, bottom = min(pixels.shape[1]-1, right_edge), min(pixels.shape[0]-1, bottom)
            if right_edge < left or bottom < top:
                continue
            a, b, c = triangle
            denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator) < 1e-10:
                continue
            yy, xx = np.ogrid[top:bottom+1, left:right_edge+1]
            first = ((b[1]-c[1])*(xx+.5-c[0])+(c[0]-b[0])*(yy+.5-c[1]))/denominator
            second = ((c[1]-a[1])*(xx+.5-c[0])+(a[0]-c[0])*(yy+.5-c[1]))/denominator
            third = 1-first-second
            z = first*a[2]+second*b[2]+third*c[2]
            target_depth = depth[top:bottom+1, left:right_edge+1]
            visible = (first >= -1e-8) & (second >= -1e-8) & (third >= -1e-8) & (z > target_depth)
            target_depth[visible] = z[visible]
            pixels[top:bottom+1, left:right_edge+1][visible] = color
        canvas = Image.fromarray(pixels)
        draw = ImageDraw.Draw(canvas)
        draw.text((55 * scale_px, 840 * scale_px),
                  'TBH01 r6 CAD render · unpowered fit prototype · controls and fasteners omitted',
                  font=small, fill='#475764')
        target = OUTPUT / f'tbh01-r6-{name}.png'
        canvas.resize((1500, 900), Image.Resampling.LANCZOS).save(target)
        outputs.append(target)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sources = [Path(__file__), *paths.values(),
               REPO / 'hardware/cad/two_board_print_01/housing.scad']
    record = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  artifact_sha256={str(p.relative_to(REPO)): sha(p) for p in outputs},
                  method='Orthographic triangle projection of delivered STL geometry; rigid installation transforms only.',
                  scope='Bare housing CAD illustration, not a photograph or complete functional assembly.')
    (OUTPUT / 'tbh01-r6-readme-renders.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Rendered front, rear and open-shell README images.')


if __name__ == '__main__':
    main()
