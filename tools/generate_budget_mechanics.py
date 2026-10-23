#!/usr/bin/env python3
"""B1 split enclosure source, drawings and independently meshed flat fit parts.

STLs made here use Shapely planar geometry, not the untrusted OpenSCAD bundle.
The complete enclosure SCAD still needs solid rendering / assembly inspection.
"""
import argparse
import collections
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
from generate_hardware import validate, artifacts, preview

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'hardware/budget'


def model():
    d=json.loads((ROOT/'hardware/prototype.json').read_text())
    d['revision']='B1 5V split fit prototype'
    d['status']='Dimensioned fit candidate; actual supplier parts and complete solid assembly unverified'
    d['enclosure']['panel_thickness']=3
    for c in d['controls']:
        if c['kind']=='pot':c['keepout']=[max(24,c['keepout'][0])]*2
    ports=[('in_l',20,16,'circle',8.5,8.5),('in_r',42,16,'circle',8.5,8.5),
           ('out_l',72,16,'circle',8.5,8.5),('out_r',94,16,'circle',8.5,8.5),
           ('usb_power_lead',127,16,'circle',6.5,6.5),('power_switch',151,16,'circle',6.5,6.5),
           ('manual_bypass',182,16,'circle',6.5,6.5),('usb_service',212,16,'rect',12,8),
           ('sd',246,16,'rect',16,3)]
    d['rear_ports']=[dict(id=i,x=x,z=z,shape=s,w=w,h=h) for i,x,z,s,w,h in ports]
    d['seam_screws']=[[159,y] for y in (8,147)]+[[175,y] for y in (8,147)]
    d['carrier']={'origin':[194,8],'size':[100,100],'standoff_height':3,'pcb_thickness':1.6,
        'holes':[[4,4],[96,4],[4,96],[96,96]],'maximum_component_height':12}
    validate(d)
    for a,b in zip(d['rear_ports'],d['rear_ports'][1:]):
        assert b['x']-b['w']/2-(a['x']+a['w']/2)>=5,'Rear connector collision'
    for x,y in d['seam_screws']:
        for c in d['controls']:
            assert math.hypot(max(0,abs(x-c['x'])-c['w']/2),max(0,abs(y-c['y'])-c['h']/2))>2.2,'Seam screw / '+c['id']
    assert 167+13<=220 and d['enclosure']['depth']<=220
    return d


SCAD='''// B1 5V fit prototype. Generated geometry; dimensions still need purchased-part checks.
include <../generated/panel_geometry.scad>
$fn=64;
part="assembly"; // panel_left/right, tray_left/right, joiner, knob, button, lever, assembly
explode=12;
module outline(w=width,d=depth,r=corner_radius) {
    hull() for(x=[r,w-r],y=[r,d-r]) translate([x,y]) circle(r=r);
}
module panel() {
    linear_extrude(panel_thickness) difference() {
        outline(); panel_cutouts();
    }
}
module tray() {
    difference() {
        union() {
            difference() {
                linear_extrude(tray_height) outline();
                translate([wall,wall,wall]) linear_extrude(tray_height)
                    outline(width-2*wall,depth-2*wall,corner_radius-wall);
            }
            for(p=posts) translate([p[0],p[1],wall]) difference() {
                cylinder(h=tray_height-wall-1,r=4.5); cylinder(h=tray_height,r=1.25);
            }
            // Carrier mounting holes match the 100x100 PCB's four 4mm-inset holes.
            for(x=[198,290],y=[12,104]) translate([x,y,wall]) difference() {
                cylinder(h=3,r=3.4); cylinder(h=4,d=2.5);
            }
            // Slotted utility mounts for hand-wired control / Seed assemblies.
            for(x=[24,150,206,226],y=[48,112]) translate([x,y,wall]) difference() {
                cylinder(h=3,r=3.4); cylinder(h=4,d=2.5);
            }
        }
        rear_cutouts();
        for(x=[159,175],y=[20,137]) translate([x,y,-1]) cylinder(h=wall+2,d=3.4);
    }
}
module joiner() { // Four joiners: two under panel, two over the tray floor.
    linear_extrude(2) difference() {
        offset(r=2) square([22,8],center=true);
        for(x=[-8,8]) translate([x,0]) circle(d=3.4);
    }
}
module knob(d=18,bore=6.2) {
    difference() {
        cylinder(h=14,d=d);
        translate([0,0,-.1]) cylinder(h=11,d=bore);
        translate([-.5,d/2-5,13.4]) cube([1,5.5,1]);
        // M3 grub screw pilot; fit the shaft coupon before printing the full set.
        translate([0,-d/2-1,5]) rotate([-90,0,0]) cylinder(h=d/2,d=2.5);
    }
}
module button(w=8,h=8) { // Print face down; stem length is a fit parameter.
    translate([0,0,1]) cube([w-.4,h-.4,2],center=true);
    translate([0,0,2.5]) cube([w+1.2,h+1.2,1],center=true);
    translate([0,0,5]) cube([3.5,3.5,4],center=true);
}
module lever() { // Printed handle; separate shaft hub, return spring and stops are required.
    difference() {
        hull() {cylinder(h=6,d=12);translate([0,23,0]) cylinder(h=6,d=9);}
        translate([0,0,-1]) cylinder(h=8,d=6.2);
    }
}
module half(side=0) {
    intersection() {
        children();
        translate([side?167:-1,-1,-1]) cube([side?168:168,depth+2,100]);
    }
}
if(part=="panel_left") half(0) panel();
else if(part=="panel_right") translate([-167,0,0]) half(1) panel();
else if(part=="tray_left") half(0) tray();
else if(part=="tray_right") translate([-167,0,0]) half(1) tray();
else if(part=="joiner") joiner();
else if(part=="knob") knob();
else if(part=="button") button();
else if(part=="lever") lever();
else {
    color("#272c33") tray();
    translate([0,0,tray_height+explode]) color("#25292f") panel();
    translate([0,0,tray_height+panel_thickness+explode]) knob_envelopes();
    color([.1,.6,.5,.6]) translate([194,8,wall+3]) cube([100,100,1.6]);
    color([.9,.7,.1,.6]) translate([202,106,wall+3]) cube([25,46,13]);
}
'''


