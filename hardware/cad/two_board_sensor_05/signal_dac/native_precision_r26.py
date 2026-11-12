"""Read exact native approximation controls for both immutable board snapshots."""
import sys,json,hashlib
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
R=Path(__file__).resolve().parent
paths={'before':R.parent/'signal_input/native-r7/signal_main.kicad_pcb','after':R/'native-r26/signal_main.kicad_pcb'}
rows={}
for role,p in paths.items():
 b=pcbnew.LoadBoard(str(p));rows[role]={'pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'max_polygonization_error_internal_units':b.GetDesignSettings().m_MaxError,'max_polygonization_error_mm':b.GetDesignSettings().m_MaxError/1e6}
assert rows['before']['max_polygonization_error_internal_units']==rows['after']['max_polygonization_error_internal_units']==5000
report={'native_version':pcbnew.GetBuildVersion(),'boards':rows,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),*paths.values()]},'units_per_mm':1000000}
(R/'native-precision-r26/report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
