"""Sequential bounded native checks; stop immediately on tool failure."""
import subprocess,sys
for part in ['route_0_obstacles','route_1_obstacles','mutual','shell','boards','positive','harness']:
 subprocess.run([sys.executable,'-m','hardware.cad.two_board_installation_06.r7.run_harness',part],check=True)
