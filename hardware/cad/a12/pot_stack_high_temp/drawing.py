"""Dimensioned source/receiving distinction for HT01; no supplier image copied."""

import json

from .contract import report
from .stage import OUT, ROOT, sha, write


def build():
    if (ROOT / "handoff.json").exists() or (OUT / "HT01-receiving.png").exists():
        raise RuntimeError("Drawing output is immutable; use a new sibling")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    blue, orange, gray = "#145f91", "#ae5200", "#737b81"
    fig, (ax, bp) = plt.subplots(1, 2, figsize=(13, 8), gridspec_kw=dict(width_ratios=[1.15, 1]))
    fig.suptitle("HT01 · RK09L1140A5L receiving study", fontsize=17, x=.05, ha="left")
    fig.text(.05, .92, "Blue: manufacturer nominal geometry   |   Orange: unaccepted receiving requirements   |   mm", fontsize=10)
    ax.set_xlim(-17, 22)
    ax.set_ylim(27, 65)
    ax.set_aspect("equal")
    ax.set_xlabel("Local radial X (section schematic)")
    ax.set_ylabel("Global Z")
    ax.add_patch(Rectangle((-8, 29.4),16,14.2,facecolor="#e5e7e9",edgecolor=gray,ls="--"))
    ax.add_patch(Rectangle((-6.05,36.15),12.1,7.45,facecolor="#d7e9f4",edgecolor=blue))
    ax.add_patch(Rectangle((-8,32),16,1.6,facecolor="#e9b67f",edgecolor=orange))
    for x in [-2.5,0,2.5]:
        ax.plot([x,x],[30.1,33.6],color=blue,lw=1.2)
    for x in [-14,4.75]:
        ax.add_patch(Rectangle((x,43.6),9.25,2,facecolor="#e3e3e3",edgecolor=gray))
    ax.add_patch(Rectangle((-4.5,43.6),9,5,fill=False,edgecolor=blue,lw=1.5))
    ax.add_patch(Rectangle((-3,48.6),6,10,facecolor="#b4d6ee",edgecolor=blue))
    ax.add_patch(Rectangle((-7.1,45.6),14.2,.6,fill=False,edgecolor=orange,lw=1.2))
    ax.add_patch(Rectangle((-6.47,46.2),12.94,2.2,fill=False,edgecolor=orange,lw=1.2))
    ax.add_patch(Rectangle((-8,49.2),16,13,fill=False,edgecolor="#252a31",lw=1.5))
    ax.plot([-3.1,-3.1,3.1,3.1],[49.2,60,60,49.2],color=orange,lw=1.4)
    ax.plot([1.5,8],[54.2,54.2],color=orange,lw=2)
    ax.plot([3.5,8],[52.2,52.2],color="#aa3333",lw=1,ls="--")
    labels=[(29.4,"29.4 tail/solder receiving floor"),(33.6,"33.6 substrate mounting plane"),
        (36.15,"36.15 nominal rear body"),(43.6,"43.6 bushing-root / panel underside"),
        (49.2,"49.2 retained knob base"),(54.2,"54.2 revised grub axis (local5)"),
        (58.6,"58.6 nominal shaft tip"),(60,"60.0 nominal bore roof"),(62.2,"62.2 smallest knob top")]
    for z,label in labels:
        ax.annotate(label,xy=(8,z),xytext=(11,z+.2),fontsize=8,color=orange if z in [29.4,49.2,54.2,60] else blue,
            arrowprops=dict(arrowstyle="-",lw=.6,color=gray))
    ax.text(-16.5,63.8,"Nominal axial stack",weight="bold",fontsize=11)
    ax.text(-16.5,27.5,"Full fit checks use source-bound swept gauges;\nthis section is not a supplier profile or torque approval.",fontsize=8,color=gray)
    ax.grid(alpha=.15)
    bp.set_aspect("equal")
    bp.set_xlim(-11,11)
    bp.set_ylim(-11,11)
    bp.add_patch(Rectangle((-8,-8),16,16,facecolor="#f5ecdf",edgecolor=orange,lw=1.5))
    for x in [-2.5,0,2.5]:
        bp.add_patch(Circle((x,6.5),.55,fill=False,ec=blue))
    for x in [-5.65,5.65]:
        bp.add_patch(Rectangle((x-1,-1-.6),2,1.2,fill=False,ec=blue))
    bp.plot([-8,8],[0,0],color=gray,lw=.6,ls="--")
    bp.plot([0,0],[-8,8],color=gray,lw=.6,ls="--")
    bp.annotate("3 × Ø1.0 +0.1 /−0\nouter span5, Y+6.5",xy=(2.5,6.5),xytext=(-7,9),fontsize=9,color=blue,
        arrowprops=dict(arrowstyle="-",color=blue))
    bp.annotate("2 × support slots\n1.8 +0.2 /−0 ×1.1 +0.1 /−0\nspan11.3; Y−1",xy=(5.65,-1),xytext=(-9,-7),fontsize=9,color=blue,
        arrowprops=dict(arrowstyle="-",color=blue))
    bp.set_title("Required local substrate\n16 ×16 ×1.6 receiving outline",fontsize=11,color=orange)
    bp.set_xlabel("Local X")
    bp.set_ylabel("Local Y; chosen terminal orientation")
    bp.grid(alpha=.15)
    fig.text(.56,.15,"Panel: round Ø9.5 retained + blind lug pocket2.4 ×1.8 ×1.1.\n"
        "Pocket Y5.1..6.9, Z43.6..44.7 →0.9 nominal panel roof.\n"
        "Solder all metal lugs into a substrate; board lands/routing,\n"
        "terminal dimensions, support strength and harness remain open.",fontsize=9)
    fig.text(.05,.045,"DRAFT RECEIVING GEOMETRY · supplier tolerances/formal drawing, nut thread engagement, washer fit, actual temperatures,\n"
        "DC/wiper loading, knob retention, calibration and fabrication remain unapproved. FI01/PS01 are unchanged.",fontsize=9,color="#8c3030")
    fig.subplots_adjust(left=.06,right=.98,bottom=.30,top=.87,wspace=.32)
    for suffix in ["svg","png"]:
        fig.savefig(OUT / ("HT01-receiving." + suffix),dpi=150,facecolor="white")
    plt.close(fig)
    write(OUT / "drawing-provenance.json",dict(source_sha256={"drawing.py":sha(ROOT / "drawing.py"),"contract.py":sha(ROOT / "contract.py")},
        contract=report()["revision"], artifacts_sha256={n:sha(OUT/n) for n in ["HT01-receiving.svg","HT01-receiving.png"]},
        source_nominal_and_receiving_requirements_distinguished=True, vendor_image_redistributed=False,
        physical_qualified=False,fabrication_released=False))
    print(json.dumps(dict(artifacts=2)))


if __name__ == "__main__":
    build()
