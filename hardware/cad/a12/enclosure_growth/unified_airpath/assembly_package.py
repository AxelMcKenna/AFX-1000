"""Preserve the first geometry-complete package; correct ONLY its OPC namespace."""
import json
import zipfile
from pathlib import Path
from hardware.cad.a12.thermal.interior_airpath_meter318.assembly import roundtrip_errors
from .ground_route import ROOT,sha,write

def build():
    folder=ROOT/'generated';old=folder/'UA01-complete-modeled-component-review.3mf';new=folder/'UA01-component-review.3mf'
    if new.exists() or (ROOT/'handoff.json').exists():raise RuntimeError('New package required')
    with zipfile.ZipFile(old) as source,zipfile.ZipFile(new,'w',compression=zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename=='[Content_Types].xml':
                assert b'http://schemas.openxmlformats-package.org/package/2006/content-types' in data
                data=data.replace(b'http://schemas.openxmlformats-package.org/package/2006/content-types',b'http://schemas.openxmlformats.org/package/2006/content-types')
            target.writestr(item.filename,data)
    d=json.loads((folder/'assembly-manifest.json').read_text())
    assert not roundtrip_errors(new,d['objects'])
    with zipfile.ZipFile(old) as a,zipfile.ZipFile(new) as b:
        assert a.read('3D/3dmodel.model')==b.read('3D/3dmodel.model')
    d['first_package_OPC_namespace_invalid_preserved']=True
    d['model_XML_unchanged_from_first_package']=True
    d['artifact_sha256']={str(new):sha(new)}
    d['source_sha256'].update({str(Path(__file__)):sha(Path(__file__)),str(old):sha(old),str(folder/'assembly-manifest.json'):sha(folder/'assembly-manifest.json')})
    write(folder/'assembly-manifest-corrected.json',d)
    print(json.dumps(dict(objects=len(d['objects']),triangle_geometry_unchanged=True,package_sha256=sha(new))))
if __name__=='__main__':build()
