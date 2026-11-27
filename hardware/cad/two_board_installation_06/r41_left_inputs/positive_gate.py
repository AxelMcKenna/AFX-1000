"""Strict clean native positive operand contract, matching the r40 handoff gate."""
def require_clean_positive(result):
 assert not result['runtime_failure'] and not result['empty']
 mesh=result['mesh']
 assert mesh and mesh['triangles']>0 and mesh['volume_mm3']>0
 assert mesh['closed_oriented_boundary'] is True
 assert mesh['degenerate_triangles_excluded']==0, 'Positive operand contains excluded degenerate facets'
 assert mesh['bad_directed_edges']==0, 'Positive operand contains bad directed edges'
