"""Reject quoted or non-finite zone coordinates before native load/fill."""
import math
from hardware.electronics.common.sexpr import Atom,children,first

def zone_coordinates(zone):
 polygons=children(zone,'polygon');assert polygons,'Zone has no polygon';result=[]
 for poly in polygons:
  points=children(first(poly,'pts'),'xy');assert len(points)>=3,'Zone polygon requires at least three points';row=[]
  for xy in points:
   assert len(xy)==3 and all(isinstance(v,Atom) for v in xy[1:]),'Coordinate must be an unquoted numeric atom'
   values=list(map(float,xy[1:]));assert all(math.isfinite(v) for v in values),'Coordinate must be finite';row.append(values)
  result.append(row)
 return result
