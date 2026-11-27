"""Capture actual local native copper and filled In6 geometry for a static review."""
import json,sys,hashlib
from pathlib import Path
import pcbnew
p=Path(sys.argv[1]);out=Path(sys.argv[2]);board=pcbnew.LoadBoard(str(p));region=pcbnew.BOX2I(pcbnew.VECTOR2I(pcbnew.FromMM(186),pcbnew.FromMM(138)),pcbnew.VECTOR2I(pcbnew.FromMM(19),pcbnew.FromMM(19)))
def polygons(poly):
 def pts(c):return [[pcbnew.ToMM(c.CPoint(i).x),pcbnew.ToMM(c.CPoint(i).y)] for i in range(c.PointCount())]
 return [dict(outer=pts(poly.COutline(i)),holes=[pts(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]) for i in range(poly.OutlineCount())]
rows=[]
for item in [pad for f in board.GetFootprints() for pad in f.Pads()]+list(board.GetTracks()):
 if not item.IsOnLayer(pcbnew.B_Cu) or not item.GetBoundingBox().Intersects(region):continue
 poly=pcbnew.SHAPE_POLY_SET();item.TransformShapeToPolygon(poly,pcbnew.B_Cu,0,pcbnew.FromMM(.001),pcbnew.ERROR_OUTSIDE);poly.Simplify();r={'uuid':item.m_Uuid.AsString(),'kind':item.GetClass(),'net':item.GetNetname(),'polygons':polygons(poly)}
 if item.GetClass()=='PAD':r.update(ref=item.GetParentFootprint().GetReference(),pin=item.GetNumber())
 if item.GetClass()=='PCB_VIA':r.update(position_mm=[pcbnew.ToMM(item.GetPosition().x),pcbnew.ToMM(item.GetPosition().y)],drill_mm=pcbnew.ToMM(item.GetDrillValue()))
 rows.append(r)
z=next(z for z in board.Zones() if z.m_Uuid.AsString()=='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb');poly=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(board.GetLayerID('In6.Cu')));poly.Unfracture()
(out/'local-native-geometry.json').write_text(json.dumps({'source_pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'native_version':pcbnew.Version(),'viewport_mm':[186,138,19,19],'objects':rows,'reference_polygons':polygons(poly)},separators=(',',':'))+'\n')
