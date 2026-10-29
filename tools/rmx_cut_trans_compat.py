#!/usr/bin/env python3
"""Require all 146 live Trans/Roll programs to retain their qualified parent WAV bytes."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from tools import rmx_isolate_modes as modes
from tools import rmx_trans_match as trans
from tools.reference_audio import save_json,sha256
from tools.rmx_factory_match import new_directory,run
from tools.rmx_drums import require


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['host','renderer','parent-root','original-root','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();binding=trans.bindings();script=sha256(Path(__file__));binary=sha256(a.renderer);root=new_directory(a.output);rows=[];parents={}
 for stage in ['discovery','fresh','lifecycle','fresh2','lifecycle2']:
  report=a.parent_root/f'trans-live-final-{stage}/comparison.json';published=Path(f'research/audio/measurements/2026-10-29-trans-roll-live-{stage}.json');require(sha256(report)==sha256(published),'Published Trans parent changed');parents[stage]=sha256(report);d=json.loads(report.read_text());old={r['case']:r for r in d['cases']};cases=trans.recipe(stage);original='rmx-isolate-modes-discovery-20261029' if stage=='discovery' else f'rmx-trans-{stage}-v1-20261029';args=SimpleNamespace(stage=stage,session=a.original_root/original,host=a.host)
  for c in cases:
   _,provenance=modes.original(args,c,expected_source=trans.source(stage)[c['source']]);row=old[c['name']];require(row['passed'] and all(row[k]==v for k,v in provenance.items()),'Trans parent provenance changed');candidate=report.parent/(c['name']+'.wav');require(sha256(candidate)==row['candidate_sha256'],'Parent audio changed');plan=root/(c['name']+'.tsv');plan.write_text(modes.schedule(c));require(sha256(plan)==row['schedule_sha256'],'Parent schedule changed');out=plan.with_suffix('.wav');run([a.renderer,args.session/(c['source']+'.wav'),out,plan]);require(sha256(out)==row['candidate_sha256'],'Trans audio changed: '+c['name']);rows.append(provenance|dict(passed=True,candidate_sha256=sha256(out),whole_wav_parent_byte_identity=True));print('UNCHANGED',c['name'],flush=True)
 require(len(rows)==146 and binding==trans.bindings() and binary==sha256(a.renderer) and script==sha256(Path(__file__)),'Coverage/source changed');save_json(root/'verification.json',dict(kind='rmx220-cutadd-prior-transroll-byte-compatibility',passed=True,programs=146,cases=rows,source_sha256=binding,verifier_sha256=script,renderer_sha256=binary,parent_reports_sha256=parents,scope='All146 prior Trans/Roll programs; current native complete WAV bytes equal qualified live parent, original provenance rechecked. No new capture, wrapper or sanitizer qualification.'))
if __name__=='__main__':main()
