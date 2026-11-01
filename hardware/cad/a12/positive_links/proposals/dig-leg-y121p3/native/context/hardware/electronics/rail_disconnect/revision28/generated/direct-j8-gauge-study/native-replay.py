"""Sequential native receipt replay; no source or receiving-bound relaxation."""
import subprocess
import sys
exe = "/private/tmp/rmx-openscad-mounted/OpenSCAD.app/Contents/MacOS/OpenSCAD"
base = "hardware.electronics.rail_disconnect.revision28."
for name, extra in (("direct_j8_gauge", ["--capture"]), ("direct_j8_gauge_details", []), ("direct_j8_south_gauge", [])):
    subprocess.run([sys.executable, "-m", base + name, *extra, "--openscad", exe], check=True, timeout=300)
