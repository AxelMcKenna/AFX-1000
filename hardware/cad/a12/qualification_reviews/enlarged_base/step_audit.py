"""Read the existing EB01 STEP artifacts; no design/native solver rerun."""
import hashlib
import json
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

ROOT = Path('/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base')
OUT = Path(__file__).parent
meta = json.loads((ROOT/'generated/cad-verification.json').read_text())
result = {}
for label in ('BASE','FOOT'):
    path = ROOT/'generated'/('AFX-EB01-'+label+'.step')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    shape = cq.importers.importStep(str(path)).val()
    bound = shape.BoundingBox()
    cylinders = []
    if label=='FOOT':
        for face in shape.Faces():
            if face.geomType()=='CYLINDER':
                cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
                cylinders.append(cylinder.Radius())
    volume = shape.Volume()
    expected = meta['base_volume_mm3' if label=='BASE' else 'foot_volume_mm3']
    assert shape.isValid() and len(shape.Solids())==1
    assert abs(volume-expected)<1e-6
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    result[label] = dict(sha256=before,valid=True,solids=1,volume_mm3=volume,
                         declared_volume_matches=True,surface_area_mm2=shape.Area(),
                         bbox_mm=[bound.xmin,bound.ymin,bound.zmin,bound.xmax,bound.ymax,bound.zmax],
                         cylindrical_radii_mm=cylinders)
assert any(abs(r-1.25)<1e-9 for r in result['FOOT']['cylindrical_radii_mm'])
assert all(abs(r-1.51)>1e-9 for r in result['FOOT']['cylindrical_radii_mm'])
payload=dict(existing_STEP_artifacts_only=result,manufacturing_foot_preserves_2p5_pilot=True,
             no_design_rebuild_or_native_rerun=True,new_physical_qualification=False,
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'step-audit-result.json').write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload,indent=2))
