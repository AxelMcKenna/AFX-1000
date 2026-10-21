#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
swift build -c release
app="RMX Lab.app"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS"
cp .build/release/RMXLab "$app/Contents/MacOS/RMXLab"
cp Info.plist "$app/Contents/Info.plist"
echo "Built $PWD/$app"