def mesh(polygon,height):
    from shapely.geometry.polygon import orient
    from shapely.geometry import Polygon
    import ctypes as ct
    import ctypes.util
    import sys
    library='/System/Library/Frameworks/OpenGL.framework/OpenGL' if sys.platform=='darwin' else ct.util.find_library('GLU')
    glu=ct.CDLL(library)
    glu.gluNewTess.restype=ct.c_void_p
    glu.gluTessCallback.argtypes=[ct.c_void_p,ct.c_uint,ct.c_void_p]
    glu.gluTessBeginPolygon.argtypes=[ct.c_void_p,ct.c_void_p]
    glu.gluTessBeginContour.argtypes=[ct.c_void_p]
    glu.gluTessVertex.argtypes=[ct.c_void_p,ct.POINTER(ct.c_double),ct.c_void_p]
    glu.gluTessEndContour.argtypes=[ct.c_void_p]
    glu.gluTessEndPolygon.argtypes=[ct.c_void_p]
    glu.gluDeleteTess.argtypes=[ct.c_void_p]
    glu.gluTessNormal.argtypes=[ct.c_void_p,ct.c_double,ct.c_double,ct.c_double]

    def triangulate(p):
        # GLU preserves polygon boundary constraints, including notches where
        # panel openings meet the split seam. Unconstrained Delaunay does not.
        vertices=[];storage=[];errors=[];primitives=[]
        @ct.CFUNCTYPE(None,ct.c_uint)
        def begin(kind):primitives.append(kind)
        @ct.CFUNCTYPE(None,ct.c_void_p)
        def vertex(pointer):
            v=ct.cast(pointer,ct.POINTER(ct.c_double));vertices.append((v[0],v[1]))
        @ct.CFUNCTYPE(None,ct.c_uint)
        def error(code):errors.append(code)
        @ct.CFUNCTYPE(None,ct.c_ubyte)
        def edge(flag):pass
        tess=glu.gluNewTess()
        assert tess,'GLU tessellator unavailable'
        try:
            for kind,callback in [(100100,begin),(100101,vertex),(100103,error),(100104,edge)]:glu.gluTessCallback(tess,kind,callback)
            glu.gluTessNormal(tess,0,0,1);glu.gluTessBeginPolygon(tess,None)
            for ring in [p.exterior,*p.interiors]:
                glu.gluTessBeginContour(tess)
                for x,y in list(ring.coords)[:-1]:
                    data=(ct.c_double*3)(x,y,0);storage.append(data)
                    glu.gluTessVertex(tess,data,ct.cast(data,ct.c_void_p))
                glu.gluTessEndContour(tess)
            glu.gluTessEndPolygon(tess)
            assert not errors and all(x==4 for x in primitives) and len(vertices)%3==0,('GLU error',errors,primitives)
            return [Polygon(vertices[i:i+3]) for i in range(0,len(vertices),3)]
        finally:glu.gluDeleteTess(tess)
    polygons=[polygon] if polygon.geom_type=='Polygon' else list(polygon.geoms)
    faces=[]
    for p in polygons:
        p=orient(p,sign=1)
        triangles=triangulate(p)
        assert all(p.buffer(1e-8).covers(t) for t in triangles),'Triangulation crosses a panel opening'
        assert abs(sum(t.area for t in triangles)-p.area)<1e-6,'Planar triangulation left gaps'
        for t in triangles:
            v=list(orient(t,sign=1).exterior.coords)[:3]
            faces.append([(x,y,height) for x,y in v]);faces.append([(x,y,0) for x,y in reversed(v)])
        for ring in [p.exterior,*p.interiors]:
            v=list(ring.coords)
            for a,b in zip(v,v[1:]):
                aa=(*a,0);bb=(*b,0);cc=(*b,height);dd=(*a,height)
                faces.extend([[aa,bb,cc],[aa,cc,dd]])
    edges=collections.Counter()
    volume=0
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((tuple(round(v,6) for v in a),tuple(round(v,6) for v in b))))]+=1
        a,b,c=f
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    assert all(n==2 for n in edges.values()),'STL has open/nonmanifold edges'
    assert abs(volume-polygon.area*height)<1e-5,'STL winding/volume mismatch'
    data=bytearray(b'RMX B1 flat fit part / independently checked mesh'.ljust(80,b' '))+struct.pack('<I',len(faces))
    for f in faces:data+=struct.pack('<12fH',0,0,0,*[n for v in f for n in v],0)
    return bytes(data),dict(triangles=len(faces),volume_mm3=round(volume,3),watertight=True)


