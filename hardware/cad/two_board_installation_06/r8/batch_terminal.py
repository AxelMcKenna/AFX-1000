import subprocess,sys
for p in ['components','shell','mutual_wires','positive','harness']:
 subprocess.run([sys.executable,'-m','hardware.cad.two_board_installation_06.r8.run_terminal',p],check=True)
