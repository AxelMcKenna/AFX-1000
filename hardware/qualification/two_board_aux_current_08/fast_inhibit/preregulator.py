"""Selected architecture's regulator operating requirements, not bench acceptance."""
import json
from .candidate import calculate,HERE

def calculate_preregulator():
 rtop=105000;rb=20000;e=.0035;ib=100e-9
 nom=.8*(1+rtop/rb)
 lo=.8*.982*(1+rtop*(1-e)/(rb*(1+e)))-ib*rtop*(1+e)
 hi=.8*1.03*(1+rtop*(1+e)/(rb*(1-e)))+ib*rtop*(1+e)
 aux=calculate()['regulator'];load=.1;ig=.0001
 ldo_loss=(hi-aux['conditional_interval_V'][0])*load+hi*ig
 buck_output_W=hi*(load+ig)+hi**2/(rtop+rb)
 buck_max_loss=(125-85)/61.6
 return {'selected_controller':'TPS62175DQCR','output_nominal_V':nom,'conditional_output_interval_V':[lo,hi],
  'R_top_ohm':rtop,'R_bottom_ohm':rb,'total_R_error_allocation':e,'FB_current_bound_at0V8_A':ib,
  'input_operating_scenario_V':[9.8,13.2],'controller_recommended_input_V':[4.75,28],
  'LDO_accuracy_headroom_margin_at_prereg_min_V':lo-aux['input_for_accuracy_V'],
  'maximum_LDO_loss_at_allocated100mA_W':ldo_loss,'LDO_JEDEC66p2_sensitivity_TJ_at85C':85+66.2*ldo_loss,
  'maximum_installed_LDO_theta_JA_for125C_at85C':40/ldo_loss,
  'buck_output_power_requirement_W':buck_output_W,'buck_maximum_loss_using_JEDEC61p6_at85C_W':buck_max_loss,
  'minimum_buck_efficiency_for_that_thermal_screen':buck_output_W/(buck_output_W+buck_max_loss),
  'LC_requirement':{'nominal_L_H':10e-6,'nominal_Cout_F':22e-6,'datasheet_total_LC_variation_assumption':.2,'effective_Cout_target_interval_F':[17.6e-6,26.4e-6],'effective_Cin_min_requirement_F':1.76e-6,'Cin_voltage_rating_requirement_V':25,'Cout_voltage_rating_requirement_V':10,'inductor_peak_current_requirement_A':1.2,'inductor_L_at_current_and_temperature_qualified':False},
  'wiring':{'1_PGND':'AGND ground plane','2_VIN':'VIN_IC with local input capacitor','3_EN':'VIN_IC (always on)','4_NC':'AGND','5_FB':'105k/20k divider midpoint','6_AGND':'AGND quiet return','7_PG':'unused open-drain output; no pull-up needed if unused','8_SLEEP':'new 5V preregulator output (normal operation after startup)','9_SW':'10uH inductor input','10_VOS':'new 5V preregulator output at output capacitor','exposed_pad':'AGND and PGND with thermal vias','P_U102_IN8_and_EN5':'new 5V preregulator output instead of VIN_IC'},
  'source_accuracy_conditions':'TPS62175 power-save -1.8/+3%;PWM +/-1.8%;VIN>=VOUT+1V;10uH/22uF;temperature-40..85C;total divider error is allocation, not selected-component qualification',
  'no_claims':['100mA is not a full application current bound','Buck efficiency curves are typical; numerical minimum is a receiving requirement','LC bias/saturation and PCB thermal resistance not yet established','Buck startup/transient, short circuit and actual gate turnoff not qualified','No schematic or board mutation'],
  'board_changed':False,'thermal_qualified':False}
if __name__=='__main__':(HERE/'preregulator.json').write_text(json.dumps(calculate_preregulator(),indent=2)+'\n')
