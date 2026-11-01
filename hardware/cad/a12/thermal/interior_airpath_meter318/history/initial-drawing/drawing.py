"""Dimensioned AP03 plan/section derived from the captured source values."""

import json

from .stage import OUT, ROOT, sha, write


def build():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    png=OUT/"AP03-layout.png"
    if png.exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("New drawing destination required")
    d=json.loads((OUT/"analysis.json").read_text())
    budget=json.loads((OUT/"channel-budget.json").read_text())
    fig=plt.figure(figsize=(14,9),layout="constrained")
    gs=fig.add_gridspec(2,2,height_ratios=[2.6,1.5],width_ratios=[1.6,1])
    ax=fig.add_subplot(gs[0,:])
    ax.add_patch(Rectangle((0,0),334,188.4,fill=False,linewidth=1.5,color="#1d3745"))
    for x,y in d["kept_pins"]:
        ax.add_patch(Rectangle((x-1.5,y-1.5),3,3,color="#bdc6cd",linewidth=0))
    for x,y in d["additional_whole_removed"]:
        ax.add_patch(Rectangle((x-1.5,y-1.5),3,3,fill=False,edgecolor="#db591a",linewidth=1))
    for x0,y0,x1,y1 in d["bay_outer_XY"]:
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor="#007f89",linewidth=2))
    for x in [80,254]:
        ax.add_patch(Rectangle((x-20.25,145.25),40.5,40.5,fill=False,edgecolor="#5760ad",linewidth=1.3))
        ax.add_patch(Rectangle((x-10,134.5),20,2,facecolor="#db591a"))
        ax.plot([x-18,x+18],[142,142],"--",color="#a55f5f",linewidth=.8)
        ax.text(x,129,"16 × 10 R1 meter",ha="center",fontsize=8)
    for x,y in [[20,20],[314,20],[20,168.4],[314,168.4]]:
        ax.add_patch(Circle((x,y),14,fill=False,color="#444",linewidth=.8))
    ax.text(167,196,"334 mm × 188.4 mm — existing enclosure, ports and feet unchanged",ha="center",fontsize=11)
    ax.text(167,118,"Rear wall Y137..139  •  old wall Y142 shown dashed  •  fan back Y145.25",ha="center",fontsize=9)
    ax.set(xlim=(-7,341),ylim=(203,-5),aspect="equal",xlabel="World X (mm)",ylabel="World Y (mm)")
    ax.set_title("AP03 — larger metered base outlet / rear approach",loc="left",fontweight="bold")
    ax.grid(alpha=.12)
    side=fig.add_subplot(gs[1,0])
    side.add_patch(Rectangle((137,-24.7),2,18,facecolor="#007f89",alpha=.8))
    side.add_patch(Rectangle((134.5,-24.2),2,17.5,facecolor="#db591a",alpha=.8))
    side.add_patch(Rectangle((136.5,-24.2),.5,17.5,facecolor="#e9b44c"))
    for xx,w in [(134.5,2),(136.5,.5),(137,2)]:
        side.add_patch(Rectangle((xx,-22),w,10,facecolor="white",edgecolor="none"))
    side.add_patch(Rectangle((145.25,-24.7),15,10.4,facecolor="#757dcc",alpha=.6))
    side.add_patch(Rectangle((145.25,-14.3),15,2.1,facecolor="#abb2ed",alpha=.8))
    side.plot([132,162],[-6.2,-6.2],color="#111",linewidth=2)
    side.plot([144.95,144.95],[-24.7,-12.2],"--",color="#5760ad",linewidth=.8)
    side.annotate("6.25 nominal\n5.95 at −0.30 fan-Y",xy=(142,-16),xytext=(149,-10),fontsize=8,arrowprops=dict(arrowstyle="->"))
    side.annotate("10 mm aperture\nZ −22..−12",xy=(138,-20),xytext=(129,-16),ha="right",fontsize=8,arrowprops=dict(arrowstyle="->"))
    side.text(142,-27.7,"Y section at meter centre (bolt row lies outside this section)",ha="center",fontsize=8)
    side.set(xlim=(124,164),ylim=(-28,-3.5),aspect="equal",xlabel="World Y (mm)",ylabel="World Z (mm)")
    side.grid(alpha=.12)
    notes=fig.add_subplot(gs[1,1])
    notes.axis("off")
    lines=[
        "NATIVE GEOMETRY: 32 main + 22 nominal-interface cases pass",
        "899 retained pins; 19 additional whole pins removed vs AP02",
        f"Two actual faceted apertures: {budget['meter_actual_faceted_total_mm2']:.4f} mm² total",
        "Every-height approach lower bounds: 208.03 / 204.43 mm²",
        "Includes full nut/shank/FIP AABBs; no sampled minimum",
        "Extra wall/component sensitivity: right ≥183.29 mm²",
        "5300 rpm / Cd .6: meter 1.717 Pa; 3.322 Pa remains",
        "Remaining budget must cover ALL approach/pins/turns/outlet",
        "No installed-flow, seal, strength, thermal or fabrication approval",
        "Historical AP02 boards/controls/wires; no latest-unit adoption",
    ]
    for i,line in enumerate(lines):
        notes.text(0,.96-i*.092,line,fontsize=8.5,va="top")
    fig.savefig(png,dpi=155)
    fig.savefig(OUT/"AP03-layout.svg")
    plt.close(fig)
    write(OUT/"drawing-provenance.json",dict(source_sha256={"drawing.py":sha(ROOT/"drawing.py"),
        "generated/analysis.json":sha(OUT/"analysis.json"),"generated/channel-budget.json":sha(OUT/"channel-budget.json")},
        artifact_sha256={n:sha(OUT/n) for n in ["AP03-layout.png","AP03-layout.svg"]},
        drawing_receiving_requirements_not_factory_tolerances=True,physical_qualified=False))


if __name__=="__main__":
    build()
