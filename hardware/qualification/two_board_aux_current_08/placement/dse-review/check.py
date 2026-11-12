"""Cross-check the source drawing vector extents, independent of footprint code."""
import hashlib,json,re,xml.etree.ElementTree as E
from pathlib import Path
H=Path(__file__).resolve().parent
s=(H/'ti-page38.svg').read_text();root=E.fromstring(s)
colors={'exposed_blue':'rgb(0%, 50%, 100%)','outer_green':'rgb(42.999268%, 94.999695%, 0%)'}
points={k:[] for k in colors};counts={k:0 for k in colors}
for e in root.iter():
    for name,color in colors.items():
        if e.attrib.get('stroke')!=color:continue
        nums=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',e.attrib.get('transform',''))))
        if len(nums)!=6:continue
        a,b,c,d,tx,ty=nums
        vals=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',e.attrib['d'])))
        pts=[(a*x+c*y+tx,b*x+d*y+ty) for x,y in zip(vals[::2],vals[1::2])]
        if pts and all(200<x<310 and 190<y<239 for x,y in pts):points[name]+=pts;counts[name]+=1
scale=40*72/25.4
bounds={k:[min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)] for k,p in points.items()}
widths={k:(b[3]-b[1])/scale for k,b in bounds.items()}
assert abs(widths['exposed_blue']-.25)<.0001
assert abs(widths['outer_green']-.35)<.0001
r={'source_pdf_sha256':hashlib.sha256((H.parent.parent/'fast_inhibit/primary/tps3703.pdf').read_bytes()).hexdigest(),'rendered_svg_sha256':hashlib.sha256((H/'ti-page38.svg').read_bytes()).hexdigest(),'drawing':'4220552/B 01/2024','page':38,'scale_points_per_mm':scale,'pin1_vector_bounds_points':bounds,'vector_path_count':counts,'pin1_transverse_width_mm':widths,'interpretation':'Drawing dimension arrows terminate at exposed-blue boundaries. For left SMD pads, blue is mask opening and green is copper; for right NSMD pads blue is copper and green is mask opening. Page39 stencil repeats 0.25 mm aperture. The 0.05 mm SMD overlap is not already included in the 0.25 mm dimension.','derived_left_copper_gap_mm':.5-.35,'manufacturer_guaranteed_fabrication_clearance':False}
(H/'vector-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
# Preserve source vector rendering unmodified, with clearly separate review notes.
notes=['Independent reading of TI page 38','Blue outlines: exposed areas, 0.25 mm wide.','Left pads 1-3: blue is the mask opening.','Green extends 0.05 mm on EACH side.','Thus left copper width = 0.35 mm.','Pitch 0.50 - copper 0.35 = 0.15 mm gap.','The extra overlap is NOT already included.','','Right pads 4-6: blue is the copper.','Green is the larger mask opening.','Do not identify material by color alone.','','Below: TI explicitly labels the left bank SMD.','Page 39 separately repeats 0.25-mm stencil apertures.','Vector extraction confirms widths, independent','of authored footprint dimensions.','','This annotation is our interpretation,','not a TI manufacturing approval.']
over='<g font-family="sans-serif" font-size="11" fill="#17334c">'+''.join(f'<text x="625" y="{160+i*19}">{t}</text>' for i,t in enumerate(notes))+'</g><path d="M 620 196 L 300 214 M 620 234 L 300 194 M 620 385 L 420 565" fill="none" stroke="#ac3535" stroke-width="1"/>'
s=re.sub(r'width="[^"]+"','width="1000pt"',s,count=1);s=re.sub(r'viewBox="[^"]+"','viewBox="0 0 1000 792"',s,count=1)
(H/'annotated-page38.svg').write_text(s.replace('</svg>',over+'</svg>'))
