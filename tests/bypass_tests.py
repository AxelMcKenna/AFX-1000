#!/usr/bin/env python3
"""Check the emitted CAD connectivity and ideal digital bypass fault behavior.

Deliberately reads the KiCad file, not generator internals or the JSON pin map.
This is a restricted schematic reader and ideal logic model, not KiCad ERC,
analog simulation, propagation-delay analysis or target/relay measurement.
"""
import copy
import itertools
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / 'hardware/electrical/bypass-permission.kicad_sch'


def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = [[]]
    for token in tokens:
        if token == '(':
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ')':
            assert len(stack) > 1, 'Extra closing parenthesis'
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    assert len(stack) == 1 and len(stack[0]) == 1, 'Unbalanced CAD file'
    return stack[0][0]


def children(node, name):
    return [n for n in node[1:] if isinstance(n, list) and n and n[0] == name]


def child(node, name):
    entries = children(node, name)
    assert len(entries) == 1, (name, entries)
    return entries[0]


def xy(node):
    return tuple(round(float(n), 5) for n in node[1:3])


def read_circuit(text):
    root = parse(text)
    assert root[0] == 'kicad_sch'
    libraries = {n[1]: n for n in children(child(root, 'lib_symbols'), 'symbol')}
    parent = {}

    def find(p):
        parent.setdefault(p, p)
        if parent[p] != p:
            parent[p] = find(parent[p])
        return parent[p]

    def union(a, b):
        parent[find(a)] = find(b)

    labels = {}
    for n in children(root, 'label')+children(root,'global_label'):
        point = xy(child(n, 'at'))
        assert point not in labels or labels[point] == n[1], 'Shorted labels'
        labels[point] = n[1]
        find(point)
    nc = {xy(child(n, 'at')) for n in children(root, 'no_connect')}
    result = {}
    pins_at = {}
    for n in children(root, 'symbol'):
        lib = libraries[child(n, 'lib_id')[1]]
        props = {p[1]: p[2] for p in children(n, 'property')}
        ref = props['Reference']
        assert ref not in result, 'Duplicate reference'
        x, y = xy(child(n, 'at'))
        assert child(n, 'at')[3] == '0', 'Reader only supports unrotated symbols'
        pins = {}
        for unit in children(lib, 'symbol'):
            for pin in children(unit, 'pin'):
                px, py = xy(child(pin, 'at'))
                point = round(x+px, 5), round(y-py, 5)
                number = child(pin, 'number')[1]
                assert number not in pins
                pins[number] = {'point': point, 'name': child(pin, 'name')[1], 'type': pin[1]}
                assert point not in pins_at, 'Overlapping component pins'
                pins_at[point] = ref, number
                find(point)
        result[ref] = {'value': props['Value'], 'pins': pins}
    for n in children(root, 'wire'):
        points = children(child(n, 'pts'), 'xy')
        assert len(points) == 2
        a, b = map(xy, points)
        assert a[0] == b[0] or a[1] == b[1], 'Reader requires orthogonal wires'
        union(a, b)
        for point in list(parent):
            if (a[0] == b[0] == point[0] and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]) or
                a[1] == b[1] == point[1] and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])):
                union(a, point)
    nets = {}
    for point, label in labels.items():
        r = find(point)
        assert r not in nets or nets[r] == label, 'Wire joins different named nets'
        nets[r] = label
    used_nc = set()
    for part in result.values():
        for pin in part['pins'].values():
            point = pin.pop('point')
            if point in nc:
                assert find(point) not in nets, 'NC marker on connected pin'
                pin['net'] = None
                used_nc.add(point)
            else:
                assert find(point) in nets, 'Unlabelled/unconnected pin'
                pin['net'] = nets[find(point)]
    assert used_nc == nc, 'NC marker off-pin'
    return result


