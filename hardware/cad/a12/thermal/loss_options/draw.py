"""Visual comparison of deliberately impossible zero-loss allocation controls."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .analyze import OUT, read


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    a = read(OUT / "analysis.json")
    labels = [
        "Retained\nWU01 screen",
        "Zero converter\nloss (fictional)",
        "Zero all stage/feed\nloss (fictional)",
        "Endpoints only\n(fictional)",
    ]
    variants = ["lossless_converters", "lossless_all_power_stages", "endpoint_only"]
    rows = [
        next(
            r
            for r in a["counterfactual_references"]
            if r["variant"] == v and r["placement"] == "unplaced_uniform"
        )
        for v in variants
    ]
    powers = [a["retained_baseline_heat_target_w"]] + [r["result"]["total_w"] for r in rows]
    baseline = read(Path(__file__).resolve().parent.parent / "whole_unit/generated/analysis.json")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    axes[0].bar(np.arange(4), powers, color=["#a74935", "#d49a3f", "#538b97", "#586c94"])
    for x, y in enumerate(powers):
        axes[0].text(x, y + 0.35, f"{y:.2f}", ha="center")
    axes[0].set(
        xticks=np.arange(4),
        xticklabels=labels,
        ylabel="Retained input-power allocation screen (W)",
        ylim=(0, 40),
        title="Loss removal is not load-current evidence",
    )
    for i, mode in enumerate(["unplaced_uniform", "unplaced_hotcluster"]):
        b = next(
            r["result"]["plate_max_c"]
            for r in baseline["cases"]
            if r["placement"] == mode
            and r["result"]["h_assumed_w_per_m2k"] == 3
            and r["result"]["emissivity_assumed"] == 0.8
        )
        ys = [b] + [
            next(
                r["result"]["plate_max_c"]
                for r in a["counterfactual_references"]
                if r["variant"] == v and r["placement"] == mode
            )
            for v in variants
        ]
        x = np.arange(4) + (i - 0.5) * 0.3
        axes[1].bar(x, ys, width=0.3, label="Unplaced " + ("uniform" if i == 0 else "hot cluster"))
        for xx, y in zip(x, ys):
            axes[1].text(xx, y + 0.5, f"{y:.1f}", ha="center", fontsize=8)
    axes[1].axhline(60, color="#555", ls="--", lw=1)
    axes[1].axhline(65, color="#777", ls=":", lw=1)
    axes[1].set(
        xticks=np.arange(4),
        xticklabels=labels,
        ylabel="Conditional peak base (°C)",
        ylim=(40, 109),
        title="Same geometry / h3 / ε0.8 / ambient40 °C",
    )
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
    fig.suptitle(
        "LO01: even impossible zero-loss controls do not qualify the retained fanless heat screen",
        fontsize=13,
    )
    fig.text(
        0.04,
        0.03,
        "These are allocation controls, not actual minimum heat, measured consumption or an implemented design. All existing load reserves and35.4315 W target remain.\nNo fan, larger housing, converter, inlet or wiring change adopted. Real current/source/efficiency/feed bounds and physical thermal evidence remain open.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 0.92))
    fig.savefig(OUT / "loss-ceilings.svg")
    fig.savefig(OUT / "loss-ceilings.png", dpi=150)
    plt.close(fig)
    paths = [
        Path(__file__).resolve(),
        OUT / "analysis.json",
        Path(__file__).resolve().parent.parent / "whole_unit/generated/analysis.json",
    ]
    (OUT / "drawing-inputs.json").write_text(
        json.dumps(dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths}), indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
