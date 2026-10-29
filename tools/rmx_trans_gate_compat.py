#!/usr/bin/env python3
"""Require all 146 current Gate/Drive WAVs to retain their qualified parent bytes."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from tools import rmx_isolate_modes as modes
from tools.reference_audio import save_json,sha256
from tools.rmx_factory_match import new_directory,run
from tools.rmx_drums import require


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['host','renderer','parent-root','original-root','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();binding=modes.source_hashes();script=sha256(Path(__file__));binary=sha256(a.renderer);root=new_directory(a.output);rows=[];parents={}
 for suffix,stage,original in [('discovery','discovery','rmx-isolate-modes-discovery-20261029'),('former-fresh','gate-fresh','rmx-gate-drive-fresh-v2-20261029'),('fresh2','gate-fresh2','rmx-gate-drive-fresh2-20261029'),('lifecycle','gate-lifecycle','rmx-gate-drive-lifecycle-20261029'),('lifecycle2','gate-lifecycle2','rmx-gate-drive-lifecycle2-20261029')]:
  report=a.parent_root/f'gate-drive-live-first-{suffix}/comparison.json';published=Path(f'research/audio/measurements/2026-10-29-gate-drive-live-{suffix}.json');require(sha256(report)==sha256(published),'Published Gate parent changed');parents[suffix]=sha256(report);d=json.loads(report.read_text());old={r['case']:r for r in d['cases']};cases=[c for c in modes.recipe(stage) if c['mode']=='gatedrive'];args=SimpleNamespace(stage=stage,session=a.original_root/original,host=a.host)
  for c in cases:
   _,provenance=modes.original(args,c);row=old[c['name']];require(row['passed'] and all(row[k]==v for k,v in provenance.items()),'Gate parent provenance changed');candidate=report.parent/(c['name']+'.wav');require(sha256(candidate)==row['candidate_sha256'],'Parent audio changed');plan=root/(c['name']+'.tsv');plan.write_text(modes.schedule(c));require(sha256(plan)==row['schedule_sha256'],'Parent schedule changed');out=plan.with_suffix('.wav');run([a.renderer,args.session/(c['source']+'.wav'),out,plan]);require(sha256(out)==row['candidate_sha256'],'Gate audio changed: '+c['name']);rows.append(provenance|dict(passed=True,candidate_sha256=sha256(out),whole_wav_parent_byte_identity=True));print('UNCHANGED',c['name'],flush=True)
 require(len(rows)==146 and binding==modes.source_hashes() and binary==sha256(a.renderer) and script==sha256(Path(__file__)),'Coverage/source changed');save_json(root/'verification.json',dict(kind='rmx220-transroll-prior-gatedrive-byte-compatibility',passed=True,programs=146,cases=rows,source_sha256=binding,verifier_sha256=script,renderer_sha256=binary,parent_reports_sha256=parents,scope='All146 prior Gate/Drive programs; current native complete WAV bytes equal the qualified live parent, with original provenance rechecked. Transfers existing gates, no new capture or wrapper/sanitizer claim.'))
if __name__=='__main__':main()