class Circuit:
    def __init__(self, parts):
        self.parts = parts

    def net(self, ref, number):
        return self.parts[ref]['pins'][str(number)]['net']

    def step(self, q, previous_clock, inputs):
        values = {'+3V3': True, 'GND': False, **inputs}
        for ref, a, b, out in [('U22',1,2,7),('U22',5,6,3),('U23',1,2,4)]:
            values[self.net(ref,out)] = values[self.net(ref,a)] and values[self.net(ref,b)]
        # Both stages sample OLD data at a common edge. Reset is asynchronous.
        values[self.net('U24',5)] = q[0]
        values[self.net('U24',9)] = q[1]
        clock = values[self.net('U24',3)]
        assert values[self.net('U24',11)] == clock, 'Clock nets must be common'
        updated = []
        for i,(rd,sd,data) in enumerate(((1,4,2),(13,10,12))):
            assert values[self.net('U24',sd)], 'Asynchronous set must be inactive'
            if not values[self.net('U24',rd)]:
                updated.append(False)
            elif clock and not previous_clock:
                updated.append(values[self.net('U24',data)])
            else:
                updated.append(q[i])
        values[self.net('U24',5)] = updated[0]
        values[self.net('U24',9)] = updated[1]
        return tuple(updated),clock,values[self.net('J_BP4',1)]


ALL_GOOD = dict(WD_OK=True, DSP_READY=True, PG_OK=True, EXT_RAILS_OK=True)


class Watchdog:
    """Ideal TPS3435 option A frame behavior after supply/calibration settle.

    Datasheet 7.3.1.3: startup at power-up and after output pulse, exited by a
    valid falling WDI edge; no fall within tWD causes an output-low pulse.
    No analog, pulse-width, internal oscillator or propagation simulation.
    """
    def __init__(self, timeout=49.995, pulse=49.5, startup=10000):
        self.timeout, self.pulse, self.startup = timeout,pulse,startup
        self.phase, self.until, self.previous_wdi = 'startup',startup,False

    def step(self, now, wdi):
        falling = self.previous_wdi and not wdi
        self.previous_wdi = wdi
        while now >= self.until:
            if self.phase == 'fault':
                self.phase, self.until = 'startup',self.until+self.startup
            else:
                self.phase, self.until = 'fault',self.until+self.pulse
        if self.phase != 'fault' and falling:
            self.phase, self.until = 'monitor',now+self.timeout
        return self.phase != 'fault'


class BypassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = read_circuit(CAD.read_text())
        cls.circuit = Circuit(cls.parts)

    def test_vendor_pin_numbers_and_types(self):
        for ref, value in {'U21':'TPS3435AFACADDFRQ1','U22':'74LVC2G08DP',
                           'U23':'74LVC1G08GV','U24':'74LVC74APW',
                           'U25':'TPS3808G33DBVR','U26':'TPS3808G50DBVR'}.items():
            self.assertEqual(self.parts[ref]['value'], value)
        expected = {
            'U21': ['MR_N','CWD','CRST','GND','SET0','WDI','WDO_N','VDD'],
            'U22': ['1A','1B','2Y','GND','2A','2B','1Y','VCC'],
            'U23': ['B','A','GND','Y','VCC'],
            'U24': ['1RD_N','1D','1CP','1SD_N','1Q','1Q_N','GND','2Q_N','2Q','2SD_N','2CP','2D','2RD_N','VCC'],
            'U25': ['RESET_N','GND','MR_N','CT','SENSE','VDD'],
            'U26': ['RESET_N','GND','MR_N','CT','SENSE','VDD'],
        }
        for ref, names in expected.items():
            pins = self.parts[ref]['pins']
            self.assertEqual(len(pins), len(names))
            for i, name in enumerate(names, 1):
                self.assertEqual(pins[str(i)]['name'], name, (ref, i))
        for ref, number in [('U21',7), ('U25',1), ('U26',1)]:
            self.assertEqual(self.parts[ref]['pins'][str(number)]['type'], 'open_collector')
        self.assertIsNone(self.circuit.net('U24',6))
        self.assertIsNone(self.circuit.net('U24',8))

    def test_bias_supplies_and_interfaces(self):
        c = self.circuit
        for ref, vcc, gnd in [('U21',8,4),('U22',8,4),('U23',5,3),('U24',14,7),('U25',6,2),('U26',6,2)]:
            self.assertEqual(c.net(ref,vcc), '+3V3')
            self.assertEqual(c.net(ref,gnd), 'GND')
        for ref, a, b in [('R21','+3V3','WD_OK'),('R25','+3V3','PG_OK'),('R22','DSP_READY','GND'),('R23','HEARTBEAT','GND'),('R24','EXT_RAILS_OK','GND'),('R29','RELAY_PERMISSION','GND')]:
            self.assertEqual({c.net(ref,1),c.net(ref,2)}, {a,b})
        self.assertEqual(c.net('U21',1), '+3V3')
        self.assertEqual(c.net('U21',5), 'GND')
        self.assertEqual(c.net('U25',5), '+3V3')
        self.assertEqual(c.net('U26',5), '+5V')
        self.assertEqual(c.net('U25',1), c.net('U26',1))
        self.assertEqual(c.net('SW32',1), c.net('U25',3))
        self.assertEqual(c.net('SW32',1), c.net('U26',3))
        self.assertEqual(c.net('SW32',2), 'GND')
        for ref in range(22,28):
            self.assertEqual({c.net('C'+str(ref),1),c.net('C'+str(ref),2)}, {'+3V3','GND'})
        self.assertEqual(c.net('J_BP2',1), c.net('U21',6))
        self.assertEqual(c.net('J_BP2',1), c.net('U24',3))
        self.assertEqual(c.net('J_BP2',1), c.net('U24',11))
        self.assertEqual(c.net('U24',5), c.net('U24',12))
        self.assertEqual(c.net('U24',1), c.net('U24',13))
        self.assertEqual(c.net('U24',2), '+3V3')
        self.assertEqual(c.net('U24',4), '+3V3')
        self.assertEqual(c.net('U24',10), '+3V3')
        self.assertEqual(c.net('J_BP2',2), 'DSP_READY')
        self.assertEqual(c.net('J_BP3',1), 'EXT_RAILS_OK')
        self.assertEqual(c.net('J_BP4',1), c.net('U24',9))

    def prime(self,circuit=None,q=(False,False),prev=False):
        circuit = circuit or self.circuit
        for heartbeat in (False,True,False,True):
            q,prev,on=circuit.step(q,prev,{**ALL_GOOD,'HEARTBEAT':heartbeat})
        return q,prev,on

    def test_exhaustive_state_transitions(self):
        # Two prior Q bits, prior common clock and five external inputs: 256.
        for q1,q2,previous,wd,ready,pg,ext,hb in itertools.product([False,True],repeat=8):
            inputs=dict(WD_OK=wd,DSP_READY=ready,PG_OK=pg,EXT_RAILS_OK=ext,HEARTBEAT=hb)
            nq,clock,on=self.circuit.step((q1,q2),previous,inputs)
            healthy=wd and ready and pg and ext
            edge=hb and not previous
            self.assertEqual(nq,(healthy and (True if edge else q1),
                                 healthy and (q1 if edge else q2)),inputs)
            self.assertEqual(on,nq[1])
            self.assertEqual(clock,hb)

    def test_stalled_heartbeat_never_reconnects_after_fault_pulses(self):
        for frozen_clock in (False,True):
            q,prev,on=self.prime()
            self.assertTrue(on)
            for _ in range(100):
                for wd in (False,True):
                    q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':wd,'HEARTBEAT':frozen_clock})
                    self.assertFalse(on)
            _,_,on=self.prime(q=q,prev=prev)
            self.assertTrue(on)

    def test_each_fault_requires_two_fresh_edges(self):
        for fault in ALL_GOOD:
            q,prev,on=self.prime()
            self.assertTrue(on)
            q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,fault:False,'HEARTBEAT':True})
            self.assertFalse(on)
            q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'HEARTBEAT':True})
            self.assertFalse(on)
            for heartbeat,want in ((False,False),(True,False),(False,False),(True,True)):
                q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'HEARTBEAT':heartbeat})
                self.assertEqual(on,want,(fault,heartbeat))

    def test_model_detects_broken_clear_or_clock_wiring(self):
        bad=copy.deepcopy(self.parts)
        bad['U24']['pins']['13']['net']='+3V3'
        circuit=Circuit(bad)
        q,prev,on=self.prime(circuit)
        self.assertTrue(on)
        _,_,on=circuit.step(q,prev,{**ALL_GOOD,'WD_OK':False,'HEARTBEAT':True})
        self.assertTrue(on,'Broken final clear must violate fault clearance')
        bad=copy.deepcopy(self.parts)
        for pin in ('3','11'):
            bad['U24']['pins'][pin]['net']='+3V3'
        _,_,on=self.prime(Circuit(bad))
        self.assertFalse(on,'Clock stuck high must prevent complete qualification')

    def test_timeout_capacitance_and_tolerances(self):
        c = self.circuit
        self.assertEqual(self.parts['C21']['value'], '10nF C0G 1%')
        self.assertEqual(self.parts['C28']['value'], '100pF C0G 1%')
        self.assertEqual(self.parts['C29']['value'], '10nF C0G 1%')
        for ref,net in [('C21','CWD'),('C28','CWD'),('C29','CRST')]:
            self.assertEqual({c.net(ref,1),c.net(ref,2)}, {net,'GND'})
        self.assertEqual(c.net('U21',2),'CWD')
        self.assertEqual(c.net('U21',3),'CRST')
        nominal = 4.95 * (10 + .1)
        self.assertAlmostEqual(nominal,49.995)
        self.assertLess(abs(nominal-50), .01)
        self.assertAlmostEqual(nominal*.8*.99,39.59604)
        self.assertAlmostEqual(nominal*1.2*1.01,60.59394)
        self.assertGreater(nominal*1.2*1.01,50)  # Nominal, not a 50ms maximum.
        self.assertGreaterEqual(10.1*.99,1.5)
        self.assertLessEqual(10.1*1.01,1000)
        self.assertGreaterEqual(10*.99,1.5)
        self.assertLessEqual(10*1.01,1800)
        self.assertLess(10.1*1.01,200*10*.99)  # Calibration constraint.

    def test_permission_cannot_precede_watchdog_monitoring(self):
        for bypass_first_stage in (False,True):
            parts=copy.deepcopy(self.parts)
            if bypass_first_stage:
                parts['U24']['pins']['12']['net']='+3V3'
            circuit,wd=Circuit(parts),Watchdog()
            q,prev,violation=(False,False),False,False
            for now,hb in [(0,False),(1,True),(2,False),(3,True)]:
                ok=wd.step(now,hb)
                q,prev,on=circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':hb})
                violation |= on and wd.phase!='monitor'
            self.assertEqual(violation,bypass_first_stage)
            self.assertEqual(wd.phase,'monitor')

    def test_stalls_during_startup_monitoring_and_recovery(self):
        # Millisecond grid deliberately excludes edge-at-timeout ambiguity.
        for timeout in (39.59604,49.995,60.59394):
            for freeze_at in (0,1,2,3,4,50,299,300,301,302,303,999):
                wd=Watchdog(timeout=timeout)
                q,prev=(False,False),False
                last_on=None
                for now in range(12000):
                    hb=bool(min(now,freeze_at)%2)
                    ok=wd.step(now,hb)
                    q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'PG_OK':now>=300,'WD_OK':ok,'HEARTBEAT':hb})
                    if on:
                        self.assertEqual(wd.phase,'monitor',(timeout,freeze_at,now))
                        last_on=now
                    if now>freeze_at+timeout+1:
                        self.assertFalse(on,(timeout,freeze_at,now))
                if freeze_at<303:
                    self.assertIsNone(last_on)

    def test_recovery_first_rising_edge_does_not_arm(self):
        wd=Watchdog()
        q,prev=(False,False),False
        for now,hb in [(0,False),(1,True),(2,False),(3,True),(53,True),(101,False),(103,False)]:
            ok=wd.step(now,hb)
            q,prev,_=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':hb})
        self.assertEqual(wd.phase,'startup')
        for now,hb in [(104,True),(1000,True)]:
            ok=wd.step(now,hb)
            q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':hb})
            self.assertFalse(on)
        ok=wd.step(1001,False)
        q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':False})
        self.assertEqual(wd.phase,'monitor')
        self.assertFalse(on)
        ok=wd.step(1002,True)
        q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':True})
        self.assertTrue(on)
        ok=wd.step(1062,True)
        _,_,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':True})
        self.assertFalse(on)

    def test_late_watchdog_release_needs_another_complete_pulse(self):
        # Conservative ordering: a falling WDI edge is ignored just before WDO
        # releases. Even if first stage clocks at release, it cannot arm stage 2.
        q,prev=(False,False),False
        q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'HEARTBEAT':True})
        self.assertFalse(on)
        # Falling edge after release is guaranteed to reach the watchdog before
        # the second rising edge can set permission (subject to physical timing).
        wd=Watchdog()
        wd.previous_wdi=True
        ok=wd.step(1,False)
        self.assertEqual(wd.phase,'monitor')
        q,prev,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':False})
        self.assertFalse(on)
        ok=wd.step(2,True)
        _,_,on=self.circuit.step(q,prev,{**ALL_GOOD,'WD_OK':ok,'HEARTBEAT':True})
        self.assertTrue(on)


if __name__ == '__main__':
    unittest.main()
