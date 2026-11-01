"""Independent-sequence Random Noise profiles; no shared-target audio claim."""
import subprocess
import numpy as np
from tools import noise_motion_statistics as motion


def profile(audio,raw,probe,targets='own'):
    audio=audio[4*48000:];size,step=256,128;epoch_frames=10*48000
    epochs=len(audio)//epoch_frames;count=(len(audio)-size)//step+1
    result=subprocess.run([str(probe),'--bins',str(raw),str(targets),str(4*48000+size//2-4864),str(step),str(count)],capture_output=True,check=True)
    labels=np.frombuffer(result.stdout,dtype=np.uint8)
    if len(labels)!=count or np.any(labels>3):raise ValueError('Invalid Random profile labels')
    window=np.hanning(size);norm=np.sum(window*window);frequencies=np.fft.rfftfreq(size,1/48000)
    masks=[(frequencies>=a)&(frequencies<b) for a,b in zip(motion.EDGES[:-1],motion.EDGES[1:])]
    bands=np.empty((epochs,4,6,2));total=np.empty((epochs,4,2));exposure=np.empty((epochs,4),dtype=np.int32)
    per_epoch=epoch_frames//step
    for epoch in range(epochs):
        first=max(0,epoch*per_epoch-1);end=min(count,(epoch+1)*per_epoch-1)
        slices=np.stack([audio[i*step:i*step+size] for i in range(first,end)])*window[None,:,None]
        spectrum=np.abs(np.fft.rfft(slices,axis=1))**2*(2/(size*norm));spectrum[:,0]*=.5;spectrum[:,-1]*=.5
        bp=np.stack([np.sum(spectrum[:,mask],axis=1) for mask in masks],axis=1);tp=np.sum(slices*slices,axis=1)/norm
        for bin_index in range(4):
            keep=labels[first:end]==bin_index;exposure[epoch,bin_index]=np.sum(keep)
            if not np.any(keep):raise ValueError('A Random profile bin has no exposure')
            bands[epoch,bin_index]=np.mean(bp[keep],axis=0);total[epoch,bin_index]=np.mean(tp[keep],axis=0)
    return dict(bands=bands,total=total,exposure=exposure)


def measure(reference,candidate):
    a,ta,b,tb=reference['bands'],reference['total'],candidate['bands'],candidate['total']
    if a.shape!=b.shape or ta.shape!=tb.shape or a.shape[:2]!=ta.shape[:2] or a.shape[1:]!=(4,6,2) or len(a)<20:
        raise ValueError('Invalid Random profile extent')
    if any(p['exposure'].shape!=a.shape[:2] or np.any(p['exposure']<=0) for p in [reference,candidate]):raise ValueError('Invalid Random exposure')
    if any(not np.isfinite(x).all() or np.min(x)<0 for x in [a,ta,b,tb]):raise ValueError('Invalid Random powers')
    d,h,passed,different=motion.paired(a,b,.5);dl,hl,pl,dl_different=motion.paired(ta,tb,.1)
    meaningful=np.mean(a,axis=0)>=np.mean(ta,axis=0)[:,None,:]*1e-4
    verdict='pass' if np.all(passed[meaningful]) and np.all(pl) else 'different' if np.any(different[meaningful]) or np.any(dl_different) else 'inconclusive'
    return dict(kind='independent-random-control-conditioned-power-screen',verdict=verdict,epoch_seconds=10,band_margin_db=.5,level_margin_db=.1,confidence_multiplier=3.,meaningful_band_floor_db=-40,
        mean_paired_band_log_ratio_db=d.tolist(),band_interval_half_db=h.tolist(),meaningful_bands=meaningful.tolist(),mean_paired_level_log_ratio_db=dl.tolist(),level_interval_half_db=hl.tolist(),
        scope='Separate source-specific control-value bins; independent target sequences have unequal exposures. Ten-second conditional means with unchanged margins/HAC correction; does not establish identical default random controls or audio waveforms.')
