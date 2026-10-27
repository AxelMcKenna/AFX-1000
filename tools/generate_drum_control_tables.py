#!/usr/bin/env python3
"""Render numeric drum control calibration from its reviewed measurement report."""
import argparse
import json
from pathlib import Path

from tools.reference_audio import sha256
from tools.rmx_drums import require


def generate(args):
    report=json.loads(args.measurement.read_text())
    require(report['kind']=='rmx220-drum-local-scalar-observation' and
            report['binary_sha256']=='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced','Wrong numeric reference')
    tables=report['shared_pitch_level_tables']
    def scalar(x):
        s=format(x,'.17g')
        return s+('f' if '.' in s or 'e' in s else '.0f')
    text='#pragma once\n#include <array>\nnamespace rmx::drums {\n'
    text+='// Numeric control calibration; no original code or audio.\n'
    text+='// Measurement SHA-256: '+sha256(args.measurement)+'\n'
    text+='inline constexpr std::array<float,256> drumLevelTable{\n'
    require(len(tables['level_values'])==256,'Wrong level extent')
    for start in range(0,256,8):text+='    '+','.join(scalar(v) for v in tables['level_values'][start:start+8])+',\n'
    text+='};\n'
    for name,key in [('drumPitchLeft','pitch_left_rows'),('drumPitchRight','pitch_right_rows')]:
        rows=tables[key];require(len(rows)==12 and all(len(row)==4 for row in rows),'Wrong pitch extent')
        text+='inline constexpr std::array<std::array<float,4>,12> '+name+'{{\n'
        for row in rows:text+='    {'+','.join(scalar(v) for v in row)+'},\n'
        text+='}};\n'
    require(tables['pitch_center']==[0,0,0,1],'Unexpected pitch center')
    text+='}\n'
    if args.check:require(args.output.read_text()==text,'Generated drum tables differ')
    else:args.output.write_text(text)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurement',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--check',action='store_true');generate(parser.parse_args())


if __name__=='__main__':main()
