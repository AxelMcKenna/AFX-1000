"""Source-table-derived exact resistor selections; no stock or lifetime claim."""
import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
PARTS={'E_R83':('1072',10700),'E_R84':('5761',5760),'E_R88':('1622',16200),'E_R89':('1332',13300)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 rows=[]
 for ref,(code,ohms) in PARTS.items():
  assert int(code[:3])*10**int(code[3])==ohms and 250<ohms<=260000
  rows.append({'ref':ref,'nominal_ohm':ohms,'MPN':'PLT0805Z'+code+'LST1','value_unchanged':True,'package':'0805','TCR_ppm_per_C':5,'initial_tolerance_fraction':.0001,'operating_temperature_C':[-55,125],'rated_power_W':.25,'working_voltage_V':100,'datasheet':'https://www.vishay.com/docs/60030/plt.pdf','part_number_derivation':{'family':'PLT','case':'0805','TCR':'Z','resistance':code,'tolerance':'L','termination':'S','packaging':'T1'},'procurement_stock_verified':False})
 # Manufacturer dimensions are inches; original PCB land is 0805 1.025x1.4mm at +/-0.9125mm.
 dims={'length_mm':[.074*25.4,.086*25.4],'width_mm':[.045*25.4,.055*25.4],'height_mm':[.015*25.4,.033*25.4],'top_termination_D_mm':[.008*25.4,.024*25.4],'bottom_termination_E_mm':[.010*25.4,.020*25.4]};pad_inner=.9125-1.025/2;pad_outer=.9125+1.025/2
 result={'source_sha256':{'primary/plt.pdf':sha(H/'primary/plt.pdf'),'select.py':sha(Path(__file__))},'primary_document':'Vishay60030 revision11-May-2026 pages1–2','parts':rows,'ordering_table_scope':'Resistance range and ordering-code table support these specified parts; no manufacturer stock/lead-time claim.','dimensions':dims,'retained_land_mm':{'pad_size':[1.025,1.4],'pad_centers_x':[-.9125,.9125],'minimum_outer_toe_extension_mm':pad_outer-dims['length_mm'][1]/2,'minimum_centered_terminal_pad_overlap_mm':min(dims['bottom_termination_E_mm'][0],dims['length_mm'][0]/2-pad_inner)},'initial_plus_TCR_bound_fraction_at125C':.0001+5e-6*100,'stability_limits':{'2000h_at70C_absolute_fraction':.0002,'one_year25C_shelf_absolute_fraction':.0001,'solder_heat_and10000h_values_are_typical_not_limits':True,'full_service_life_bound_proven':False},'functional_values_changed':False,'qualified':False}
 (H/'selection.json').write_text(json.dumps(result,indent=2)+'\n');print([x['MPN'] for x in rows])
if __name__=='__main__':run()
