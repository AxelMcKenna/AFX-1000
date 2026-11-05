"""Time-resolved Noise screens conditioned on the verified modulation clock."""
import subprocess

import numpy as np

from tools.audio.noise.noise_statistics import mean_variance

RATE = 48000
STARTUP = 4864
SIZE = 256
STEP = 128
EDGES = (0, 500, 1000, 2000, 4000, 8000, 24001)


def profile(audio, case, probe):
    """Return two-second block powers by expected control value, never audio."""
    stationary = audio[4*RATE:]
    epochs = len(stationary)//(2*RATE)
    count = (len(stationary)-SIZE)//STEP+1
    result = subprocess.run([str(probe), '--bins', str(case['sub2']), str(case['wave']),
        str(4*RATE+SIZE//2-STARTUP), str(STEP), str(count)], capture_output=True, check=True)
    labels = np.frombuffer(result.stdout, dtype=np.uint8)
    bins = 3 if case['wave']==2 else 4
    if len(labels)!=count or np.any(labels>=bins): raise ValueError('Wrong profile labels')
    window = np.hanning(SIZE)
    norm = np.sum(window*window)
    frequencies = np.fft.rfftfreq(SIZE, 1/RATE)
    masks = [(frequencies>=a)&(frequencies<b) for a,b in zip(EDGES[:-1], EDGES[1:])]
    bands = np.empty((epochs,bins,len(masks),2))
    total = np.empty((epochs,bins,2))
    exposure = np.empty((epochs,bins), dtype=np.int32)
    per_epoch = 2*RATE//STEP
    for epoch in range(epochs):
        first=max(0, epoch*per_epoch-1)
        end=min(count, (epoch+1)*per_epoch-1)
        slices=np.stack([stationary[i*STEP:i*STEP+SIZE] for i in range(first,end)])
        weighted=slices*window[None,:,None]
        spectrum=np.abs(np.fft.rfft(weighted, axis=1))**2*(2/(SIZE*norm))
        spectrum[:,0]*=.5; spectrum[:,-1]*=.5
        band_power=np.stack([np.sum(spectrum[:,mask],axis=1) for mask in masks],axis=1)
        total_power=np.sum(weighted*weighted,axis=1)/norm
        for bin_index in range(bins):
            keep=labels[first:end]==bin_index
            if not np.any(keep): raise ValueError('A modulation profile bin has no exposure')
            exposure[epoch,bin_index]=np.sum(keep)
            bands[epoch,bin_index]=np.mean(band_power[keep],axis=0)
            total[epoch,bin_index]=np.mean(total_power[keep],axis=0)
    return dict(bands=bands,total=total,exposure=exposure)


def paired(reference, candidate, margin):
    difference=10*np.log10(np.maximum(candidate,1e-30)/np.maximum(reference,1e-30))
    delta=np.mean(difference,axis=0)
    half=3*np.sqrt(mean_variance(difference))
    return delta,half,np.abs(delta)+half<=margin,np.abs(delta)-half>margin


def measure(reference, candidate):
    a,ta,b,tb=reference['bands'],reference['total'],candidate['bands'],candidate['total']
    if a.shape!=b.shape or ta.shape!=tb.shape or a.shape[:2]!=ta.shape[:2] or a.shape[2:]!=(6,2) or len(a)<20:
        raise ValueError('Invalid modulation profile extent')
    if a.shape[1] not in [3,4] or any(p['exposure'].shape!=a.shape[:2] or np.any(p['exposure']<=0) for p in [reference,candidate]):
        raise ValueError('Invalid modulation profile exposure')
    if not np.array_equal(reference['exposure'],candidate['exposure']): raise ValueError('Profile exposure differs')
    if any(not np.isfinite(x).all() or np.min(x)<0 for x in [a,ta,b,tb]): raise ValueError('Invalid profile powers')
    d,h,p,different=paired(a,b,.5)
    dl,hl,pl,different_level=paired(ta,tb,.1)
    meaningful=np.mean(a,axis=0)>=np.mean(ta,axis=0)[:,None,:]*1e-4
    verdict='pass' if np.all(p[meaningful]) and np.all(pl) else 'different' if np.any(different[meaningful]) or np.any(different_level) else 'inconclusive'
    return dict(kind='noise-control-conditioned-power-screen',verdict=verdict,
        band_margin_db=.5,level_margin_db=.1,confidence_multiplier=3.,meaningful_band_floor_db=-40,
        mean_paired_band_log_ratio_db=d.tolist(),band_interval_half_db=h.tolist(),meaningful_bands=meaningful.tolist(),
        mean_paired_level_log_ratio_db=dl.tolist(),level_interval_half_db=hl.tolist(),
        scope='256-frame Hann windows every128 frames, grouped by independently verified expected control value; paired two-second log-power differences with the existing short HAC uncertainty correction.')
