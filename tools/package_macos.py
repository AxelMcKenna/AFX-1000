#!/usr/bin/env python3
"""Package already-built universal Mac previews and their project source snapshot."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ('include', 'src', 'tools', 'tests', 'docs', 'assets', 'Sources', 'web', 'hardware', 'firmware', '.github')
EXCLUDED_PARTS = {'build', '__pycache__', '.git', '.DS_Store'}
SOURCE_SUFFIXES = {'.md', '.h', '.hpp', '.c', '.cpp', '.mm', '.swift', '.py', '.sh', '.json', '.svg', '.png', '.rmx', '.csv', '.scad', '.dxf', '.js', '.html', '.css', '.yml', '.yaml', '.plist', '.txt', '.lock'}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()

def cache(build: Path) -> dict[str, str]:
    values = {}
    for line in (build / 'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#', '//')) and '=' in line:
            key, value = line.split('=', 1)
            values[key.split(':', 1)[0]] = value
    return values

def source_files() -> list[Path]:
    paths = []
    for name in ('CMakeLists.txt', 'Package.swift', 'build-app.sh', '.gitignore', '.python-version', 'pyproject.toml', 'uv.lock', 'README.md', 'Info.plist', 'THIRD_PARTY_NOTICES.md', 'LICENSE'):
        if (ROOT / name).is_file(): paths.append(ROOT / name)
    for directory in SOURCE_DIRS:
        if not (ROOT / directory).exists(): continue
        for path in (ROOT / directory).rglob('*'):
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_PARTS for part in relative.parts): continue
            if path.is_file() and not path.is_symlink() and (path.suffix in SOURCE_SUFFIXES or path.name in ('Makefile', 'LICENSE', 'LICENSE.md', 'LICENSE.txt')):
                paths.append(path)
    return sorted(set(paths))

def source_zip(destination: Path, files: list[Path], notices: bytes) -> dict[str, str]:
    hashes = {}
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo('RMX-source/' + relative, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if os.access(path, os.X_OK) else 0o100644) << 16
            archive.writestr(info, data)
        generated = {'package-notices.txt': notices}
        hashes['package-notices.txt'] = hashlib.sha256(notices).hexdigest()
        generated['source-manifest.json'] = (json.dumps(hashes, indent=2, sort_keys=True) + '\n').encode()
        for name, data in generated.items():
            info = zipfile.ZipInfo('RMX-source/' + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return hashes

def dependency_zip(destination: Path, dependencies: dict[str, Path], license_folder: Path) -> dict:
    manifests = {}
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(dependencies.items()):
            hashes = {}
            for path in sorted(source.rglob('*')):
                relative = path.relative_to(source)
                if any(part in EXCLUDED_PARTS or part.startswith('build-') for part in relative.parts): continue
                if not path.is_file() or path.is_symlink(): continue
                data = path.read_bytes()
                hashes[relative.as_posix()] = hashlib.sha256(data).hexdigest()
                info = zipfile.ZipInfo(name + '/' + relative.as_posix(), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if os.access(path, os.X_OK) else 0o100644) << 16
                archive.writestr(info, data)
                lower = path.name.lower()
                if lower.startswith(('license', 'licence', 'copying', 'notice')) or lower.endswith(('licence.txt', 'license.txt')):
                    target = license_folder / name / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            manifests[name] = hashes
        info = zipfile.ZipInfo('dependency-manifest.json', (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, json.dumps(manifests, indent=2, sort_keys=True) + '\n')
    return manifests

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'build-universal')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/packages')
    parser.add_argument('--sign-identity', default='-', help='Apple signing identity, or - for an ad-hoc local preview')
    parser.add_argument('--source-revision', default=None, help='Optional revision for a source snapshot with external Git metadata')
    args = parser.parse_args()
    if sys.platform != 'darwin': parser.error('Mac bundle packaging requires macOS, lipo, codesign and ditto')
    build = args.build_dir.resolve()
    output = args.output_dir.resolve()
    values = cache(build)
    if values.get('CMAKE_BUILD_TYPE') != 'Release': parser.error('Use a Release build')
    if not args.sign_identity or any(char in args.sign_identity for char in '\r\n\0'): parser.error('Unsupported signing identity')
    artifacts = [('native', build / 'RMX.app', 'Contents/MacOS/RMX')]
    if values.get('RMX_BUILD_PLUGINS') == 'ON':
        base = build / 'RMXPlugin_artefacts/Release'
        artifacts += [('AU', base / 'AU/RMX.component', 'Contents/MacOS/RMX'), ('VST3', base / 'VST3/RMX.vst3', 'Contents/MacOS/RMX')]
    # Validate all inputs before creating or signing copies. Source products stay untouched.
    architectures = {}
    for kind, bundle, executable in artifacts:
        if not bundle.is_dir(): parser.error(f'Missing artifact: {bundle}')
        slices = run('lipo', '-archs', str(bundle / executable)).split()
        if not {'arm64', 'x86_64'}.issubset(slices): parser.error(f'{kind} is not universal: {slices}')
        architectures[kind] = slices
    dependencies = {}
    if len(artifacts) > 1:
        candidates = [Path(values['RMX_JUCE_PATH'])] if values.get('RMX_JUCE_PATH') else [build / '_deps/juce-src']
        juce = next((path for path in candidates if (path / 'LICENSE.md').is_file()), None)
        if juce is None: parser.error('Plugin packages need the configured JUCE source tree and its notices')
        version = re.search(r'project\(JUCE\s+VERSION\s+([0-9.]+)', (juce / 'CMakeLists.txt').read_text())
        if not version or version.group(1) != '8.0.6': parser.error('Expected the configured JUCE 8.0.6 source tree')
        dependencies['JUCE-8.0.6'] = juce
    if values.get('RMX_ENABLE_LINK') == 'ON':
        link = Path(values.get('RMX_LINK_PATH', ''))
        if not (link / 'LICENSE.md').is_file(): parser.error('Link packages need the configured SDK source and notices')
        dependencies['Ableton-Link-3.1.5'] = link
    if output.exists(): parser.error('Output directory already exists; select a fresh --output-dir')
    output.parent.mkdir(parents=True, exist_ok=True)
    names = ['RMX-macOS-universal.zip', 'RMX-source.zip', 'manifest.json', 'SHA256SUMS']
    if len(artifacts) > 1: names.append('RMX-Plugins-universal.zip')
    if dependencies: names.append('RMX-dependencies.zip')
    files = source_files()
    notice = (ROOT / 'THIRD_PARTY_NOTICES.md').read_bytes()
    revision = args.source_revision
    if revision is None:
        try: revision = run('git', '-C', str(ROOT), 'rev-parse', 'HEAD')
        except subprocess.CalledProcessError: revision = None
    with tempfile.TemporaryDirectory(prefix='rmx-package-', dir=output.parent) as temporary:
        stage = Path(temporary)
        app_stage = stage / 'RMX-macOS'
        plugin_stage = stage / 'RMX-Plugins'
        dependency_hashes = dependency_zip(stage / 'RMX-dependencies.zip', dependencies, plugin_stage / 'Licenses') if dependencies else {}
        for group in (app_stage, plugin_stage):
            group.mkdir(exist_ok=True)
            (group / 'THIRD_PARTY_NOTICES.md').write_bytes(notice)
            for name in ('LICENSE',):
                if (ROOT / name).exists(): shutil.copy2(ROOT / name, group / name)
            (group / 'README.txt').write_text('RMX development preview\n\nAd-hoc builds are not notarized. Native audio setup: Cmd+,.\nAU/VST3 are DAW plugins; rekordbox uses native app audio capture.\nSee the included dependency notices and project source snapshot.\nA source license does not replace dependency licensing requirements.\n')
        for kind, bundle, executable in artifacts:
            parent = app_stage if kind == 'native' else plugin_stage
            target = parent / bundle.name
            shutil.copytree(bundle, target, symlinks=True)
            signing = ['codesign', '--force', '--deep', '--sign', args.sign_identity]
            if args.sign_identity != '-': signing += ['--options', 'runtime', '--timestamp']
            run(*signing, str(target))
            run('codesign', '--verify', '--deep', '--strict', str(target))
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app_stage), str(stage / names[0]))
        if len(artifacts) > 1:
            run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(plugin_stage), str(stage / 'RMX-Plugins-universal.zip'))
        hashes = source_zip(stage / 'RMX-source.zip', files, notice)
        manifest = {
            'schema': 1, 'status': 'development-preview', 'version': '0.1.0',
            'source_revision': revision,
            'architectures': architectures, 'signing': 'ad-hoc' if args.sign_identity == '-' else 'developer-identity',
            'notarized': False, 'project_license_selected': (ROOT / 'LICENSE').is_file(),
            'source_sha256': hashes,
            'dependency_source_files': {name: len(hashes) for name, hashes in dependency_hashes.items()},
            'build': {key: values.get(key) for key in ('CMAKE_BUILD_TYPE', 'CMAKE_OSX_DEPLOYMENT_TARGET', 'RMX_BUILD_PLUGINS', 'RMX_ENABLE_LINK')},
            'packages': {name: digest(stage / name) for name in names if name.endswith('.zip')},
        }
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        checksum_names = sorted(name for name in names if name != 'SHA256SUMS')
        (stage / 'SHA256SUMS').write_text(''.join(f'{digest(stage / name)}  {name}\n' for name in checksum_names))
        ready = stage / 'ready'
        ready.mkdir()
        for name in names: shutil.move(str(stage / name), ready / name)
        # Publish the whole set at once; failed preparation leaves no output set.
        os.rename(ready, output)
    print(output)
    return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print(getattr(error, 'stderr', '') or str(error), file=sys.stderr)
        raise SystemExit(1)
