"""Validate frozen source closure and normalize original absolute provenance paths."""
import hashlib,json
from contracts import *
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit():
 closure=json.loads((R/'source-closure.json').read_text());checked=[]
 for name,h in closure['inputs'].items():
  p=REPO/name;assert p.is_file(),name;assert sha(p)==h,name;checked.append(name)
 for name,h in closure['outputs'].items():
  p=R/name;assert p.is_file(),name;assert sha(p)==h,name
 supplement=json.loads((R/'reference/button-contact-contract.json').read_text())
 assert sha(R/'reference/Omron-B3F.pdf')==supplement['source_sha256']
 upstream=[]
 for e in json.loads((R/'reference/panel-contract.json').read_text())['sources']:
  normalized='hardware/'+e['path'].split('hardware/',1)[1]
  p=R/'reference/installation-r7-interface-manifest.json' if normalized=='hardware/cad/two_board_installation_06/r7/interface-manifest.json' else REPO/normalized
  assert p.is_file(),normalized;assert sha(p)==e['sha256'],normalized
  upstream.append(dict(original=e['path'],resolved=str(p.relative_to(REPO)),sha256=e['sha256']))
 report=dict(source_closure_inputs=len(checked),generated_outputs=len(closure['outputs']),transitive_panel_contract=upstream,passed=True)
 (R/'transitive-source-review.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(audit())
