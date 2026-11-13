import json,tempfile,unittest
from pathlib import Path
from .verify_plane import library_link
from ..routed.plan import sha
class LibraryBindingTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.target=self.root/'source';self.target.mkdir();(self.target/'a.kicad_mod').write_text('immutable');self.link=self.root/'candidate';self.link.mkdir();self.link=self.link/'libraries';self.link.symlink_to('../source',target_is_directory=True);self.binding={'relative_link':'../source','files_sha256':{'a.kicad_mod':sha(self.target/'a.kicad_mod')}}
 def test_matching_internal_source(self):self.assertEqual(library_link(self.link,self.binding,self.root,self.target),1)
 def test_modified_library_rejected(self):
  (self.target/'a.kicad_mod').write_text('changed')
  with self.assertRaises(AssertionError):library_link(self.link,self.binding,self.root,self.target)
 def test_missing_target_rejected(self):
  self.link.unlink();self.link.symlink_to('../missing');self.binding['relative_link']='../missing'
  with self.assertRaises(FileNotFoundError):library_link(self.link,self.binding,self.root,self.target)
 def test_escaped_target_rejected(self):
  outside=tempfile.TemporaryDirectory();self.addCleanup(outside.cleanup);self.link.unlink();self.link.symlink_to(outside.name);self.binding['relative_link']=outside.name
  with self.assertRaises(AssertionError):library_link(self.link,self.binding,self.root,self.target)
if __name__=='__main__':unittest.main()
