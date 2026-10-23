#!/usr/bin/env python3
"""Account for every modeled part and distinguish target costs from quotes."""
import argparse
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
from generate_budget import ROOT,DEST,all_sheets


def category(part):
    r=part['ref']
    if r=='U1':return 'seed'
    if r=='U8':return 'touch'
    if r=='J_SD1':return 'sd'
    if r.startswith('RV'):return 'pots' if int(r[2:])<=11 else 'trims'
    if r.startswith('SW'):
        n=int(r[2:]);return 'buttons' if n<=29 else 'selectors' if n<=31 else 'switches'
    if r=='U21':return 'watchdog'
    if r in ['U25','U26','U27','U32']:return 'supervisors'
    if r in ['U22','U23','U24','U35']:return 'bypass_logic'
    if r=='U28':return 'opamp'
    if r.startswith('U'):return 'control_logic'
    if r.startswith('DS'):return 'digits'
    if r.startswith('D') and int(r[1:]) in range(100,155):return 'leds'
    if r.startswith(('D','Q','F')):return 'discretes'
    if r.startswith('K'):return 'relay'
    if r.startswith(('R','C')):return 'passives'
    if r.startswith('J'):return 'interconnect'
    raise ValueError('Uncosted component: '+r)


def generate():
    plan=json.loads((DEST/'procurement.json').read_text());rows=plan['rows']
    assert len({r['id'] for r in rows})==len(rows)
    categories={r['id']:[] for r in rows}
    for d in all_sheets():
        for p in d['components']:
            if not p.get('virtual'):categories[category(p)].append(p['ref'])
    total=Decimal(0);listed=Decimal(0);stream=io.StringIO();w=csv.writer(stream,lineterminator='\n')
    w.writerow(['Category','Description','Quantity','UnitNZDInclGST','SubtotalNZD','PricingStatus','CircuitReferences','Source','Notes'])
    for r in rows:
        amount=Decimal(str(r['quantity']))*Decimal(str(r['unit_nzd_including_gst']));total+=amount
        if r['pricing']=='listed':listed+=amount
        w.writerow([r['id'],r['description'],r['quantity'],r['unit_nzd_including_gst'],f'{amount:.2f}',r['pricing'],' '.join(categories[r['id']]),r['source'],r['notes']])
    remaining=Decimal(str(plan['cap_nzd']))-total
    # A target made from allowances must never be reported as a confirmed price.
    assert not plan['supplier_basket_confirmed'],'Requote complete baskets and delivery before changing the budget status'
    report=dict(currency='NZD',target_total=float(total),listed_price_anchors=float(listed),
        unquoted_allowances=float(total-listed),remaining_under_300=float(remaining),
        under_cap_as_planned=remaining>=0,confirmed_delivered_under_300=False,
        status='PROVISIONAL ALLOWANCES - not a supplier basket or guaranteed delivered price',
        circuit_components_costed=sum(len(v) for v in categories.values()),
        assumptions=plan['assumptions'],unquoted_categories=[r['id'] for r in rows if r['pricing']!='listed'])
    return {'shopping-list.csv':stream.getvalue(),'cost-report.json':json.dumps(report,indent=2)+'\n'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    for n,text in generate().items():
        path=DEST/n
        if a.check:assert path.exists() and path.read_text()==text,'Stale cost artifact: '+n
        else:path.write_text(text)
    r=json.loads(generate()['cost-report.json'])
    print(f'Target NZ${r["target_total"]:.2f}; NZ${r["remaining_under_300"]:.2f} headroom; NOT a confirmed delivered quote')


if __name__=='__main__':main()
