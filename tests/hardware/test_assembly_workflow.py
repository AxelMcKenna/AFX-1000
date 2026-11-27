"""Fail-closed and incremental behavior of the shared CAD workflow."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.cad.assembly_workflow import workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.patchers = [patch.object(w, 'ROOT', self.root), patch.object(w, 'HERE', self.root), patch.object(w, 'CACHE', self.root / 'cache')]
        for patcher in self.patchers:
            patcher.start()
        for path in ['hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py',
                     'hardware/cad/a12/thermal/enlarged_base/verify.py']:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# test runtime\n')
        # The engine hash is a real module outside this test root; use a stable relative alias.
        self.relative = patch.object(w, 'relative', side_effect=lambda p: str(p.relative_to(self.root)) if p.is_relative_to(self.root) else 'engine.py')
        self.relative.start()
        (self.root / 'engine.py').write_bytes(Path(w.__file__).read_bytes())
        (self.root / 'current.json').write_text('{}')
        (self.root / 'a.scad').write_text('use <nested.scad>\nmodule a(){cube(1);}')
        (self.root / 'nested.scad').write_text('module n(){cube(2);}')
        (self.root / 'b.scad').write_text('module b(){cube(1);}')
        self.parts = {i:dict(id=i,source=i+'.scad',module=i,role='installed',description='test') for i in ['a','b']}
        self.check = dict(id='a_b',left=['a'],right=['b'],expect='empty')

    def tearDown(self):
        self.relative.stop()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def candidate_manifest(self):
        registry = self.root / 'registry.json'
        registry.write_text(json.dumps({'components': list(self.parts.values())}))
        candidate = self.root / 'candidate.json'
        candidate.write_text(json.dumps({'schema_version': 1, 'registries': ['registry.json'],
                                         'checks': [self.check], 'unresolved': []}))
        return candidate

    def test_candidate_scene_uses_candidate_without_changing_selection(self):
        candidate = self.candidate_manifest()
        selected = (self.root / 'current.json').read_bytes()
        output = self.root / 'candidate-view.scad'
        state = {'geometry_fresh': True, 'source_sha256': {}}
        with patch.object(w, 'board_state', return_value=state), patch.object(w.sys, 'argv',
                ['workflow', 'scene', '--manifest', str(candidate), '--output', str(output)]):
            w.main()
        self.assertIn('a();', output.read_text())
        self.assertEqual(selected, (self.root / 'current.json').read_bytes())
        self.assertFalse((self.root / 'generated/assembly.scad').exists())

    def test_candidate_scene_requires_separate_output(self):
        with patch.object(w, 'board_state') as board, patch.object(w.sys, 'argv',
                ['workflow', 'scene', '--manifest', str(self.candidate_manifest())]):
            with self.assertRaises(SystemExit):
                w.main()
            board.assert_not_called()

    def test_candidate_outside_worktree_rejected_before_loading(self):
        with patch.object(w, 'load_manifest') as load, patch.object(w.sys, 'argv',
                ['workflow', 'status', '--manifest', str(self.root.parent / 'foreign.json')]):
            with self.assertRaises(ValueError):
                w.main()
            load.assert_not_called()

    def test_existing_evidence_rejected_before_native_work(self):
        candidate = self.candidate_manifest()
        output = self.root / 'evidence.json'
        output.write_text('preserve me')
        with patch.object(w, 'board_state') as board, patch.object(w, 'execute') as execute, patch.object(w.sys, 'argv',
                ['workflow', 'check', '--manifest', str(candidate), '--output', str(output)]):
            with self.assertRaises(SystemExit):
                w.main()
            board.assert_not_called()
            execute.assert_not_called()
        self.assertEqual(output.read_text(), 'preserve me')

    def test_selected_capture_change_invalidates_board_cache(self):
        from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness
        for name in ['capture-a.json','capture-b.json']:(self.root/name).write_text('{}')
        boards={'signal':'s.kicad_pcb','power':'p.kicad_pcb'}
        old={'selected_pcbs':boards,'mechanical_capture':'capture-a.json','source_sha256':{'capture-a.json':w.sha(self.root/'capture-a.json')},'freshness_key':'old'}
        folder=self.root/'cache/boards';folder.mkdir(parents=True)
        (folder/'latest.json').write_text(json.dumps(old))
        new={'selected_pcbs':boards,'mechanical_capture':'capture-b.json','source_sha256':{'capture-b.json':w.sha(self.root/'capture-b.json')},'freshness_key':'new'}
        with patch.object(pcb_freshness,'run',return_value=new) as run:
            self.assertEqual(w.board_state({'boards':boards,'mechanical_capture':'capture-b.json'}),new)
            run.assert_called_once_with(self.root,boards,'capture-b.json')
        with patch.object(pcb_freshness,'run',side_effect=AssertionError('unchanged capture should be cached')):
            self.assertEqual(w.board_state({'boards':boards,'mechanical_capture':'capture-b.json'}),new)

    def test_unrelated_bound_source_cannot_impersonate_selected_capture(self):
        from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness
        (self.root/'board.kicad_pcb').write_text('(kicad_pcb)')
        boards={'signal':'board.kicad_pcb','power':'p.kicad_pcb'}
        old={'mechanical_capture':'capture.json','selected_pcbs':boards,'source_sha256':{'board.kicad_pcb':w.sha(self.root/'board.kicad_pcb')},'freshness_key':'old'}
        folder=self.root/'cache/boards';folder.mkdir(parents=True)
        (folder/'latest.json').write_text(json.dumps(old))
        with patch.object(pcb_freshness,'run',side_effect=ValueError('invalid selected capture')) as run:
            with self.assertRaisesRegex(ValueError,'invalid selected capture'):
                w.board_state({'boards':boards,'mechanical_capture':'board.kicad_pcb'})
            run.assert_called_once()

    def test_dependency_change_invalidates_only_affected_component(self):
        a = w.job('component', self.parts['a'], self.parts)[1]
        b = w.job('component', self.parts['b'], self.parts)[1]
        check = w.job('check', self.check, self.parts)[1]
        (self.root/'nested.scad').write_text('module n(){cube(3);}')
        self.assertNotEqual(a, w.job('component', self.parts['a'], self.parts)[1])
        self.assertEqual(b, w.job('component', self.parts['b'], self.parts)[1])
        self.assertNotEqual(check, w.job('check', self.check, self.parts)[1])

    def test_descriptive_metadata_does_not_invalidate_geometry(self):
        before = w.job('check', self.check, self.parts)[1]
        self.parts['a']['description'] = 'Updated explanation only'
        self.assertEqual(before, w.job('check', self.check, self.parts)[1])

    def test_check_operand_change_invalidates_result(self):
        before = w.job('check', self.check, self.parts)[1]
        changed = dict(self.check, left=['b'], right=['a'])
        self.assertNotEqual(before, w.job('check', changed, self.parts)[1])

    def test_cache_corruption_is_rejected(self):
        identity, folder = w.job('check', self.check, self.parts)
        folder.mkdir(parents=True)
        log = folder/'native.log'; log.write_text('original')
        (folder/'result.json').write_text(json.dumps(dict(identity=identity,artifacts={'native.log':w.sha(log)},runtime_failure=False,passed=True)))
        self.assertTrue(w.cached(identity,folder)['passed'])
        log.write_text('changed')
        with self.assertRaisesRegex(AssertionError,'Corrupt'):
            w.cached(identity,folder)

    def test_incomplete_or_failed_jobs_are_not_automatically_retried(self):
        identity, folder = w.job('check', self.check, self.parts)
        folder.mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            w.cached(identity,folder)
        (folder/'result.json').write_text(json.dumps(dict(identity=identity,artifacts={},runtime_failure=True,passed=False)))
        with self.assertRaisesRegex(RuntimeError,'Failed'):
            w.cached(identity,folder)

    def test_missing_dependency_and_outside_source_are_rejected(self):
        (self.root/'nested.scad').unlink()
        with self.assertRaises(FileNotFoundError):
            w.job('component',self.parts['a'],self.parts)

    def test_empty_component_cannot_make_false_clearance_pass(self):
        class Result:
            returncode=1
            stdout='Current top level object is empty.'
            stderr=''
        with patch.object(w,'command',return_value=['docker','run','image']), patch.object(w.subprocess,'run',return_value=Result()):
            result, reused=w.execute('component',self.parts['a'],self.parts)
        self.assertFalse(result['passed'])
        self.assertFalse(result['runtime_failure'])
        self.assertFalse(reused)

    def seed_positive_operands(self):
        for component in self.parts.values():
            identity, folder = w.job('component', component, self.parts)
            folder.mkdir(parents=True)
            target = folder/'geometry.stl'; target.write_text('mock native mesh')
            (folder/'result.json').write_text(json.dumps(dict(identity=identity,artifacts={'geometry.stl':w.sha(target)},runtime_failure=False,passed=True,mesh={'closed_oriented_boundary':True})))

    def test_source_drift_during_native_run_is_rejected(self):
        self.seed_positive_operands()
        class Result:
            returncode=1
            stdout='Current top level object is empty.'
            stderr=''
        def mutate(*args,**kwargs):
            (self.root/'b.scad').write_text('module b(){cube(99);}')
            return Result()
        with patch.object(w,'command',return_value=['docker','run','image']), patch.object(w.subprocess,'run',side_effect=mutate):
            result,_=w.execute('check',self.check,self.parts)
        self.assertFalse(result['passed'])
        self.assertTrue(result['runtime_failure'])
        self.assertEqual(result['source_drift'],['b.scad'])


    def test_inter_job_source_change_cannot_turn_empty_operand_into_pass(self):
        def fake_execute(kind, definition, components, **kwargs):
            self.assertEqual(kind, 'component')
            if definition['id'] == 'b':
                (self.root/'a.scad').write_text('module a(){}')
            return {'passed':True}, False
        manifest = ({'unresolved':[],'_loaded_sources':{'current.json':w.sha(self.root/'current.json')}}, self.parts, {'a_b':self.check}, {})
        policy = self.root/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json'
        policy.parent.mkdir(parents=True)
        policy.write_text(json.dumps(dict(isolated_Linux_restart_authorized_by_user=True,allowed_isolated_image=w.IMAGE)))
        with patch.object(w, 'board_state', return_value={'geometry_fresh':True,'source_sha256':{}}), patch.object(w, 'load_manifest', return_value=manifest), patch.object(w, 'execute', side_effect=fake_execute), patch.object(w.sys, 'argv', ['workflow','check']):
            with self.assertRaisesRegex(RuntimeError, 'Source snapshot changed'):
                w.main()

    def test_native_launch_failure_is_terminal_and_recoverable(self):
        with patch.object(w,'command',return_value=['docker','run','image']), patch.object(w.subprocess,'run',side_effect=FileNotFoundError('docker missing')):
            result,_=w.execute('component',self.parts['a'],self.parts)
        self.assertTrue(result['runtime_failure'])
        identity,folder=w.job('component',self.parts['a'],self.parts)
        probe=type('Probe',(),{'returncode':1,'stdout':'','stderr':'No such container'})()
        with patch.object(w.subprocess,'run',return_value=probe):
            recovered=w.recover(str(folder.relative_to(w.CACHE)),'Docker path repaired; original launch failed before container start')
        self.assertFalse(folder.exists())
        self.assertFalse(recovered['automatically_retried'])
        self.assertTrue((self.root/recovered['archived']/'result.json').exists())

    def test_recovery_requires_explicit_container_absence_or_stopped_state(self):
        responses = [
            (1, '', 'error: no such object: owned', True),
            (1, '', 'Error response from daemon: No such container: owned', True),
            (1, '', 'No such container', True),
            (0, 'false\n', '', True),
            (0, 'true\n', '', False),
            (1, '', 'permission denied connecting to Docker', False),
            (1, '', 'Cannot connect to the Docker daemon', False),
            (1, '', 'No such image: owned', False),
            (1, '', 'unrelated diagnostic: no such object: owned', False),
        ]
        for incomplete in (False, True):
            for code, stdout, stderr, allowed in responses:
                with self.subTest(incomplete=incomplete, stderr=stderr, stdout=stdout):
                    _, folder = w.job('component', self.parts['a'], self.parts)
                    folder.mkdir(parents=True, exist_ok=True)
                    state = {'pid': 99999999, 'container': 'owned'} if incomplete else {
                        'runtime_failure': True, 'container': 'owned'}
                    evidence = folder / ('running.json' if incomplete else 'result.json')
                    evidence.write_text(json.dumps(state))
                    probe = type('Probe', (), dict(returncode=code, stdout=stdout, stderr=stderr))()
                    with patch.object(w.os, 'kill', side_effect=ProcessLookupError), patch.object(
                            w.subprocess, 'run', return_value=probe) as inspect:
                        if allowed:
                            result = w.recover(str(folder.relative_to(w.CACHE)), 'Explicit diagnosis')
                            self.assertFalse(result['automatically_retried'])
                            self.assertFalse(folder.exists())
                            self.assertTrue((self.root / result['archived'] / evidence.name).exists())
                        else:
                            with self.assertRaises(AssertionError):
                                w.recover(str(folder.relative_to(w.CACHE)), 'Must remain retained')
                            self.assertTrue(evidence.exists())
                            evidence.unlink()
                    self.assertEqual(inspect.call_count, 1)
                    self.assertEqual(inspect.call_args.args[0][1], 'inspect')

    def test_live_job_cannot_be_archived(self):
        _, folder=w.job('component',self.parts['a'],self.parts)
        folder.mkdir(parents=True)
        (folder/'running.json').write_text(json.dumps(dict(pid=w.os.getpid(),container='live-test')))
        with self.assertRaisesRegex(RuntimeError,'still live'):
            w.recover(str(folder.relative_to(w.CACHE)),'Not allowed while active')

    def test_changed_snapshot_rejected_before_native_launch(self):
        expected=w.job('component',self.parts['a'],self.parts)[0]
        (self.root/'a.scad').write_text('module a(){}')
        with patch.object(w.subprocess,'run') as native:
            with self.assertRaisesRegex(RuntimeError,'snapshot changed'):
                w.execute('component',self.parts['a'],self.parts,expected=expected)
            native.assert_not_called()



    def test_closed_contact_boundaries_are_distinguished_from_open_surfaces(self):
        points=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        faces=[(0,2,1),(0,1,3),(1,2,3),(2,0,3)]
        def write_faces(rows):
            target=self.root/'topology.stl'
            raw=b'0'*80+struct.pack('<I',len(rows))
            for face in rows:
                xyz=[v for i in face for v in points[i]]
                raw+=struct.pack('<12fH',0.,0.,0.,*xyz,0)
            target.write_bytes(raw)
            return w.boundary_balance(target)
        self.assertEqual(write_faces(faces),dict(balanced_oriented_boundary=True,maximum_edge_multiplicity=1))
        self.assertEqual(write_faces(faces+faces),dict(balanced_oriented_boundary=True,maximum_edge_multiplicity=2))
        self.assertFalse(write_faces(faces[:-1])['balanced_oriented_boundary'])

    def manifest_fixture(self):
        registry=self.root/'parts.json'
        registry.write_text(json.dumps(dict(components=list(self.parts.values()),source_sha256={'a.scad':w.sha(self.root/'a.scad')})))
        manifest=self.root/'current.json'
        manifest.write_text(json.dumps(dict(schema_version=1,registries=['parts.json'],checks=[self.check])))
        return manifest,registry

    def test_registry_source_drift_is_rejected(self):
        manifest,_=self.manifest_fixture()
        w.load_manifest(manifest)
        (self.root/'a.scad').write_text('module a(){cube(2);}')
        with self.assertRaisesRegex(AssertionError,'Registry source drift'):
            w.load_manifest(manifest)

    def test_duplicate_public_module_names_are_rejected(self):
        self.parts['b']['module']='a'
        manifest,_=self.manifest_fixture()
        with self.assertRaisesRegex(AssertionError,'Duplicate public module'):
            w.load_manifest(manifest)



    def test_manifest_or_board_change_invalidates_completed_batch(self):
        policy=self.root/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json'
        policy.parent.mkdir(parents=True)
        policy.write_text(json.dumps(dict(isolated_Linux_restart_authorized_by_user=True,allowed_isolated_image=w.IMAGE)))
        board=self.root/'board.kicad_pcb'; board.write_text('original board')
        for changed in [self.root/'current.json',board]:
            with self.subTest(path=changed.name):
                changed.write_text('initial')
                board_hash=w.sha(board)
                def mutate(kind,definition,components,**kwargs):
                    if kind=='check':changed.write_text('changed after source selection')
                    return {'passed':True,'runtime_failure':False},False
                manifest=({'unresolved':[],'_loaded_sources':{'current.json':w.sha(self.root/'current.json')}},self.parts,{'a_b':self.check},{})
                state={'geometry_fresh':True,'source_sha256':{'board.kicad_pcb':board_hash}}
                with patch.object(w,'board_state',return_value=state),patch.object(w,'load_manifest',return_value=manifest),patch.object(w,'execute',side_effect=mutate),patch.object(w.sys,'argv',['workflow','check']):
                    with self.assertRaisesRegex(RuntimeError,'Source snapshot changed'):
                        w.main()



    def test_manifest_changed_during_board_check_is_rejected(self):
        manifest,_=self.manifest_fixture()
        original_load=w.load_manifest
        def board_change(data):
            changed=json.loads(manifest.read_text())
            changed['checks'][0]['id']='new_required_check'
            manifest.write_text(json.dumps(changed))
            return {'geometry_fresh':True,'source_sha256':{}}
        with patch.object(w,'load_manifest',side_effect=lambda:original_load(manifest)),patch.object(w,'board_state',side_effect=board_change),patch.object(w.sys,'argv',['workflow','check']):
            with self.assertRaisesRegex(RuntimeError,'Source snapshot changed'):
                w.main()

    def allow_native_policy(self):
        policy = self.root/'hardware/validation/board-qualification/NATIVE-CAD-STOP.json'
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text(json.dumps(dict(isolated_Linux_restart_authorized_by_user=True, allowed_isolated_image=w.IMAGE)))

    def test_export_report_binds_components_artifacts_and_recursive_sources(self):
        candidate = self.candidate_manifest()
        self.allow_native_policy()
        self.seed_positive_operands()
        output = self.root/'exports.json'
        state = dict(geometry_fresh=True, source_sha256={}, freshness_key='board-key')
        with patch.object(w, 'board_state', return_value=state), patch.object(w.subprocess, 'run') as native, patch.object(w.sys, 'argv',
                ['workflow', 'export', '--manifest', str(candidate), '--only', 'a', '--output', str(output)]):
            w.main()
            native.assert_not_called()
        report = json.loads(output.read_text())
        row, = report['results']
        self.assertEqual(row['component'], 'a')
        self.assertTrue(row['passed'] and row['cached'])
        folder = self.root/row['cache']
        self.assertEqual(row['result_sha256'], w.sha(folder/'result.json'))
        self.assertEqual(row['artifacts']['geometry.stl'], w.sha(folder/'geometry.stl'))
        for name in ['a.scad', 'nested.scad', 'engine.py']:
            self.assertEqual(report['snapshot_sha256'][name], w.sha(self.root/name))
        self.assertEqual(report['board_freshness_key'], 'board-key')

    def test_report_created_during_native_work_is_not_overwritten(self):
        candidate = self.candidate_manifest()
        self.allow_native_policy()
        self.seed_positive_operands()
        output = self.root/'race.json'
        original_execute = w.execute
        def concurrent_report(*args, **kwargs):
            result = original_execute(*args, **kwargs)
            output.write_text('other owner evidence')
            return result
        state = dict(geometry_fresh=True, source_sha256={}, freshness_key='board-key')
        with patch.object(w, 'board_state', return_value=state), patch.object(w, 'execute', side_effect=concurrent_report), patch.object(w.sys, 'argv',
                ['workflow', 'export', '--manifest', str(candidate), '--only', 'a', '--output', str(output)]):
            with self.assertRaisesRegex(RuntimeError, 'Fresh evidence output required'):
                w.main()
        self.assertEqual(output.read_text(), 'other owner evidence')
        self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_two_publishers_cannot_clobber_fresh_evidence(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        target = self.root/'concurrent.json'
        barrier = Barrier(2)
        original_link = w.os.link
        def synchronize(source, destination):
            # Both publishers have finished writing their private JSON before
            # either attempts publication of the same originally absent path.
            json.loads(Path(source).read_text())
            barrier.wait(timeout=5)
            return original_link(source, destination)
        def publish(owner):
            try:
                w.publish_json(target, {'owner': owner, 'payload': 'x'*10000}, replace=False)
                return owner
            except FileExistsError:
                return None
        with patch.object(w.os, 'link', side_effect=synchronize), ThreadPoolExecutor(max_workers=2) as pool:
            winners = list(pool.map(publish, ['a', 'b']))
        winner, = [owner for owner in winners if owner is not None]
        self.assertEqual(json.loads(target.read_text())['owner'], winner)
        self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_atomic_cache_publication_keeps_old_json_until_complete(self):
        target = self.root/'latest.json'
        target.write_text(json.dumps({'old': True}))
        original_replace = Path.replace
        observations = []
        def observe(source, destination):
            observations.append((json.loads(target.read_text()), json.loads(source.read_text())))
            return original_replace(source, destination)
        with patch.object(Path, 'replace', observe):
            w.publish_json(target, {'new': True})
        self.assertEqual(observations, [({'old': True}, {'new': True})])
        self.assertEqual(json.loads(target.read_text()), {'new': True})
        self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_plan_observes_incomplete_and_runtime_failure_without_retry(self):
        identity, folder = w.job('check', self.check, self.parts)
        folder.mkdir(parents=True)
        w.publish_json(folder/'running.json', dict(identity=identity, pid=w.os.getpid()))
        with patch.object(w.subprocess, 'run') as native:
            self.assertEqual(w.plan(self.parts, {'a_b': self.check})[0]['state'], 'incomplete')
            native.assert_not_called()
        log = folder/'native.log'; log.write_text('preserved failure')
        w.publish_json(folder/'result.json', dict(identity=identity, artifacts={'native.log': w.sha(log)},
                                                runtime_failure=True, passed=False, returncode=137))
        with patch.object(w.subprocess, 'run') as native:
            self.assertEqual(w.plan(self.parts, {'a_b': self.check})[0]['state'], 'runtime_failed')
            native.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, 'Failed job preserved'):
            w.cached(identity, folder)
        log.write_text('corrupt')
        with self.assertRaisesRegex(AssertionError, 'Corrupt cached artifact'):
            w.plan(self.parts, {'a_b': self.check})

    def test_plan_does_not_read_transient_running_marker(self):
        _, folder = w.job('check', self.check, self.parts)
        folder.mkdir(parents=True)
        (folder/'running.json').write_text('not a completed result')
        original_read = Path.read_text
        def reject_running_read(path, *args, **kwargs):
            if path.name == 'running.json':
                raise FileNotFoundError('Publisher removed running marker')
            return original_read(path, *args, **kwargs)
        with patch.object(Path, 'read_text', reject_running_read):
            self.assertEqual(w.plan(self.parts, {'a_b': self.check})[0]['state'], 'incomplete')

    def test_source_snapshot_merge_rejects_conflicting_geometry(self):
        snapshot = {'a.scad': 'original'}
        w.merge_sources(snapshot, {'nested.scad': 'dependency', 'a.scad': 'original'})
        self.assertEqual(snapshot['nested.scad'], 'dependency')
        with self.assertRaisesRegex(RuntimeError, 'Conflicting source snapshots: a.scad'):
            w.merge_sources(snapshot, {'a.scad': 'changed'})
        self.assertEqual(snapshot['a.scad'], 'original')

    def test_native_returncode_is_preserved_in_failed_cache_result(self):
        proc = type('Proc', (), dict(returncode=137, stdout='', stderr='killed'))()
        with patch.object(w, 'command', return_value=['docker','run','image']), patch.object(w.subprocess, 'run', return_value=proc):
            result, _ = w.execute('component', self.parts['a'], self.parts)
        self.assertTrue(result['runtime_failure'])
        self.assertEqual(result['returncode'], 137)
        _, folder = w.job('component', self.parts['a'], self.parts)
        self.assertEqual(json.loads((folder/'result.json').read_text())['returncode'], 137)


if __name__=='__main__':
    unittest.main()
