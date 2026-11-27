"""Replace duplicate immutable libraries with a verified worktree-relative binding."""
import json
from pathlib import Path
from ..routed.plan import sha
from .verify_plane import library_link
H=Path(__file__).resolve().parent

def package(out):
 out=Path(out).resolve();source=H.parent/'shared_cutover/native-04/libraries';binding={'relative_link':'../../shared_cutover/native-04/libraries','target_from_aux_root':'shared_cutover/native-04/libraries','files_sha256':{str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},'unchanged_from_native_run':True};target=out/'libraries'
 assert out.parent==H,'Output must be a held-cell candidate directory'
 if not target.is_symlink():
  actual={str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()};assert actual==binding['files_sha256'];backup=H/(out.name+'-library-copy-local');assert not backup.exists();target.rename(backup);target.symlink_to(binding['relative_link'],target_is_directory=True)
 library_link(target,binding,H.parents[3],source);(H/'library-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
if __name__=='__main__':package(H/'native-plane-04')
