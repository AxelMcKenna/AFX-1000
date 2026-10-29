#!/usr/bin/env python3
"""Inspect a real ARM ELF, validate memory placement and record build provenance."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGIONS = {
    'FLASH': (0x08000000, 128 * 1024),
    'DTCMRAM': (0x20000000, 128 * 1024),
    'SRAM': (0x24000000, 512 * 1024),
    'RAM_D2_DMA': (0x30000000, 32 * 1024),
    'RAM_D2': (0x30008000, 256 * 1024),
    'RAM_D3': (0x38000000, 64 * 1024),
    'BACKUP_SRAM': (0x38800000, 4 * 1024),
    'ITCMRAM': (0, 64 * 1024),
    'SDRAM': (0xc0000000, 64 * 1024 * 1024),
    'QSPIFLASH': (0x90040000, 7936 * 1024),
}


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def translation_unit(source, build, working, elf, makefiles):
    """Reject stale C++ objects before treating an ELF as current evidence."""
    obj = build / (source.stem + '.o')
    dep = obj.with_suffix('.d')
    if not obj.is_file() or not dep.is_file():
        raise ValueError('Missing object/header dependency file for ' + str(source))
    # GCC writes one continued prerequisite line, followed by -MP phony rules.
    rules = dep.read_text().replace('\\\n', ' ').splitlines()
    if not rules:
        raise ValueError('Empty dependency file for ' + str(source))
    rule = rules[0]
    target, separator, prerequisites = rule.partition(':')
    targets = shlex.split(target)
    if not separator or len(targets) != 1 or Path(targets[0]).name != obj.name:
        raise ValueError('Unexpected dependency target for ' + str(source))
    dependencies = {(working / path).resolve() for path in shlex.split(prerequisites)}
    if source.resolve() not in dependencies:
        raise ValueError('Dependency file omits its source: ' + str(source))
    dependencies.update(path.resolve() for path in makefiles)
    newest = obj.stat().st_mtime_ns
    fingerprint = hashlib.sha256()
    for path in sorted(dependencies):
        if not path.is_file() or path.stat().st_mtime_ns > newest:
            raise ValueError('Stale object ' + str(obj) + ': changed/missing ' + str(path))
        # Record contents as well as checking mtimes; --check catches later edits
        # even when an external tool restores an input's timestamp.
        fingerprint.update((os.path.relpath(path, working) + ':' + sha(path) + '\n').encode())
    if newest > elf.stat().st_mtime_ns:
        raise ValueError('ELF has not linked current object: ' + str(obj))
    return {'object_sha256': sha(obj), 'dependencies_sha256': fingerprint.hexdigest(), 'dependency_count': len(dependencies)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcc-bin', type=Path, default=ROOT / '.tools/arm-gnu-14.3/Payload/bin')
    parser.add_argument('--elf', type=Path, default=ROOT / 'firmware/daisy/build/rmx_seed.elf')
    parser.add_argument('--sdk', type=Path, default=ROOT / '.tools/libDaisy-8.1.0')
    parser.add_argument('--record', type=Path, default=ROOT / 'firmware/daisy/build-record.json')
    parser.add_argument('--check', action='store_true', help='Check existing record against current sources and artifact')
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'tools/generate_hardware.py'), '--check'], check=True)
    def tool(name, *arguments):
        return subprocess.check_output([str(args.gcc_bin / ('arm-none-eabi-' + name)), *map(str, arguments)], text=True)
    header = tool('readelf', '-h', args.elf)
    stack_match = re.search(r'^([0-9a-f]+) A _estack$', tool('nm', '-n', args.elf), re.M)
    if not stack_match or int(stack_match[1], 16) != 0x20020000:
        raise ValueError('Unexpected initial stack pointer')
    storage = {name: {'address': hex(int(address, 16)), 'bytes': int(size, 16)} for address, size, name in
               re.findall(r'^([0-9a-f]+) ([0-9a-f]+) [bB] \(anonymous namespace\)::(audioMemory|engineStorage|bankStorage|card)$', tool('nm', '-S', '-C', args.elf), re.M)}
    if len(storage) != 4 or storage['audioMemory'] != {'address': '0xc0000000', 'bytes': 60 * 1024 * 1024}:
        raise ValueError('Required static engine/bank/external arena symbols missing or misplaced')
    card_address = int(storage['card']['address'], 16)
    if card_address % 32 or not 0x24000000 <= card_address < card_address + storage['card']['bytes'] <= 0x24080000:
        raise ValueError('Card/FatFS DMA storage is not aligned in AXI SRAM')
    attributes = tool('readelf', '-A', args.elf)
    if not all(value in header for value in ('ELF32', 'Machine:                           ARM', 'hard-float ABI')):
        raise ValueError('Expected a 32-bit ARM hard-float ELF')
    if 'Tag_CPU_arch: v7E-M' not in attributes or 'Tag_ABI_VFP_args: VFP registers' not in attributes:
        raise ValueError('Unexpected CPU/FPU calling convention')
    sections = []
    pattern = re.compile(r'^\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([A-Z]+)\s', re.M)
    usage = {name: 0 for name in REGIONS}
    for name, address, size, flags in pattern.findall(tool('readelf', '-SW', args.elf)):
        if 'A' not in flags or int(size, 16) == 0:
            continue
        address, size = int(address, 16), int(size, 16)
        region = next((key for key, (base, capacity) in REGIONS.items() if base <= address and address + size <= base + capacity), None)
        if region is None:
            raise ValueError('Allocated section outside known memory: ' + name)
        base = REGIONS[region][0]
        usage[region] = max(usage[region], address + size - base)
        sections.append({'name': name, 'address': hex(address), 'bytes': size, 'region': region})
    vector = next(section for section in sections if section['name'] == '.isr_vector')
    sdram = next(section for section in sections if section['name'] == '.sdram_bss')
    if vector['address'] != '0x90040000' or sdram['address'] != '0xc0000000' or sdram['bytes'] != 60 * 1024 * 1024:
        raise ValueError('Unexpected boot vector or external audio arena placement')
    binary = args.elf.with_suffix('.bin')
    usage['QSPIFLASH'] = max(usage['QSPIFLASH'], binary.stat().st_size)
    if usage['QSPIFLASH'] > REGIONS['QSPIFLASH'][1]:
        raise ValueError('QSPI image exceeds application region')
    cpp_sources = [ROOT / ('src/core/' + file) for file in ('Spiral.cpp', 'CutAdd.cpp', 'TransRoll.cpp', 'GateDrive.cpp', 'FactoryRelease.cpp', 'Engine.cpp', 'Isolator.cpp', 'Scene.cpp', 'CardSamples.cpp', 'CardSettings.cpp', 'ReverbDown.cpp', 'ReverbUp.cpp')]
    cpp_sources += sorted((ROOT / 'src/core/drums').glob('*.cpp'))
    cpp_sources += sorted((ROOT / 'firmware/daisy').glob('*.cpp'))
    makefiles = [ROOT / 'firmware/daisy/Makefile', args.sdk / 'core/Makefile']
    units = {str(source.relative_to(ROOT)): translation_unit(source, args.elf.parent, ROOT / 'firmware/daisy', args.elf, makefiles) for source in cpp_sources}
    source_paths = sorted((ROOT / 'include/rmx').rglob('*.h')) + cpp_sources
    source_paths += list((ROOT / 'firmware/daisy').glob('*.h'))
    source_paths += [ROOT / 'firmware/daisy/Makefile',
                     ROOT / 'firmware/daisy/dependencies.lock.json', ROOT / 'hardware/generated/BoardConfig.h']
    source_paths += [ROOT / 'hardware/prototype.json']
    inputs = {str(path.relative_to(ROOT)): sha(path) for path in source_paths}
    artifacts = {path.name: sha(path) for path in (args.elf, binary, args.elf.with_suffix('.map'))}
    sdk_source = hashlib.sha256()
    for path in sorted(args.sdk.rglob('*')):
        if path.is_file() and 'build' not in path.relative_to(args.sdk).parts and (path.suffix.lower() in ('.c', '.cpp', '.h', '.hpp', '.s', '.mk', '.lds') or path.name == 'Makefile'):
            sdk_source.update((str(path.relative_to(args.sdk)) + ':' + sha(path) + '\n').encode())
    sdk_hashes = {'sources': sdk_source.hexdigest(), 'library': sha(args.sdk / 'build/libdaisy.a')}
    regions = {key: {'origin': hex(base), 'capacity_bytes': capacity, 'used_bytes': usage[key]} for key, (base, capacity) in REGIONS.items()}
    if args.check:
        record = json.loads(args.record.read_text())
        if record['source_sha256'] != inputs or record['artifact_sha256'] != artifacts or record['sdk_sha256'] != sdk_hashes:
            raise ValueError('Build record is stale: sources or linked artifacts changed')
        if record.get('translation_units') != units:
            raise ValueError('Build record translation units differ from current objects/dependencies')
        if record['memory_regions'] != regions or record['static_storage'] != storage or record['allocated_sections'] != sections:
            raise ValueError('Build record memory values differ from the actual ELF')
        print('PASS: recorded ARM artifacts match current source hashes and memory placement')
        return
    record = {
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'Cross-compiled and linked; not flashed or runtime-qualified',
        'compiler': tool('g++', '--version').splitlines()[0],
        'sdk_revision': json.loads((ROOT / 'firmware/daisy/dependencies.lock.json').read_text())['sources'][0]['revision'],
        'source_sha256': inputs, 'artifact_sha256': artifacts,
        'translation_units': units,
        'sdk_sha256': sdk_hashes,
        'memory_regions': regions,
        'allocated_sections': sections,
        'static_storage': storage,
        'stack': {'initial_pointer': '0x20020000', 'available_dtcm_bytes': 128 * 1024 - usage['DTCMRAM'], 'high_water_measured': False},
        'limitations': ['No board execution, callback deadline, stack high-water or physical audio measurements',
                        'Upstream startup FP-register warning, nosys syscall stubs and RWX ELF segment warning remain'],
    }
    args.record.write_text(json.dumps(record, indent=2) + '\n')
    for key, value in usage.items():
        if value:
            print(key + ': ' + str(value) + ' / ' + str(REGIONS[key][1]) + ' bytes')
    print('PASS: ARM memory placement; record written to ' + str(args.record))


if __name__ == '__main__':
    main()
