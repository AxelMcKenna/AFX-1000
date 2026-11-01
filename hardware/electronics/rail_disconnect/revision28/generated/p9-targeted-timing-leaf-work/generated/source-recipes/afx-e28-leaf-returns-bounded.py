from pathlib import Path
import subprocess,json,hashlib,time
repo=Path.cwd();root=repo/'hardware/electronics/rail_disconnect/revision28/generated';dest=root/'p9-targeted-timing-leaf-work/generated'
for label,workspace,fill in [('before-five','p9-pruned-leaf-reviewed-work','pruned-leaf1'),('after-five','p9-targeted-timing-leaf-work','targeted-timing1')]:
 board=root/workspace/f'generated/filled-{fill}.kicad_pcb';pads=root/workspace/'generated/native-pads.json';output=dest/f'return-{label}.json';log=dest/f'return-{label}.log'
 command=[str(repo/'.venv/bin/python'),'-m','hardware.electronics.rail_disconnect.revision28.coupled',str(board),'--returns','--steps','.15,.1','--stud-contact-radius','3.5','--load-contact-layer','F.Cu','--native-pad-geometry',str(pads),'--distributed-barrels','--output',str(output)]
 receipt=dict(command=command,source_filled_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),native_pads_sha256=hashlib.sha256(pads.read_bytes()).hexdigest(),timeout_seconds=600,started_time_ns=time.time_ns(),physical_qualified=False)
 target=dest/f'return-{label}-command.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 try:
  with log.open('w') as handle:p=subprocess.run(command,stdout=handle,stderr=subprocess.STDOUT,timeout=600)
  receipt['returncode']=p.returncode
 except subprocess.TimeoutExpired:receipt['timed_out_after_seconds']=600
 receipt['finished_time_ns']=time.time_ns();receipt['log_sha256']=hashlib.sha256(log.read_bytes()).hexdigest();receipt['completed_rows_retained']=output.exists();target.write_text(json.dumps(receipt,indent=2)+'\n');print(label,receipt.get('returncode'),receipt.get('timed_out_after_seconds'),flush=True)
