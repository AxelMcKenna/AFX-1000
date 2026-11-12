import subprocess,sys
for p in ['components','shell','hardware','harness','retention_positive','positive','supports']:
 subprocess.run([sys.executable,'-m','hardware.cad.two_board_installation_06.r8.run',p],check=True)
