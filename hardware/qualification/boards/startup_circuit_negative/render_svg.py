"""CPU raster preview of native KiCad's stroke-font SVG; strict supported grammar."""

import json
import math
import os
import re
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-mpl")

from .analyze import OUT, sha


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.collections import LineCollection

    path = OUT / "schematic-svg/negative_startup.svg"
    root = ET.parse(path).getroot()
    lines = []
    colors = []
    widths = []

    def walk(node, matrix, style):
        style = dict(style)
        for k, v in re.findall(r"([^:;]+):([^;]+)", node.attrib.get("style", "")):
            style[k.strip()] = v.strip()
        transform = node.attrib.get("transform", "")
        for kind, args in re.findall(r"(translate|scale|rotate)\(([^)]+)\)", transform):
            v = [float(q) for q in re.findall(r"[-+]?[\d.]+", args)]
            m = np.eye(3)
            if kind == "translate":
                m[0, 2] = v[0]
                m[1, 2] = v[1] if len(v) > 1 else 0
            elif kind == "scale":
                m[0, 0] = v[0]
                m[1, 1] = v[1] if len(v) > 1 else v[0]
            else:
                a = math.radians(v[0])
                c, s = math.cos(a), math.sin(a)
                m[:2, :2] = [[c, -s], [s, c]]
                if len(v) == 3:
                    m[:2, 2] = np.asarray(v[1:]) - m[:2, :2] @ v[1:]
            matrix = matrix @ m
        tag = node.tag.split("}")[-1]
        color = style.get("stroke", "#000000")
        width = float(style.get("stroke-width", ".15"))

        def line(xy):
            points = (matrix @ np.column_stack([np.asarray(xy), np.ones(len(xy))]).T).T[:, :2]
            lines.append(points)
            colors.append(color)
            widths.append(width)

        if tag == "path":
            tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", node.attrib["d"])
            i = 0
            xy = []
            while i < len(tokens):
                op = tokens[i]
                assert op in ["M", "L"], op
                i += 1
                points = []
                while i < len(tokens) and tokens[i] not in ["M", "L"]:
                    points.append([float(tokens[i]), float(tokens[i + 1])])
                    i += 2
                if op == "M":
                    if len(xy) > 1:
                        line(xy)
                    xy = points
                else:
                    xy += points
            if len(xy) > 1 and color != "none":
                line(xy)
        elif tag == "rect" and color != "none":
            x, y, w, h = [float(node.attrib.get(k, 0)) for k in ["x", "y", "width", "height"]]
            line([[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]])
        for child in node:
            walk(child, matrix, style)

    walk(root, np.eye(3), {})
    for name, box, width in [
        ("schematic-preview", (0, 0, 700, 1180), 2400),
        ("n19-left", (20, 40, 345, 515), 2100),
        ("n19-right", (345, 40, 680, 515), 2100),
        ("n12-left", (20, 535, 345, 1010), 2100),
        ("n12-right", (345, 535, 680, 1010), 2100),
    ]:
        x, y, xx, yy = box
        fig = plt.figure(figsize=(width / 150, width * (yy - y) / (xx - x) / 150), dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.add_collection(
            LineCollection(
                lines, colors=colors, linewidths=np.asarray(widths) * 72 * width / (150 * (xx - x))
            )
        )
        ax.set_xlim(x, xx)
        ax.set_ylim(yy, y)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.savefig(OUT / (name + ".png"), dpi=150)
        plt.close(fig)
    (OUT / "render-metadata.json").write_text(
        json.dumps(
            dict(
                native_svg_sha256=sha(path),
                renderer_sha256=sha(__file__),
                stroke_polylines=len(lines),
                text_basis="Actual native stroke-fontpaths; invisibleSVGtextignored. StrictM/Lgrammar, inherited transforms/styles applied.",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
