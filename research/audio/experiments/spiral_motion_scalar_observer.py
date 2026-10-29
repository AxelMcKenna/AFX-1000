"""Observe bounded Spiral pitch clock and ring-offset metadata; never audio buffers."""
import hashlib,json,os,struct
from pathlib import Path
import lldb
OUTPUT=Path(os.environ['RMX_SPIRAL_PITCH_TRACE']);BASE=0;MODULE=None;NEXT=0;PENDING=None;POINTS=[]
SAMPLES=[0,1,2,*range(2999,3009),3010,3020,3050,3100,3200,3500,4000,*range(4505,4516),4520,4530,4600,4800,*range(6003,6014),7500,7501,7502,9005,9006,9007,10518]
def read(p,a,n):
 e=lldb.SBError();b=p.ReadMemory(a,n,e)
 if not e.Success() or len(b)!=n:raise RuntimeError(str(e))
 return b
def state(frame):
 p=frame.GetThread().GetProcess()
 fields={'scene':(0x92f6,'H'),'pitch_raw':(0x92fc,'H'),'time_raw':(0x92f8,'H'),'pitch_type':(0xc250,'H'),'up':(0xacca,'H'),'increment':(0xaccc,'f'),'short':(0xd12c,'h'),'phase':(0xde30,'f'),'window_phase':(0xde80,'f'),'window_count':(0xdea0,'H'),'pitch_work':(0xdf70,'7f'),'window_work':(0xdf8c,'7H'),'distances':(0xdf60,'4I'),'window_steps':(0xdf84,'3f'),'loop_delay':(0xe578,'d'),'loop_step':(0xe538,'f'),'loop_phase':(0xe540,'f'),'input_floor':(0xe580,'f'),'feedback_gain':(0xa810,'3f'),'wet_gain':(0x98c8,'3f'),'main_slewed':(0x933e,'H'),'dry_gain':(0x9240,'3f'),'input_peak':(0xe564,'f'),'delay_slew_limit':(0xe52a,'h'),'delay_velocity':(0xe54c,'f'),'delay_acceleration':(0xe550,'f'),'delay_target_velocity':(0xe554,'f'),'secondary_mix':(0x98f0,'3f'),'loop_phase_dir':(0xe53c,'H'),'pitch_change':(0xdf98,'H')}
 r={n:list(struct.unpack('<'+f,read(p,BASE+o,struct.calcsize('<'+f)))) for n,(o,f) in fields.items()}
 begin=struct.unpack('<Q',read(p,BASE+0xdda0,8))[0]
 r['ring_offsets_floats']={n:(address-begin)//4 if address else None for n,o in [('read',0xdd00),('second_read',0xdee0),('second_anchor',0xdf30),('write',0xdd50),('end',0xddf0)] for address in [struct.unpack('<Q',read(p,BASE+o,8))[0]]}
 return r
def point(frame,location,internal):
 global PENDING
 tag=POINTS[location.GetBreakpoint().GetID()];PENDING[tag]=state(frame)
 if tag=='before_pitch':
  process=frame.GetThread().GetProcess();target=process.GetTarget()
  PENDING['coefficients']={n:list(struct.unpack('<5f',read(process,MODULE.ResolveFileAddress(a).GetLoadAddress(target),20))) for n,a in [('loop_highpass',0xc05270),('loop_lowpass',0xc05290),('source_filter',0xc052b0),('output_filter',0xc05310)]}
  PENDING['coefficients']['pitch_filter']=list(struct.unpack('<3f',read(process,BASE+0xdc28,12)))+list(struct.unpack('<2f',read(process,BASE+0xdc38,8)))
  fp=frame.FindRegister('rbp').GetValueAsUnsigned()
  PENDING['loop_write_gain']=struct.unpack('<f',read(process,fp-0x40,4))[0]

 if tag=='after_pitch':
  with OUTPUT.open('a') as f:f.write(json.dumps(PENDING)+'\n')
  for ident in POINTS:frame.GetThread().GetProcess().GetTarget().FindBreakpointByID(ident).SetEnabled(False)
 return False
def before(frame,location,internal):
 global BASE,MODULE,NEXT,PENDING,POINTS
 BASE=frame.FindRegister('rdi').GetValueAsUnsigned();MODULE=frame.GetModule();target=frame.GetThread().GetProcess().GetTarget()
 if NEXT==0:
  assert hashlib.sha256(Path(str(MODULE.GetFileSpec())).read_bytes()).hexdigest()=='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced'
  POINTS={}
  for address,tag in [(0x240d9,'before_pitch'),(0x240e6,'after_pitch')]:
   bp=target.BreakpointCreateByAddress(MODULE.ResolveFileAddress(address).GetLoadAddress(target));bp.SetScriptCallbackFunction(__name__+'.point');POINTS[bp.GetID()]=tag
 index=SAMPLES[NEXT];NEXT+=1;PENDING={'block':index,'before_spiral':state(frame)}
 for ident in POINTS:target.FindBreakpointByID(ident).SetEnabled(True)
 if NEXT==len(SAMPLES):location.GetBreakpoint().SetEnabled(False)
 else:location.GetBreakpoint().SetIgnoreCount(SAMPLES[NEXT]-index-1)
 return False
def __lldb_init_module(debugger,internal):
 with OUTPUT.open('x'):pass
 b=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::scnfx_spiral(float*, float*)');b.SetScriptCallbackFunction(__name__+'.before')