def generate(d):
    out={'mechanics.json':json.dumps(d,indent=2)+'\n','cad/enclosure.scad':SCAD}
    drawings=copy.deepcopy(d)
    drawings['enclosure']['posts']+=d['seam_screws']
    for n,content in artifacts(drawings).items():
        if n=='BoardConfig.h':continue
        if n=='panel_geometry.scad':
            # Drawing holes include seam screws; only the original four posts
            # are full-height enclosure bosses. Seam joiners are separate parts.
            content=content.replace('posts='+json.dumps(drawings['enclosure']['posts'])+';','posts='+json.dumps(d['enclosure']['posts'])+';')
            content=content.replace('  for(p=posts) translate(p) circle(d=screw_diameter);',
                '  for(p=posts) translate(p) circle(d=screw_diameter);\n  for(p='+json.dumps(d['seam_screws'])+') translate(p) circle(d=screw_diameter);')
        content=content.replace('hardware/prototype.json','hardware/budget/mechanics.json').replace('RMX · A0','RMX · B1').replace('fit prototype · verify parts before fabrication','5V fit prototype · verify parts before fabrication')
        out['generated/'+n]=content
    return out


def export_stl(d):
    from shapely.geometry import Point,box
    from shapely.ops import unary_union
    e=d['enclosure'];r=e['corner_radius']
    outer=box(r,r,e['width']-r,e['depth']-r).buffer(r,resolution=16)
    holes=[]
    for c in d['controls']:
        holes.append(Point(c['x'],c['y']).buffer(c['w']/2,resolution=16) if c['shape']=='circle' else box(c['x']-c['w']/2,c['y']-c['h']/2,c['x']+c['w']/2,c['y']+c['h']/2))
    holes += [Point(x,y).buffer(e['screw_diameter']/2,resolution=16) for x,y in e['posts']+d['seam_screws']]
    panel=outer.difference(unary_union(holes))
    regions={'panel_left':(panel.intersection(box(-1,-1,167,200)),e['panel_thickness']),
             'panel_right':(panel.intersection(box(167,-1,400,200)),e['panel_thickness']),
             'joiner':(box(-11,-4,11,4).buffer(2,resolution=16).difference(unary_union([Point(x,0).buffer(1.7,resolution=16) for x in [-8,8]])),2),
             'shaft_coupon':(box(0,0,38,14).difference(unary_union([Point(7+i*12,7).buffer(d/2,resolution=16) for i,d in enumerate([6.0,6.1,6.2])])),4)}
    dest=DEST/'generated';dest.mkdir(parents=True,exist_ok=True);record={}
    for name,(region,z) in regions.items():
        if name=='panel_right':
            from shapely.affinity import translate
            region=translate(region,xoff=-167)
        data,metrics=mesh(region,z);(dest/(name+'.stl')).write_bytes(data)
        record[name]=dict(**metrics,sha256=hashlib.sha256(data).hexdigest())
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),ROOT/'hardware/prototype.json',DEST/'mechanics.json']}
    (dest/'flat-mesh-check.json').write_text(json.dumps(dict(scope='Flat fit parts only; tray and complete assembly not solid-rendered',source_sha256=sources,parts=record),indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--stl',action='store_true');parser.add_argument('--preview',action='store_true');a=parser.parse_args()
    d=model()
    for name,content in generate(d).items():
        p=DEST/name
        if a.check:assert p.exists() and p.read_text()==content,'Stale B1 mechanical file: '+name
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    if a.check:
        record=json.loads((DEST/'generated/flat-mesh-check.json').read_text())
        for n,digest in record['source_sha256'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==digest,'Stale STL source: '+n
        for n,part in record['parts'].items():assert hashlib.sha256((DEST/'generated'/(n+'.stl')).read_bytes()).hexdigest()==part['sha256'],'Stale STL mesh: '+n
    if a.preview:
        drawings=copy.deepcopy(d);drawings['enclosure']['posts']+=d['seam_screws']
        path=DEST/'generated/panel.png';preview(drawings,path)
        from PIL import Image,ImageDraw,ImageFont
        im=Image.open(path);draw=ImageDraw.Draw(im);draw.rectangle((10,10,400,34),fill='#20262e')
        font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',10)
        draw.text((20,20),'RMX / B1 5V SPLIT FIT PROTOTYPE',font=font,fill='white')
        for y in range(45,735,12):draw.line((835,y,835,y+5),fill='#92a4b8')
        im.save(path)
    if a.stl:export_stl(d)
    print('PASS: B1 panel/rear-port/PCB-mount geometry; full 3D fit remains unverified')


if __name__=='__main__':main()
