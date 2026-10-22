#!/usr/bin/env python3
"""Prepare pinned SDK archives and an optional local macOS Arm compiler.

Downloads are optional; --archives accepts .tar or .tar.gz files obtained with
a browser. Only .tools is modified. Package installer scripts are never run.
"""
import argparse
import gzip
import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'firmware/daisy/dependencies.lock.json').read_text())


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(block)
    return result.hexdigest()


def extract_source(archive, item, destination):
    opener = gzip.open if archive.name.endswith('.gz') else open
    with opener(archive, 'rb') as stream:
        if digest(stream) != item['tar_sha256']:
            raise ValueError('Archive checksum mismatch: ' + archive.name)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            parts = PurePosixPath(member.name).parts
            if (not parts or parts[0] != item['archive_root'] or '..' in parts
                    or PurePosixPath(member.name).is_absolute()
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe archive entry: ' + member.name)
            member.name = str(PurePosixPath(*parts[1:])) if len(parts) > 1 else '.'
            # An existing symlink in a cache must not redirect extraction.
            path = destination / member.name
            if not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Extraction escapes destination: ' + str(path))
        destination.mkdir(parents=True, exist_ok=True)
        source.extractall(destination, members)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, default=ROOT / '.cache/firmware')
    parser.add_argument('--download', action='store_true', help='Download missing source archives')
    parser.add_argument('--compiler-package', type=Path, help='Official macOS Arm 14.3.Rel1 .pkg')
    parser.add_argument('--gcc-bin', type=Path, help='Use an existing Arm 14.3.Rel1 compiler bin directory')
    args = parser.parse_args()
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    sdk = tools / LOCK['sdk_directory']
    for item in LOCK['sources']:
        candidates = [args.archives / (item['archive_root'] + suffix) for suffix in ('.tar.gz', '.tar')]
        archive = next((p for p in candidates if p.is_file()), None)
        if archive is None:
            if not args.download:
                raise FileNotFoundError('Missing archive for ' + item['name'] + ': ' + item['url'])
            args.archives.mkdir(parents=True, exist_ok=True)
            archive = candidates[0]
            temporary = archive.with_suffix(archive.suffix + '.partial')
            urllib.request.urlretrieve(item['url'], temporary)
            temporary.replace(archive)
        extract_source(archive, item, sdk / item['path'])
        print('Verified and extracted ' + item['name'] + ' ' + item['revision'])
    gcc = args.gcc_bin
    if args.compiler_package:
        if platform.system() != 'Darwin':
            raise ValueError('--compiler-package is for the pinned macOS package; use --gcc-bin elsewhere')
        with args.compiler_package.open('rb') as stream:
            if digest(stream) != LOCK['compiler']['sha256']:
                raise ValueError('Compiler package checksum mismatch')
        compiler = tools / 'arm-gnu-14.3'
        with tempfile.TemporaryDirectory(dir=tools, prefix='arm-unpack-') as temp:
            expanded = Path(temp) / 'expanded'
            subprocess.run(['pkgutil', '--expand-full', str(args.compiler_package), str(expanded)], check=True)
            if compiler.exists():
                shutil.rmtree(compiler)
            expanded.rename(compiler)
        gcc = compiler / 'Payload/bin'
    if gcc is None:
        gcc = tools / 'arm-gnu-14.3/Payload/bin'
    gcc = gcc.resolve()
    version = subprocess.check_output([str(gcc / 'arm-none-eabi-g++'), '--version'], text=True).splitlines()[0]
    if LOCK['compiler']['release'] not in version:
        raise ValueError('Expected pinned Arm compiler ' + LOCK['compiler']['release'] + ', got ' + version)
    # Generated paths are local only; the SDK and compiler are not installed globally.
    def make_path(path):
        return str(path).replace('$', '$$').replace('#', '\\#').replace(' ', '\\ ')
    (tools / 'firmware-env.mk').write_text('LIBDAISY_DIR := ' + make_path(sdk) + '\nGCC_PATH := ' + make_path(gcc) + '\n')
    print(version)
    print('Ready: make -C ' + str(sdk) + ' GCC_PATH=' + str(gcc) + ' -j4')
    print('Then: make -C firmware/daisy -j4')


if __name__ == '__main__':
    main()
