"""Per-run materialized inputs and host/native equality; never trust unchanged alone."""
import hashlib,json,shutil
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def file_hashes(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def prepare(source,destination):
 assert not destination.exists();shutil.copytree(source,destination,symlinks=False)
 hashes=file_hashes(destination);assert hashes and not any(p.is_symlink() for p in destination.rglob('*'))
 return {'files':hashes,'tree_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}
def check_tree(root,manifest):
 assert file_hashes(root)==manifest['files'],'Input bundle differs from host-captured bytes'
 assert hashlib.sha256(json.dumps(manifest['files'],sort_keys=True).encode()).hexdigest()==manifest['tree_sha256']
def check_recorded(process,expected):
 assert process['status']=='passed'
 assert process['input_sha256']==expected,'Native recorded inputs differ from expected host hashes'
 assert process['inputs_unchanged']=={p:True for p in expected}
