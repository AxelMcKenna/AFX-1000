"""Paired delta-method screens for verified identical control trajectories."""
import numpy as np
from tools.audio.noise.noise_statistics import mean_variance
from tools.audio.noise.noise_random_statistics import measure as profile_measure


def interval(reference,candidate,margin):
    a=np.mean(reference,axis=0);b=np.mean(candidate,axis=0)
    if np.any(a<=0) or np.any(b<=0):raise ValueError('Silent paired power')
    delta=10*np.log10(b/a)
    # Same ratio-of-mean-power estimand as the independent screen. Matching
    # trajectories justify retaining the cross-source covariance term.
    influence=candidate/b-reference/a
    half=3*(10/np.log(10))*np.sqrt(mean_variance(influence))
    return delta,half,np.abs(delta)+half<=margin,np.abs(delta)-half>margin


def measure(reference,candidate):
    a,ta,b,tb=reference['bands'],reference['total'],candidate['bands'],candidate['total']
    if a.shape!=b.shape or ta.shape!=tb.shape or a.shape!=(len(ta),30,2) or len(ta)<20:raise ValueError('Invalid paired extent')
    if any(not np.isfinite(v).all() or np.min(v)<0 for v in [a,ta,b,tb]):raise ValueError('Invalid paired powers')
    d,h,p,different=interval(a,b,.5);dl,hl,pl,ld=interval(ta,tb,.1)
    meaningful=np.mean(a,axis=0)>=np.mean(ta,axis=0)[None,:]*1e-4
    verdict='pass' if np.all(p[meaningful]) and np.all(pl) else 'different' if np.any(different[meaningful]) or np.any(ld) else 'inconclusive'
    return dict(kind='verified-trajectory-paired-delta-power-screen',verdict=verdict,band_margin_db=.5,level_margin_db=.1,confidence_multiplier=3.,meaningful_band_floor_db=-40,mean_power_ratio_db=d.tolist(),band_interval_half_db=h.tolist(),meaningful_bands=meaningful.tolist(),whole_level_ratio_db=dl.tolist(),whole_level_interval_half_db=hl.tolist(),scope='Ratio of mean powers; paired delta-method HAC variance includes cross-source covariance. Applicable only after verifying identical modulation trajectories; margins unchanged.')
