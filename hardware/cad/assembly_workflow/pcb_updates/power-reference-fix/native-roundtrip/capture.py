"""Pinned Linux KiCad roundtrip of two frozen boards, without refill or edits."""
import gzip,hashlib,json,sys
from pathlib import Path
import pcbnew
assert sys.platform == 'linux'
inputs=Path('/inputs');out=Path('/output');rows={}
for name in ('before','after'):
    src=inputs/(name+'.kicad_pcb'); digest=hashlib.sha256(src.read_bytes()).hexdigest()
    board=pcbnew.LoadBoard(str(src)); assert board is not None
    target=Path('/tmp')/(name+'.kicad_pcb');pcbnew.SaveBoard(str(target),board)
    data=target.read_bytes();artifact=out/(name+'.kicad_pcb.gz')
    artifact.write_bytes(gzip.compress(data,mtime=0))
    assert hashlib.sha256(src.read_bytes()).hexdigest()==digest
    rows[name]={'input_sha256':digest,'saved_sha256':hashlib.sha256(data).hexdigest(),
                'gzip_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
                'footprints':len(list(board.GetFootprints()))}
(out/'capture.json').write_text(json.dumps({'native_version':pcbnew.GetBuildVersion(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'boards':rows,'refilled':False},indent=2)+'\n')
print('Captured both native roundtrips without refill')
