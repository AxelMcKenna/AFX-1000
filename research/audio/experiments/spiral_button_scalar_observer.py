"""Observe bounded Spiral pitch clock and ring-offset metadata; never audio buffers."""
import hashlib,json,os,struct
from pathlib import Path
import lldb
OUTPUT=Path(os.environ['RMX_SPIRAL_PITCH_TRACE']);BASE=0;MODULE=None;NEXT=0;PENDING=None;POINTS=[]
SAMPLES=[*range(0,9),*range(2999,3012),*range(4508,4531),4540,4560,4600,4630,4700,4800,4900,4910,5000,6000,6006,6007,6008,6012,7506,7507,7510,7515,7550,7600,7900,8000,9000,9007,9008,10519,10520,10525,10600,10920]
def read(p,a,n):
 e=lldb.SBError();b=p.ReadMemory(a,n,e)
 if not e.Success() or len(b)!=n:raise RuntimeError(str(e))
 return b
def state(frame):
 p=frame.GetThread().GetProcess()
 fields={'selected':(0x92f6,'H'),'requested':(0x92f4,'H'),'phase':(0x930c,'H'),'init':(0x9308,'H'),'common_wet':(0x9330,'3f'),'dry':(0x9240,'3f'),'dry_blocks':(0x924c,'H'),'dry_target':(0x9324,'3f'),'private_gain':(0xc270,'2f'),'input_gain':(0xe854,'f'),'primary_gain':(0xe85c,'f'),'primary_age':(0x9310,'I'),'secondary_mix':(0x98f0,'3f'),'secondary_age':(0x98e0,'I'),'main_slewed':(0x933e,'H'),'loop_delay':(0xe578,'d'),'loop_phase':(0xe540,'f'),'held':(0xe584,'f'),'floor':(0xe580,'f'),'pitch_change':(0xdf98,'H'),'output_gain':(0xa810,'3f')}
 r={n:list(struct.unpack('<'+f,read(p,BASE+o,struct.calcsize('<'+f)))) for n,(o,f) in fields.items()}
 return r
def point(frame,location,internal):
 global PENDING
 PENDING['after_scene']=state(frame)
 with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
 location.GetBreakpoint().SetEnabled(False)
 return False

def before(frame,location,internal):
 global BASE,MODULE,NEXT,PENDING,POINTS
 BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule();target=frame.GetThread().GetProcess().GetTarget()
 if NEXT==0:
  assert hashlib.sha256(Path(str(MODULE.GetFileSpec())).read_bytes()).hexdigest()=='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced'
  bp=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(0x24ae4).GetLoadAddress(target));bp.SetScriptCallbackFunction(__name__+'.point');POINTS=[bp.GetID()]
 index=SAMPLES[NEXT];NEXT+=1;PENDING={'block':index,'before_scene':state(frame)}
 for ident in POINTS:target.FindBreakpointByID(ident).SetEnabled(True)
 if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
 else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-index-1)
 return False
def __lldb_init_module(debugger,internal):
 with OUTPUT.open('x'):pass
 b=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_subproc()');b.SetScriptCallbackFunction(__name__+'.before')
