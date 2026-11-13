"""Bind all newly added electrical footprints to exact native schematic UUID paths."""
import xml.etree.ElementTree as ET
from hardware.electronics.common.sexpr import read_sexpr,children,first,Atom
NEW_REFS={'P_C906','E_C900','P_C902','P_L900','P_R902','P_C904','P_C900','P_R903','P_U901','P_R900','P_C903','E_U900','P_U902','P_C905','P_R901','P_C901','P_U900','E_R900','P_C907'}
def expected_paths(schematic,netlist):
 rootid=first(read_sexpr(schematic.read_text()),'uuid')[1];tree=ET.parse(netlist);paths={}
 for c in tree.findall('./components/comp'):
  ids=c.findtext('tstamps').split();assert len(ids)==1
  paths[c.attrib['ref']]='/'+rootid+c.find('sheetpath').attrib['tstamps']+ids[0]
 assert len(set(paths.values()))==len(paths)
 return paths

def bind(board,paths):
 changes=[];mechanical=[];unchanged=[];seen=set()
 for f in children(board,'footprint'):
  ref=next(p[2] for p in children(f,'property') if p[1]=='Reference');assert ref not in seen;seen.add(ref)
  if ref not in paths:mechanical.append(ref);continue
  ps=children(f,'path');assert len(ps)<=1
  if ps:assert ps[0][1]==paths[ref],ref;unchanged.append(ref)
  else:
   assert ref in NEW_REFS,ref;f.append([Atom('path'),paths[ref]]);changes.append({'reference':ref,'before':None,'after':paths[ref]})
 assert set(paths)<=seen and {r['reference'] for r in changes}==NEW_REFS
 return {'changes':changes,'unchanged_existing_associations':len(unchanged),'mechanical_footprints_without_schematic_symbols':sorted(mechanical),'all_electrical_footprints_have_unique_exact_schematic_paths':True}
