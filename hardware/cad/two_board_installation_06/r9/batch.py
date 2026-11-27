import subprocess,sys
for p in ['external_pod','external_parts','external_fans','external_ties','ties_pod','ties_parts','head_pod','head_parts','head_leads','lead_components','lead_controls','lead_fans','fan_pod_clearance','bushing_pod','bushing_shell','pod_components','tie_positive','pod','lead_cap','external_harness']:
 subprocess.run([sys.executable,'-m','hardware.cad.two_board_installation_06.r9.run',p],check=True)
