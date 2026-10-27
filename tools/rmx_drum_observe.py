#!/usr/bin/env python3
"""Read named scalar constants from the locally acquired original; never writes DSP state."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess

from tools.reference_audio import save_json, sha256

BINARY_SHA256 = 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced'
NAMES = ['_g_adsr_'+s for s in ('kick_tri','kick_eg','kick_noi','snare_tri','snare_eg','snare_noi','clap_noi','clap_rvb','hihat_puls','hihat_puls_atk')]+['_g_coef_kick_lcf']


def observe(args):
    if sha256(args.binary) != BINARY_SHA256: raise ValueError('Requires the reviewed original 2.2.0 Intel binary')
    data = args.binary.read_bytes(); header = struct.unpack_from('<IiiIIIII',data)
    if header[0] != 0xfeedfacf or header[1] != 0x1000007: raise ValueError('Requires thin x86_64 Mach-O')
    segments = []; at = 32
    for _ in range(header[4]):
        command,size = struct.unpack_from('<II',data,at)
        if size < 8 or at+size > len(data): raise ValueError('Invalid Mach-O commands')
        if command == 0x19:
            _,_,name,vm,_,offset,length,*_ = struct.unpack_from('<II16sQQQQiiII',data,at)
            if offset+length > len(data): raise ValueError('Invalid segment extent')
            segments.append((name.rstrip(b'\0').decode(),vm,offset,length))
        at += size
    result = subprocess.run(['nm','-C',str(args.binary)],check=True,capture_output=True,text=True)
    symbols = {}
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) == 3:
            try: symbols[fields[2]] = int(fields[0],16)
            except ValueError: pass
    def floats(address,count):
        matches = [s for s in segments if s[1] <= address and address+count*4 <= s[1]+s[3]]
        if len(matches) != 1: raise ValueError('Scalar outside a unique file-backed segment')
        segment = matches[0]; offset = segment[2]+address-segment[1]
        return list(struct.unpack_from('<'+str(count)+'f',data,offset))
    values = {name:dict(address=hex(symbols[name]),float32_values=floats(symbols[name],5)) for name in NAMES}
    methods = ['PluginDSP::rbnfx_'+name+'()' for name in ('kick','snare','clap','hihat')]
    table=symbols['gf_rbnfx_thru_lvl_table']
    snare_offsets=dict(tone_scale=1932,tone_decay_scale=1936,base_frequency=2364,lowpass_frequency=2368,
                       highpass_frequency=2372,second_tone_offset=2376,noise_scale=2380,noise_limit=2384,
                       clip_high=2388,clip_low=2392,output_scale=2396)
    clap_offsets=dict(output_scale=1840,bandpass_frequency=1848,highpass_frequency=1852,
                      saw_frequency=1856,burst_seconds=1860,clip_high=1864,clip_low=1868,
                      tail_scale_alternate=1880,tail_scale_default=1884)
    hat_offsets=dict(highpass1_frequency=1908,highpass2_frequency=1912,pulse1_frequency=1852,
                     pulse2_frequency=1916,pulse3_frequency=1920,pulse4_frequency=1924,attack_decay_ratio=1928,
                     noise_scale=1936,pulse_scale=1940,output_scale=1944)
    save_json(args.report,dict(kind='rmx220-drum-local-scalar-observation',binary_sha256=sha256(args.binary),script_sha256=sha256(Path(__file__)),
              symbol_inventory_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),named_float_arrays=values,
              generator_symbols={name:hex(symbols[name]) for name in methods},
              hat_numeric_hypothesis=dict(reference_symbol='gf_rbnfx_thru_lvl_table',
                  scalars={name:dict(byte_offset=offset,value=floats(table+offset,1)[0]) for name,offset in hat_offsets.items()},
                  decay_choices=floats(symbols['_g_hh_cstm_dec_tbl'],3),pulse_levels=floats(table+2320,2),
                  curve60=dict(quadratic_linear=floats(table+2152,2),upper_vector=floats(table+2288,4),lower_vector=floats(table+2304,4))),
              clap_numeric_hypothesis=dict(reference_symbol='gf_rbnfx_thru_lvl_table',
                  scalars={name:dict(byte_offset=offset,value=floats(table+offset,1)[0]) for name,offset in clap_offsets.items()},
                  decay_choices=floats(symbols['_g_cl_cstm_dec_tbl'],6)),
              snare_numeric_hypothesis=dict(reference_symbol='gf_rbnfx_thru_lvl_table',
                  scalars={name:dict(byte_offset=offset,value=floats(table+offset,1)[0]) for name,offset in snare_offsets.items()},
                  decay_choices=floats(symbols['_g_sn_cstm_dec_tbl'],3),
                  curve60=dict(threshold=floats(table+1680,1)[0],quadratic_linear=floats(table+2144,2),
                               upper_vector=floats(table+2256,4),lower_vector=floats(table+2272,4))),
              kick_curve_constants=dict(reference_symbol='gf_rbnfx_thru_lvl_table',byte_offset=2120,
                                        float32_values=floats(symbols['gf_rbnfx_thru_lvl_table']+2120,4)),
              scope='Read-only file observation of numeric constants and symbol names. No code/instruction listing, binary, original audio or DSP state is distributed. Field semantics and complete audio synthesis still require independent identification and waveform tests.'))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    raise SystemExit(observe(parser.parse_args()))


if __name__ == '__main__': main()
