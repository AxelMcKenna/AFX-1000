"""Read-only sparse selector/send/direct gain observations; never reads sample buffers."""
import hashlib,json,os,struct
from pathlib import Path
import lldb
BASE=0
OUTPUT=None
BLOCKS=[]
CURSOR=0


def observe(frame,location,internal):
    global CURSOR
    process=frame.GetThread().GetProcess()
    def read(offset,fmt):
        error=lldb.SBError();size=struct.calcsize(fmt);data=process.ReadMemory(BASE+offset,size,error)
        if not error.Success() or len(data)!=size:raise RuntimeError('Read-only selector observation failed')
        return list(struct.unpack(fmt,data))
    block=BLOCKS[CURSOR]
    row=dict(block=block,controls=read(0x92f4,'<5H'),flags=read(0x9308,'<3H'),wet=read(0x9330,'<3f'),dry_mix=read(0x9324,'<3f'),direct=read(0x9240,'<3f'),main=read(0x933e,'<4H'))
    starts=[read(0xc158+i*16,'<Q')[0] for i in range(4)]
    row['return_bank_frames']=[(read(0xc160+i*16,'<Q')[0]-starts[i])//8 for i in range(4)]
    row['return_write_frames']=[(read(0x9c00+i*8,'<Q')[0]-starts[i])//8 for i in range(4)]
    row['return_send_gain']=read(0xa4c0,'<f')[0]
    row['return_age_interleaved_samples']=read(0xa4c4,'<4I')
    row['return_activation']=read(0xa600,'<3f')
    row['filter_input_gain']=read(0xe854,'<f')[0]
    row['modulation_edges']=[read(0xa610,'<f')[0],read(0xa650,'<f')[0]]
    row['return_weights']=read(0x9c40,'<12f');row['return_weight_blocks']=read(0x9c70,'<H')[0]
    row['echo_delay_words_a484']=read(0xa484,'<4I');row['echo_delay_words_a494']=read(0xa494,'<4I')
    if row['controls'][1]==8:row['hold_clock']=dict(fraction=read(0xbbe0,'<f')[0],count=read(0xbbec,'<H')[0],choice=read(0xbbee,'<H')[0],modulation=read(0xa610,'<32f'))
    with OUTPUT.open('a') as stream:stream.write(json.dumps(row)+'\n')
    CURSOR+=1
    if CURSOR==len(BLOCKS):location.GetBreakpoint().SetEnabled(False)
    else:location.GetBreakpoint().SetIgnoreCount(BLOCKS[CURSOR]-block-1)
    return False


def setup(frame,location,internal):
    global BASE
    module=frame.GetModule();binary=Path(str(module.GetFileSpec()))
    if hashlib.sha256(binary.read_bytes()).hexdigest()!='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced':raise RuntimeError('Wrong Original binary')
    BASE=frame.FindRegister('rdi').GetValueAsUnsigned();target=frame.GetThread().GetProcess().GetTarget();point=target.BreakpointCreateByAddress(module.ResolveFileAddress(0x24ae4).GetLoadAddress(target));point.SetScriptCallbackFunction(__name__+'.observe');point.SetIgnoreCount(BLOCKS[0]);location.GetBreakpoint().SetEnabled(False)
    return False


def __lldb_init_module(debugger,internal):
    global OUTPUT,BLOCKS
    OUTPUT=Path(os.environ['RMX_SCENE_SELECTOR_TRACE']);BLOCKS=json.loads(Path(os.environ['RMX_SCENE_SELECTOR_BLOCKS']).read_text())
    if not BLOCKS or len(BLOCKS)>1500 or BLOCKS!=sorted(set(BLOCKS)) or min(BLOCKS)<0 or max(BLOCKS)>=15000:raise RuntimeError('Invalid bounded selector windows')
    with OUTPUT.open('x'):pass
    point=debugger.GetSelectedTarget().BreakpointCreateByName('PluginDSP::source_select()');point.SetScriptCallbackFunction(__name__+'.setup')
