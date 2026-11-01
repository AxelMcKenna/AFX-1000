"""Read-only late-window metadata for our synthetic overdub commands."""
import hashlib,json,os,struct
from pathlib import Path
import lldb
OUTPUT=None
AFTER=None
PENDING=None
LAST=None
CALLS=0
ROWS=0


def reg(f,name):return f.FindRegister(name).GetValueAsUnsigned()
def read(f,address,fmt):
    e=lldb.SBError();n=struct.calcsize(fmt);b=f.GetThread().GetProcess().ReadMemory(address,n,e)
    if not e.Success() or len(b)!=n:raise RuntimeError('Command metadata read failed')
    values=struct.unpack(fmt,b);return values[0] if len(values)==1 else list(values)
def emit(row):
    global ROWS
    if ROWS>=2000:raise RuntimeError('Command metadata bound exceeded')
    with OUTPUT.open('a') as s:s.write(json.dumps(row)+'\n')
    ROWS+=1

def after(f,location,internal):
    global PENDING,LAST
    seq,clock,command,before=PENDING
    table=read(f,seq,'<128H');flag=read(f,seq+0x100,'<I');mask=read(f,seq+0x104,'<I');output=read(f,command,'<H')
    changes=[[i,v] for i,v in enumerate(table) if LAST is None or v!=LAST[0][i]]
    if changes or before or output or LAST is None or (flag,mask)!=LAST[1:]:emit(dict(beat=read(f,clock+0x198,'<d'),input=before,output=output,flag=flag,mask=mask,slot_changes=changes))
    LAST=(table,flag,mask);PENDING=None;AFTER.SetEnabled(False)
    return False

def entry(f,location,internal):
    global OUTPUT,AFTER,PENDING,CALLS
    if OUTPUT is None:
        module=f.GetModule();binary=Path(str(module.GetFileSpec()))
        if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong Original')
        OUTPUT=Path(os.environ['RMX_PATTERN_CLOCK_TRACE'])
        with OUTPUT.open('x'):pass
        target=f.GetThread().GetProcess().GetTarget();AFTER=target.BreakpointCreateByAddress(module.ResolveFileAddress(0x5bbd).GetLoadAddress(target));AFTER.SetScriptCallbackFunction(__name__+'.after');AFTER.SetEnabled(False)
        location.GetBreakpoint().SetIgnoreCount(10000)
        return False
    CALLS+=1
    if CALLS>4000:location.GetBreakpoint().SetEnabled(False);return False
    PENDING=(reg(f,'rdi'),reg(f,'rcx'),reg(f,'rsi'),read(f,reg(f,'rsi'),'<H'));AFTER.SetEnabled(True)
    return False

def __lldb_init_module(debugger,internal):
    p=debugger.GetSelectedTarget().BreakpointCreateByName('BeatOverDubFunction::OverDubMain(unsigned short&, unsigned short (&) [5], BeatManager*, int&, int&, unsigned short, int)');p.SetScriptCallbackFunction(__name__+'.entry')
