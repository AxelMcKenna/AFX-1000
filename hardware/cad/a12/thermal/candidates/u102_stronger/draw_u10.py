"""Native B.Cu thermal-contact diagnostic, including actual foreign routing and bores."""

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/afx-mpl")
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    fig, axes = plt.subplots(1, 2, figsize=(12, 6.8))
    for ax, (title, pcb) in zip(
        axes,
        [
            ("Closedf94c: restored routing", ROOT / "sources/closed-U10/power_p03.kicad_pcb"),
            ("B-transit recovery draft:4opens", ROOT / "u10_B_trial/power_p03.kicad_pcb"),
        ],
    ):
        tree = read_sexpr(pcb.read_text())
        for zone in children(tree, "zone"):
            if not children(zone, "net") or str(first(zone, "net")[1]).lstrip("/") != "RAW_N22":
                continue
            for fill in children(zone, "filled_polygon"):
                if first(fill, "layer")[1] != "B.Cu":
                    continue
                points = [[float(p[1]) - 100, float(p[2]) - 100] for p in children(first(fill, "pts"), "xy")]
                ax.add_patch(Polygon(points, color="#4d9764", alpha=0.65))
        for segment in children(tree, "segment"):
            if first(segment, "layer")[1] != "B.Cu" or str(first(segment, "net")[1]).lstrip("/") == "RAW_N22":
                continue
            a, b = [list(map(float, first(segment, k)[1:3])) for k in ["start", "end"]]
            if not (
                min(a[0], b[0]) < 195
                and max(a[0], b[0]) > 189
                and min(a[1], b[1]) < 133
                and max(a[1], b[1]) > 126
            ):
                continue
            ax.plot(
                [a[0] - 100, b[0] - 100], [a[1] - 100, b[1] - 100], color="#9d3131", linewidth=2, alpha=0.8
            )
        for via in children(tree, "via"):
            x, y = map(float, first(via, "at")[1:3])
            node = str(first(via, "net")[1]).lstrip("/")
            if 189 < x < 195 and 126 < y < 133:
                radius = float(first(via, "size")[1]) / 2
                ax.add_patch(
                    Circle(
                        (x - 100, y - 100),
                        radius,
                        fill=False,
                        edgecolor="#1e6543" if node == "RAW_N22" else "#a33333",
                        linewidth=1,
                    )
                )
                ax.add_patch(Circle((x - 100, y - 100), float(first(via, "drill")[1]) / 2, color="white"))
        for box, color, style in [
            ([90.1, 27.7, 3.65, 3.7], "#222222", "-"),
            ([89.1, 26.7, 5.65, 5.7], "#356ba0", "--"),
        ]:
            ax.add_patch(
                Rectangle(box[:2], box[2], box[3], fill=False, edgecolor=color, linestyle=style, linewidth=2)
            )
        ax.set(
            xlim=(88.8, 95.1),
            ylim=(32.7, 26.4),
            aspect="equal",
            title=title,
            xlabel="P03 localX (nativeX−100), mm",
            ylabel="P03 localY (nativeY−100), mm",
        )
        ax.grid(alpha=0.15)
    closed = json.loads((ROOT / "generated/closed-U10-replay.json").read_text())["scenarios"][-1]["result"]
    draft = json.loads((ROOT / "generated/U10-B-transit-probe.json").read_text())["results"][-1]
    fig.suptitle("U10 contact: actual foreign vias remain in both models", fontsize=15)
    fig.text(
        0.08,
        0.09,
        f"Green actual B.Cu RAW_N22 fill; red foreign B traces/via lands; white actual bores. Black metal3.65×3.70; blue TIM5.65×5.70.\nMatching copper: closed{closed['sink_area_under_matching_bottom_copper_mm2']:.3f}mm² → draft{draft['sink_area_under_matching_bottom_copper_mm2']:.3f}mm².\nAt65 °C base+2 °C allocated uncertainty: {closed['conditional_junction_at_60c_base_c'] + 7:.2f} °C → {draft['conditional_junction_at_60c_base_c'] + 7:.2f} °C. No physical or guardbanded qualification.",
        fontsize=9,
    )
    fig.subplots_adjust(bottom=0.23, top=0.86, wspace=0.23)
    fig.savefig(ROOT / "generated/U10-contact-recovery.svg")
    fig.savefig(ROOT / "generated/U10-contact-recovery.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
