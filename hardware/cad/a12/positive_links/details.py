"""Dimensioned nominal cover/retainer sections for prototype quotation."""

from .generate import OUT, load


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    d = load()
    fig, axes = plt.subplots(1, 3, figsize=(16, 8), layout="constrained")
    a = axes[0]
    a.set(
        aspect="equal", xlim=(-8, 8), ylim=(-5.7, 11), xlabel="Local U / mm", ylabel="Above copper bottom / mm"
    )
    a.add_patch(Rectangle((-5.85, -1), 11.7, 6.32, facecolor="#e4d9b1", edgecolor="black"))
    a.add_patch(Rectangle((-4, 4.4), 8, 4.9, facecolor="#e4d9b1", edgecolor="black"))
    a.add_patch(Rectangle((-3.85, -1.05), 7.7, 5.77, facecolor="white", edgecolor="black"))
    a.add_patch(Rectangle((-5.0625, -0.05), 10.125, 1.4, facecolor="white", edgecolor="black"))
    a.add_patch(Rectangle((-5, 0), 10, 1.2, facecolor="#bc7e46", edgecolor="black"))
    a.add_patch(Rectangle((-1.7, -0.1), 3.4, 1.4, facecolor="white", edgecolor="black"))
    a.add_patch(Circle((0, 7), 0.9, facecolor="white", edgecolor="black"))
    a.axhline(4.72, color="#999", lw=0.5, ls="--")
    a.text(-7.8, 10.2, "Terminal cover / central nominal section", fontsize=10)
    a.text(
        -7.8,
        -2.5,
        "OD11.7; upper bridge8×8; top9.3\nHead cavityØ7.7 toZ4.72; boltaxisZ7.0\nM1.6clearanceØ1.8; nut pocket3.35AF\nCu cavityØ10.125±.025; heightT_received+.20\nPEEKsurface allocation±.05; radial OD bounds±.10",
        va="top",
        fontsize=8,
    )
    a = axes[1]
    a.set(aspect="equal", xlim=(155, 178), ylim=(90, 144), xlabel="Housing X / mm", ylabel="Housing Y / mm")
    a.add_patch(Rectangle((163, 117.5), 6, 12, facecolor="#dfd4ee", edgecolor="black"))
    a.add_patch(Circle((166, 123.5), 1.5, facecolor="#a28db9", edgecolor="black"))
    a.add_patch(Rectangle((166, 122.5), 5, 2, facecolor="#cdbbdf", edgecolor="black"))
    a.add_patch(Rectangle((170, 100.5), 2, 32.625, facecolor="#cdbbdf", edgecolor="black"))
    for name, q in d["support"]["saddles"].items():
        a.add_patch(Rectangle((169.75, q[1] - 6.5), 2.5, 13, facecolor="#b7a1d0", edgecolor="black"))
        for dy in d["support"]["screw_y_offsets"]:
            a.add_patch(Circle((q[0] + 1.5, q[1] + dy), 2.5, facecolor="#b7a1d0", edgecolor="black"))
            a.add_patch(Circle((q[0] + 1.5, q[1] + dy), 1.9, fill=False, edgecolor="black"))
            a.add_patch(Circle((q[0] + 1.5, q[1] + dy), 0.9, facecolor="white", edgecolor="black"))
        a.text(173, q[1], name, fontsize=8)
    a.set_title("Separate PEEK pedestal / plan", fontsize=10)
    a = axes[2]
    a.axis("off")
    a.text(
        0,
        1,
        "PB01 insulating hardware / nominal quotation schedule\n\n4×split terminal covers,8PEEK halves\n4×PTS A91201608 M1.6×8\n4×Accu HPN-M1.6-A2 captive hex nuts\n4×Accu SPP-M3-8-A2 +HPW-M3-A2 washers\n1×Ketron1000PEEK bonded pedestal\n2×matched PEEK saddle keepers\n4×Accu SPK-M1.6-6-A2 countersunk\n3M92 two wraps; DP460EG bond candidate\n\nFoot6×12×.4 atZ2.9 on nominal.1bond\nMastØ3 centred166,123.5; no PCBedge contact\nArm2wide×3deep; saddle spine2.5×13\nØ5bosses atX+1.5,Y±6.8: overallY18.6\nSaddle minor drillØ1.3, M1.6through tap\nCountersunk top datum =actual floor+3.5\nM1.6×6 receiving length5.8..6.2PROJECTrange\nNominal engagement2.615; projectminimum2\nKeeper thickness matched to actualT/tape\nØ3.8/90countersink throughØ1.8clearance\nConservative .285rim+.675frustum; seat0..0.30\nMatched .6mm side rails; longitudinal slide\n\nLocal cap variants:\nANA/P03 upper bridge shifted+2.7X\nDIG/P03 upper bridge shifted+4Y; splitlineY+4\nDIG/E28 flat: CuX+4.0,cavity+4.2,outer+4.8\nOthers centred; four intentional bare land faces\n\nNo adhesive, PEEKthread, cantilever, coating,\ncontact/torque, lifetime or dielectric allowable\nis established by these dimensions.\n\nMatch actual terminal planes and Cu/wrap.\nUse current STEP for the full local geometry.\nPrototype drawings, not fabrication released.",
        va="top",
        fontsize=9,
        linespacing=1.35,
    )
    fig.suptitle(
        "AFX A12 PB01 — cover and restraint details / nominal dimensions in mm / UNRELEASED", fontsize=14
    )
    fig.savefig(OUT / "PB01-cover-support-details.svg")
    fig.savefig(OUT / "PB01-cover-support-details.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
