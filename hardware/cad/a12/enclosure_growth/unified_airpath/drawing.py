"""CPU dimensioned review drawing sourced from actual candidate contracts."""
import json
from pathlib import Path
from .ground_route import ROOT,sha,write

def build():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    out=ROOT/'generated';target=out/'UA01-dimensioned-review.svg'
    if target.exists() or (ROOT/'handoff.json').exists():raise RuntimeError('New drawing output required')
    sources=[ROOT/'return_variant3/generated/geometry.json',ROOT/'positive_variant27/design.json',out/'ground-route.json']
    ret,pb,g=[json.loads(p.read_text()) for p in sources]
    fig=plt.figure(figsize=(16,11));grid=fig.add_gridspec(2,2,height_ratios=[2,1]);ax=fig.add_subplot(grid[0,:]);side=fig.add_subplot(grid[1,0]);note=fig.add_subplot(grid[1,1]);note.axis('off')
    for name,b in ret['bars'].items():
        pts=b['points_mm'];ax.plot([p[0] for p in pts],[p[1] for p in pts],lw=7,alpha=.65,label='R04 '+name+' return');side.plot([p[0] for p in pts],[p[2] for p in pts],lw=4,label='R04 '+name)
    for name,b in pb['paths'].items():
        pts=b['points'];ax.plot([p[0] for p in pts],[p[1] for p in pts],lw=3,label='PB27 '+name+' positive');side.plot([p[0] for p in pts],[p[2] for p in pts],lw=2,label='PB27 '+name)
    pts=g['paths_mm']['dense'];ax.plot([p[0] for p in pts],[p[1] for p in pts],color='black',lw=1.6,label='G129 actual GND');side.plot([p[0] for p in pts],[p[2] for p in pts],color='black',lw=1.6,label='G129')
    for xy in [[166,113],[166,134.625]]:
        ax.add_patch(Circle(xy,1.75,fill=False,color='red'));ax.annotate(f'base/floor axis {xy[0]}, {xy[1]}',xy,xytext=(xy[0]+10,xy[1]+8),arrowprops=dict(arrowstyle='->'),fontsize=8)
    ax.scatter([161,188],[129.5,104],color='black',s=18);ax.annotate('J4.2: (161,129.5), face6.62', (161,129.5),xytext=(112,148),arrowprops=dict(arrowstyle='->'),fontsize=8);ax.annotate('J13.2: (188,104), face8.10', (188,104),xytext=(193,98),arrowprops=dict(arrowstyle='->'),fontsize=8)
    ax.set(xlim=(45,220),ylim=(88,157),xlabel='World X / mm',ylabel='World Y / mm',title='UA01 / R04 / PB27 — dimensioned candidate routing and support plan');ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(loc='lower left',fontsize=8,ncol=3)
    side.axhline(9,color='red',ls=':',lw=1,label='R04 head bottom9.0');side.axhline(8.46,color='grey',ls='--',lw=1,label='P03 maxPCBtop8.46');side.set(xlabel='World X / mm',ylabel='World Z / mm',ylim=(-1,36),title='Nominal elevation; all terminal planes matched to measured assembly');side.grid(alpha=.2);side.legend(fontsize=7,ncol=2)
    note.text(0,1,'REVIEW CANDIDATE — NOT RELEASED\n\nR04 Cu6.0±0.1 ×3.50±0.05; landsØ10±0.1; holesØ4±0.05.\nMinimum screened normal section20.1425mm² incl edge-break allocation.\nANA dogleg: (153,133.125) →(160,134.625) →(173,134.625).\nANA support/floor bore moves133.125→134.625Y; no duplicate old hole.\nBase:Ø2.4 through;Ø4.8/90° CSK, depth1.2 in6.2 plate.\nR04 PEEK head bottom9.0; OD3 stem remains in4mm board gap.\n\nPB27 ANA road bottom26.0; north saddle screw offset−6.0Y.\nPB Cu6.4 nominal ×1.2 nominal; analytical net section≥6mm².\nPorts and DIG route unchanged; wrap/contact/torque unqualified.\n\nG129 continuous R≥9.92294 (>9.6393 hard requirement).\nMax insulationOD1.7526; coreØ1.4 receiving requirement.\nPosition±0.65; external clearance0.25; geometry reserve0.005.\nReceiver straight7.0; bare3.1; cut/strain slack not allocated.\n\nH9 access requires panel+guide/control assembly removal.\nAll boards/parts/process/material/contact/thermal qualification FALSE.',va='top',fontsize=9,linespacing=1.35)
    fig.tight_layout();fig.savefig(target);fig.savefig(out/'UA01-dimensioned-review.png',dpi=150);plt.close(fig)
    write(out/'drawing-inputs.json',dict(source_sha256={str(p):sha(p) for p in sources+[Path(__file__)]},artifact_sha256={str(p):sha(p) for p in [target,out/'UA01-dimensioned-review.png']},not_a_fabrication_release=True))
if __name__=='__main__':build()
