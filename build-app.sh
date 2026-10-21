#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target RMX --parallel 4
codesign --force --deep --sign - build/RMX.app
print "Built $PWD/build/RMX.app"
