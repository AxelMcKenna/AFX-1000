"""Finite circular aperture free area, exact nominal mesh phase and sensitivity."""
import json,hashlib
from pathlib import Path
from shapely.geometry import Point,box
from shapely.ops import unary_union
R=Path(__file__).resolve().parent
circle=Point(0,0).buffer(18,resolution=4096)
def area(dx,dz):
 strips=[]
 for i in range(-10,11):
  x=i*2.54+dx;z=i*2.54+dz
  strips.extend([box(x-.127,-20,x+.127,20),box(-20,z-.127,20,z+.127)])
 return circle.difference(unary_union(strips)).area
v=[area(i*2.54/16,j*2.54/16) for i in range(16) for j in range(16)]
r=dict(mesh='Howard Wire Cloth 304SS woven 10 mesh, .010 inch wire',product_url='https://howardwire.com/products/304-ss-woven-10-mesh-010',technical_table_url='https://www.iwmesh.com/technical-mesh/',wire_diameter_mm=.254,pitch_mm=2.54,nominal_opening_mm=2.286,infinite_grid_open_fraction=.81,aperture_diameter_mm=36,authored_zero_phase_open_mm2=area(0,0),phase_16x16_sensitivity_mm2=[min(v),max(v)],phase_scan_is_not_continuous_bound=True,mesh_supplier_tolerance_received=False,pressure_loss_or_finger_test_qualified=False,source_sha256={str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
(R/'mesh-area.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
