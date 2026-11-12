"""Rebuild from only declared inputs in an isolated temporary repository-shaped package."""
import json,shutil,tempfile,subprocess,sys,hashlib
from contracts import *
closure=json.loads((R/'source-closure.json').read_text());transitive=json.loads((R/'transitive-source-review.json').read_text())
target=Path(tempfile.mkdtemp(prefix='tbh-panel-relocation-',dir='/private/tmp'));rel=R.relative_to(REPO);dest=target/rel
paths={REPO/p for p in closure['inputs']}|{R/p for p in closure['outputs']}|{REPO/e['resolved'] for e in transitive['transitive_panel_contract']}|{R/'source-closure.json',R/'transitive-source-review.json'}
# Imported common Python package metadata is required even when absent from source file imports.
paths|={REPO/'hardware/electronics/common/__init__.py'}
for p in paths:
 q=target/p.relative_to(REPO);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
for script in ['seal.py','audit_sources.py']:
 p=subprocess.run([sys.executable,str(dest/script)],capture_output=True,text=True,timeout=60)
 assert p.returncode==0,(script,p.stdout,p.stderr)
# All regenerated outputs must remain identical regardless of location.
rebuilt=json.loads((dest/'source-closure.json').read_text());assert rebuilt['outputs']==closure['outputs']
report=dict(passed=True,relocated_root=str(target),copied_files=len(paths),identical_generated_outputs=len(closure['outputs']),original_source_unchanged=all(hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h for p,h in closure['inputs'].items()))
assert report['original_source_unchanged'];(R/'relocation-review.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
