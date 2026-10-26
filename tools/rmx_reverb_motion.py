#!/usr/bin/env python3
"""Capture Reverb Down state changes; timing diagnostics are not full fidelity."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import controls
from tools.rmx_spiral_core import calibration

STAGES = ('button', 'steps', 'ramps', 'blocks')
HOLDOUT_STAGES = ('cutoff-holdout','sub1-holdout','activation-holdout','activation-v2-holdout','main-holdout','main-v2-holdout','startup-holdout','startup-v2-holdout','startup-v3-holdout','production-holdout','engine-holdout')
CAPTURE_STAGES = (*STAGES,*HOLDOUT_STAGES,'state-probes','button-probes','initialization-probes','callback-probes')
NAMES = {'main':'SceneVolume','amount':'Sub1Volume','cutoff':'Sub2Volume','enabled':'ReverbDownButto'}


def recipe(stage):
    rng = np.random.default_rng(0x2C170)
    t = np.arange(288000)/48000
    continuous = np.zeros((384000,2))
    continuous[48000:336000] = rng.normal(0,.022,(288000,2))
    continuous[48000:336000] += .018*np.column_stack((np.sin(2*np.pi*233*t)+np.sin(2*np.pi*1000*t),
                                                    np.sin(2*np.pi*711*t)+np.cos(2*np.pi*2651*t)))
    burst = continuous.copy()
    burst[144000:240000] = 0
    tones = np.zeros_like(continuous)
    tones[48000:336000] = .025*np.column_stack((np.sin(2*np.pi*233*t)+np.sin(2*np.pi*1000*t),
                                              np.sin(2*np.pi*711*t)+np.cos(2*np.pi*2651*t)))
    pulses = np.zeros_like(continuous)
    pulses[48000,0],pulses[144000,1],pulses[300000,0] = .02,-.017,.013
    waves = dict(continuous=continuous,burst=burst,tones=tones,pulses=pulses)
    cases = []
    event_frame = 192037

    def add(name,source='burst',main=128,amount=128,cutoff=0,enabled=1,events=None,block=128,tail=None,baseline=None):
        events = events or []
        high = max([amount]+[e['value'] for e in events if e['control']=='amount'])
        cases.append(dict(name='down-'+name,source=source,direction='down',main=main,amount=amount,cutoff=cutoff,
            enabled=enabled,events=events,block=block,tail=tail if tail is not None else (90 if high>=224 else 18),baseline=baseline))

    if stage == 'button':
        for main in (128,255):
            for source in ('burst','continuous'):
                base=f'down-baseline-{source}-{main}'
                add(f'baseline-{source}-{main}',source,main)
                add(f'off-on-{source}-{main}',source,main,events=[dict(frame=event_frame,control='enabled',value=0),
                    dict(frame=288073,control='enabled',value=1)],baseline=base)
            for source in ('continuous','pulses'):
                add(f'initial-off-{source}-{main}',source,main,enabled=0,
                    events=[dict(frame=event_frame,control='enabled',value=1),dict(frame=336091,control='enabled',value=0)])
    elif stage == 'steps':
        transitions = [('main',a,b) for a,b in ((128,192),(192,128),(64,224),(224,64),(128,0),(0,128),(143,144))]
        transitions += [('amount',a,b) for a,b in ((64,224),(224,64),(128,255),(255,0))]
        transitions += [('cutoff',a,b) for a,b in ((0,192),(192,0),(77,241),(241,77))]
        for control,start,end in transitions:
            values=dict(main=128,amount=128,cutoff=0)
            values[control]=start
            source='continuous' if control=='main' and (start,end) in ((128,192),(192,128)) else 'burst'
            add(f'step-{control}-{start}-{end}',source,**values,events=[dict(frame=event_frame,control=control,value=end)])
        add('step-combined-forward','continuous',events=[dict(frame=event_frame,control=k,value=v)
            for k,v in (('main',177),('amount',229),('cutoff',139))])
        add('step-combined-reverse','burst',main=177,amount=229,cutoff=139,events=[dict(frame=event_frame,control=k,value=v)
            for k,v in (('main',128),('amount',128),('cutoff',0))])
    elif stage == 'ramps':
        for control,low,high in (('main',32,224),('amount',32,224),('cutoff',0,255)):
            for start,end in ((low,high),(high,low)):
                values=dict(main=128,amount=128,cutoff=0)
                values[control]=start
                events=[dict(frame=144013+i*1500,control=control,value=int(raw))
                        for i,raw in enumerate(np.rint(np.linspace(start,end,64)).astype(int))]
                add(f'ramp-{control}-{start}-{end}','tones',**values,events=events)
    elif stage == 'blocks':
        for block in (32,256):
            for control in ('main','cutoff'):
                add(f'step-{control}-block-{block}','continuous' if control=='main' else 'burst',block=block,
                    events=[dict(frame=event_frame,control=control,value=192)],
                    baseline=f'steps/down-step-{control}-128-192' if control=='main' else 'steps/down-step-cutoff-0-192')
            add(f'off-on-block-{block}','continuous',main=255,block=block,
                events=[dict(frame=event_frame,control='enabled',value=0),dict(frame=288073,control='enabled',value=1)],
                baseline='button/down-off-on-continuous-255')
    elif stage in ('startup-holdout','startup-v2-holdout','startup-v3-holdout'):
        v2=stage=='startup-v2-holdout'
        v3=stage=='startup-v3-holdout'
        program=np.zeros((480000,2))
        program[:456000]=np.random.default_rng(0x5A1031 if v3 else 0x5A1029 if v2 else 0x5A1027).normal(0,.017,(456000,2))
        t=np.arange(456000)/48000
        program[:456000]+=.008*np.column_stack((np.sin(2*np.pi*(157*t+31*t*t)),np.cos(2*np.pi*1193*t)))
        gap=program.copy();gap[144000:264000]=0
        pulses=np.zeros_like(program)
        locations=[0,17,31,32,127,128,159,160,719,12001,24017,48031,96019,192067,288071,384079]
        if v2:locations=[0,7,31,32,67,95,127,128,159,160,1023,11937,12381,12417,12503,24037,48059,96101,192113,288119]
        if v3:locations=[0,3,17,31,33,97,127,129,157,161,701,11819,12373,12437,12539,24113,48139,96143,192157,288163]
        pulses[locations]=np.random.default_rng(0x5A1032 if v3 else 0x5A1030 if v2 else 0x5A1028).uniform(-.024,.024,(len(locations),2))
        waves=dict(startup_program=program,startup_gap=gap,startup_pulses=pulses)
        specs=[(128,97,19,1,'startup_program',128,[(96013,'main',129),(192019,'enabled',0),(192211,'enabled',1)]),
            (255,239,160,1,'startup_gap',16,[(96017,'main',0),(240019,'main',255)]),
            (211,207,96,1,'startup_program',63,[(17,'main',47),(48031,'main',183),(96111,'cutoff',224)]),
            (143,1,5,1,'startup_pulses',17,[(31,'main',144),(12011,'main',143)]),
            (0,83,241,1,'startup_program',33,[(32,'main',4),(24043,'main',129),(96037,'main',0),(192047,'main',128)]),
            (177,221,77,0,'startup_program',256,[(17,'main',61),(63,'amount',17),(95,'cutoff',224),
                (12013,'enabled',1),(96031,'main',211),(96031,'amount',247),(96031,'cutoff',32),
                (120037,'enabled',0),(144043,'enabled',1)]),
            (64,128,255,0,'startup_program',8,[(5,'main',255),(61,'enabled',1),(96013,'main',47)]),
            (129,137,32,1,'startup_program',31,[(17,'enabled',0),(63,'enabled',1),(95,'enabled',0),
                (327,'enabled',1),(24011,'main',197),(96013,'amount',239),(144019,'main',0)])]
        if v2:
            specs=[(144,2,19,1,'startup_pulses',15,[(63,'main',143),(11871,'main',144),(12813,'main',143)]),
                (1,97,250,1,'startup_program',47,[(32,'main',5),(23991,'main',117),(96111,'main',0),(191223,'main',131)]),
                (130,149,47,1,'startup_program',9,[(23,'enabled',0),(95,'enabled',1),(127,'enabled',0),
                    (379,'enabled',1),(24139,'main',211),(96713,'amount',231),(144197,'main',2)]),
                (219,239,111,0,'startup_program',255,[(17,'main',79),(61,'amount',13),(93,'cutoff',241),(129,'enabled',1),
                    (12719,'main',197),(14513,'main',83),(119117,'enabled',0),(144173,'enabled',1)]),
                (0,7,192,1,'startup_pulses',129,[(31,'main',4),(10013,'main',1),(12247,'main',5),(14519,'main',143)]),
                (128,3,5,1,'startup_program',32,[(31,'amount',255),(12013,'amount',0),(12617,'amount',239)]),
                (255,223,77,1,'startup_gap',16,[(17,'main',61),(127,'main',203),(503,'main',47),(11807,'main',211),
                    (12101,'amount',0),(12203,'cutoff',255)]),
                (79,128,32,0,'startup_program',64,[(5,'enabled',1),(17,'enabled',0),(23,'enabled',1),(31,'enabled',0),
                    (63,'enabled',1),(95,'enabled',0),(111,'main',157),(191,'enabled',1)])]
        if v3:
            specs=[(130,137,19,1,'startup_program',128,[(96013,'main',133),(192019,'enabled',0),(192237,'enabled',1)]),
                (133,149,95,1,'startup_program',31,[(29,'enabled',0),(97,'enabled',1),(159,'enabled',0),(443,'enabled',1),
                    (24091,'main',199),(96713,'amount',239),(144197,'cutoff',224)]),
                (136,3,241,0,'startup_program',15,[(7,'main',133),(73,'enabled',1),(111,'enabled',0),(207,'enabled',1),
                    (503,'main',138),(24037,'main',147)]),
                (138,239,111,1,'startup_gap',47,[(17,'main',141),(11803,'main',224),(12137,'amount',7),
                    (12277,'cutoff',5),(96043,'main',248)]),
                (147,1,47,1,'startup_pulses',9,[(32,'main',150),(11837,'main',147),(12899,'main',156)]),
                (192,207,160,1,'startup_program',32,[(31,'amount',255),(11973,'amount',0),(12739,'amount',247),
                    (14519,'main',194),(96067,'main',198)]),
                (224,223,77,0,'startup_program',255,[(17,'main',229),(63,'amount',17),(95,'cutoff',224),(159,'enabled',1),
                    (12689,'main',230),(96037,'main',0),(192017,'main',242)]),
                (248,128,32,1,'startup_program',16,[(17,'enabled',0),(65,'enabled',1),(113,'enabled',0),(431,'enabled',1),
                    (24139,'main',242),(96121,'main',130),(144173,'amount',3)])]
        for i,(main,amount,cutoff,enabled,source,block,events) in enumerate(specs):
            high=max([amount]+[v for _,k,v in events if k=='amount'])
            add(f'{stage}-{i}',source,main,amount,cutoff,enabled,block=block,tail=90 if high>=192 else 18,
                events=[dict(frame=n,control=k,value=v) for n,k,v in events])
    elif stage == 'production-holdout':
        # New signals and gestures frozen before original capture. Large host
        # blocks stress the bounded processor beyond the earlier <=256 set.
        program=np.random.default_rng(0xB10C1027).normal(0,.016,(432000,2))
        t=np.arange(len(program))/48000
        program+=.009*np.column_stack((np.sin(2*np.pi*(181*t+23*t*t)),np.cos(2*np.pi*1627*t)))
        program[168000:216000]=0
        pulses=np.zeros_like(program)
        locations=[0,11,31,32,163,511,1023,2047,4095,12017,12397,12553,48017,96199,192239,288271]
        pulses[locations]=np.random.default_rng(0xB10C1028).uniform(-.023,.023,(len(locations),2))
        waves=dict(block_program=program,block_pulses=pulses)
        specs=[(131,97,19,1,'block_program',511,[(96019,'main',137),(192239,'enabled',0),(192499,'enabled',1)]),
            (199,149,95,1,'block_program',1024,[(13,'main',61),(12037,'cutoff',224),(48047,'amount',173)]),
            (230,207,160,0,'block_program',2048,[(19,'main',79),(67,'amount',17),(101,'enabled',1),
                (12683,'main',211),(96053,'enabled',0),(120127,'enabled',1)]),
            (255,239,77,1,'block_program',4096,[(96073,'main',47),(192293,'main',255),(288307,'cutoff',241)]),
            (144,7,47,1,'block_pulses',511,[(29,'main',143),(11897,'main',144),(12937,'main',147)]),
            (130,137,192,1,'block_program',1024,[(23,'enabled',0),(79,'enabled',1),(139,'enabled',0),
                (467,'enabled',1),(24193,'main',194),(96139,'amount',231)]),
            (0,83,250,1,'block_program',2048,[(32,'main',5),(24179,'main',131),(96731,'main',0),(192313,'main',138)]),
            (248,223,32,0,'block_pulses',4096,[(7,'enabled',1),(37,'enabled',0),(103,'enabled',1),
                (12359,'amount',3),(12871,'cutoff',255),(48097,'main',242)])]
        for i,(main,amount,cutoff,enabled,source,block,events) in enumerate(specs):
            high=max([amount]+[v for _,k,v in events if k=='amount'])
            add(f'{stage}-{i}',source,main,amount,cutoff,enabled,block=block,tail=90 if high>=192 else 18,
                events=[dict(frame=n,control=k,value=v) for n,k,v in events])
    elif stage == 'engine-holdout':
        program=np.random.default_rng(0xE0611027).normal(0,.015,(456000,2))
        t=np.arange(len(program))/48000
        program+=.007*np.column_stack((np.sin(2*np.pi*(223*t+29*t*t)),np.cos(2*np.pi*1877*t)))
        program[192000:264000]=0
        pulses=np.zeros_like(program)
        locations=[0,13,31,33,173,509,1031,2053,4093,12023,12403,12569,48113,96217,192323,288367]
        pulses[locations]=np.random.default_rng(0xE0611028).uniform(-.021,.021,(len(locations),2))
        waves=dict(engine_program=program,engine_pulses=pulses)
        specs=[(137,97,19,1,'engine_program',8,[(96029,'main',141),(192337,'enabled',0),(192647,'enabled',1)]),
            (194,149,95,1,'engine_program',17,[(11,'main',67),(12043,'cutoff',229),(48061,'amount',177)]),
            (242,207,160,0,'engine_program',31,[(17,'main',83),(71,'amount',19),(109,'enabled',1),
                (12697,'main',203),(96079,'enabled',0),(120163,'enabled',1)]),
            (252,239,77,1,'engine_program',128,[(96097,'main',53),(192353,'main',248),(288373,'cutoff',239)]),
            (143,7,47,1,'engine_pulses',511,[(37,'main',144),(11909,'main',143),(12959,'main',150)]),
            (133,137,192,1,'engine_program',1024,[(31,'enabled',0),(83,'enabled',1),(149,'enabled',0),
                (487,'enabled',1),(24223,'main',198),(96169,'amount',229)]),
            (1,83,250,1,'engine_program',2048,[(32,'main',4),(24203,'main',138),(96769,'main',2),(192379,'main',136)]),
            (229,223,32,0,'engine_pulses',4096,[(11,'enabled',1),(43,'enabled',0),(107,'enabled',1),
                (12377,'amount',1),(12893,'cutoff',254),(48119,'main',230)])]
        for i,(main,amount,cutoff,enabled,source,block,events) in enumerate(specs):
            high=max([amount]+[v for _,k,v in events if k=='amount'])
            add(f'{stage}-{i}',source,main,amount,cutoff,enabled,block=block,tail=90 if high>=192 else 18,
                events=[dict(frame=n,control=k,value=v) for n,k,v in events])
    elif stage == 'callback-probes':
        program=np.random.default_rng(0xCB1027).normal(0,.019,(96000,2))
        waves=dict(callback_program=program)
        for block in (8,16,17,31,32,33,63,64,128,256):
            add(f'callback-off-block-{block}','callback_program',enabled=0,block=block,tail=.1)
        for block in (8,16,31,32,33,128):
            add(f'callback-active-block-{block}','callback_program',block=block,tail=6)
        for frame in (5,17,31,32,33,63,65):
            add(f'callback-noop-{frame}','callback_program',enabled=0,tail=6,
                events=[dict(frame=frame,control='main',value=128),dict(frame=48013,control='enabled',value=1)])
    elif stage == 'initialization-probes':
        source=np.zeros((192000,2))
        source[:96000]=np.random.default_rng(0x1A177).normal(0,.019,(96000,2))
        waves=dict(initial_program=source)
        for main in (128,255):
            add(f'initialization-main-{main}','initial_program',main=main)
    elif stage in ('activation-holdout','activation-v2-holdout'):
        v2=stage=='activation-v2-holdout'
        fresh=np.zeros((432000,2))
        fresh[12000:408000]=np.random.default_rng(0xAC716 if v2 else 0xAC714).normal(0,.017,(396000,2))
        t=np.arange(396000)/48000
        fresh[12000:408000]+=.011*np.column_stack((np.sin(2*np.pi*(271*t+41*t*t)),
                                                  np.cos(2*np.pi*1481*t)+np.sin(2*np.pi*97*t)))
        gap=fresh.copy();gap[144000:240000]=0
        long=np.zeros((1440000,2))
        long[12000:1416000]=np.random.default_rng(0xAC717 if v2 else 0xAC715).normal(0,.014,(1404000,2))
        pulses=np.zeros_like(fresh)
        pulses[[24000,48051,96007,144071,192019,240017,360013]]=[[.021,0],[0,-.019],[.017,.011],[-.015,.023],[.012,0],[.019,-.013],[0,.016]]
        waves=dict(activation_program=fresh,activation_gap=gap,activation_pulses=pulses,activation_long=long)
        specs=[(47,83,19,0,'activation_program',32,[(96013,1),(120059,0),(144071,1)]),
            (203,221,77,1,'activation_program',256,[(96013,0),(96109,1),(192019,0),(192303,1)]),
            (128,3,241,0,'activation_program',128,[(72001,1),(72097,0),(72241,1),(192013,0)]),
            (255,254,138,0,'activation_program',32,[(96013,1),(96077,0),(96269,1),(98031,0),(100111,1)]),
            (64,96,255,1,'activation_pulses',256,[(48049,0),(48095,1),(144019,0),(144303,1)]),
            (176,223,95,0,'activation_gap',128,[(144019,1),(145111,0),(192071,1),(288013,0)]),
            (143,241,0,1,'activation_long',32,[(96013,0),(1248007,1)]),
            (129,128,77,0,'activation_program',256,[(17,1),(23,0),(49,1),(64,0),(96,1),(160,0),(327,1),(96013,0),(96191,1)])]
        if v2:
            pulses=np.zeros_like(fresh)
            pulses[[24317,48368,96324,144388,192336,240334,360330]]=[[.019,0],[0,-.021],[.013,.017],[-.023,.015],[.016,0],[.011,-.019],[0,.018]]
            waves['activation_pulses']=pulses
            specs=[(61,97,32,0,'activation_program',128,[(72017,1),(96191,0),(120223,1)]),
                (211,207,96,1,'activation_program',32,[(120019,0),(120127,1),(192023,0),(192319,1)]),
                (128,1,224,0,'activation_program',256,[(48011,1),(48139,0),(48333,1),(192017,0)]),
                (255,239,160,0,'activation_program',128,[(120019,1),(120083,0),(120275,1),(122037,0),(124117,1)]),
                (79,128,250,1,'activation_pulses',32,[(48061,0),(48107,1),(144023,0),(144319,1)]),
                (183,192,111,0,'activation_gap',256,[(144013,1),(145127,0),(192083,1),(288019,0)]),
                (157,223,15,1,'activation_long',128,[(120019,0),(1296005,1)]),
                (130,137,95,0,'activation_program',32,[(31,1),(32,0),(63,1),(96,0),(128,1),(224,0),(411,1),(120019,0),(120223,1)])]
        for i,(main,amount,cutoff,enabled,source,block,events) in enumerate(specs):
            add(f'{stage}-{i}',source,main,amount,cutoff,enabled,block=block,tail=90 if amount>=192 else 18,
                events=[dict(frame=frame,control='enabled',value=value) for frame,value in events])
    elif stage == 'button-probes':
        waves={}
        for offset in (0,32,64,128,192,256):
            source=f'gate-pulse-{offset}'
            pulse=np.zeros_like(continuous);pulse[event_frame+offset,0]=.02
            waves[source]=pulse
            baseline=f'down-gate-baseline-{offset}'
            add(f'gate-baseline-{offset}',source)
            add(f'gate-off-{offset}',source,events=[dict(frame=event_frame,control='enabled',value=0)],baseline=baseline)
            add(f'gate-on-{offset}',source,events=[dict(frame=event_frame-48000,control='enabled',value=0),
                dict(frame=event_frame,control='enabled',value=1)],baseline=baseline)
    elif stage == 'state-probes':
        dry=np.zeros_like(continuous)
        dry[event_frame-128:event_frame+256]=np.random.default_rng(0xD029).normal(0,.02,(384,2))
        late=np.zeros_like(continuous);late[event_frame+48000]=[.02,0]
        waves=dict(dry=dry,late=late)
        for start,end in ((128,192),(192,128),(255,0),(0,255),(143,144),(144,143)):
            add(f'dry-main-{start}-{end}','dry',main=start,
                events=[dict(frame=event_frame,control='main',value=end)])
        for main in (128,255):
            for offset in (64,4096,12000):
                name=f'on-pulse-{offset}'
                pulse=np.zeros_like(continuous);pulse[event_frame+offset]=[.02,0]
                waves[name]=pulse
                add(f'initial-off-{main}-pulse-{offset}',name,main=main,enabled=0,
                    events=[dict(frame=event_frame,control='enabled',value=1)])
        for main in (0,128,192):
            add(f'settled-main-baseline-{main}','late',main=main)
        for start,end in ((0,128),(128,0),(128,192),(192,128)):
            add(f'settled-main-{start}-{end}','late',main=start,
                events=[dict(frame=event_frame,control='main',value=end)],
                baseline=f'down-settled-main-baseline-{end}')
        for amount in (0,64,224,255):
            add(f'settled-amount-baseline-{amount}','late',amount=amount)
        for start,end in ((64,224),(224,64),(128,255),(255,0)):
            add(f'settled-amount-{start}-{end}','late',amount=start,
                events=[dict(frame=event_frame,control='amount',value=end)],
                baseline=f'down-settled-amount-baseline-{end}')
    elif stage in ('main-holdout','main-v2-holdout'):
        v2=stage=='main-v2-holdout'
        fresh=np.zeros((480000,2))
        fresh[12000:456000]=np.random.default_rng(0x4A1C28 if v2 else 0x4A1C27).normal(0,.016,(444000,2))
        t=np.arange(444000)/48000
        fresh[12000:456000]+=.009*np.column_stack((np.sin(2*np.pi*(193*t+67*t*t)),
                                                   np.cos(2*np.pi*1427*t)+np.sin(2*np.pi*83*t)))
        gap=fresh.copy();gap[144000:264000]=0
        pulses=np.zeros_like(fresh)
        pulses[[24017,96029,120101,144107,192023,264019,384031]]=[
            [.019,0],[0,-.023],[.011,.017],[-.021,.013],[.016,0],[.015,-.019],[0,.021]]
        if v2:pulses=np.roll(pulses,173,axis=0)
        waves=dict(main_program=fresh,main_gap=gap,main_pulses=pulses)
        specs=[(31,87,19,1,'main_program',32,[(96013,'main',247),(96143,'main',19),(144031,'main',211)]),
            (223,239,77,1,'main_gap',256,[(144019,'main',12),(288037,'main',199)]),
            (0,128,241,1,'main_program',128,[(72000,'main',3),(96032,'main',4),(120064,'main',0),(144096,'main',128)]),
            (143,47,0,1,'main_pulses',32,[(96013,'main',144),(120019,'main',143),(144023,'main',144)]),
            (255,32,95,1,'main_program',256,[(96017,'main',0),(240031,'main',255)]),
            (64,201,223,1,'main_gap',128,[(96013,'main',219),(96013,'amount',17),(96013,'cutoff',32),
                (144019,'main',83),(144019,'amount',247),(144019,'cutoff',111)]),
            (176,7,138,1,'main_program',32,[(96013,'main',129),(97019,'amount',255),(192031,'amount',3),
                (240043,'main',183),(240043,'amount',128)]),
            (129,177,32,0,'main_program',256,[(31,'main',61),(48013,'enabled',1),(96017,'main',203),
                (120019,'enabled',0),(144023,'main',1),(192031,'enabled',1),(240037,'main',157)])]
        if v2:
            specs=[(47,99,32,1,'main_program',128,[(72019,'main',231),(72241,'main',23),(144071,'main',197)]),
                (211,223,96,1,'main_gap',32,[(144031,'main',7),(288059,'main',183)]),
                (1,137,224,1,'main_program',256,[(72032,'main',3),(96064,'main',4),(120096,'main',0),(144128,'main',117)]),
                (144,61,15,1,'main_pulses',128,[(96029,'main',143),(120037,'main',144),(144043,'main',143)]),
                (251,47,111,1,'main_program',32,[(96191,'main',0),(240223,'main',255)]),
                (79,207,192,1,'main_gap',256,[(96029,'main',203),(96029,'amount',31),(96029,'cutoff',19),
                    (144037,'main',97),(144037,'amount',239),(144037,'cutoff',128)]),
                (183,1,160,1,'main_program',128,[(96031,'main',130),(97111,'amount',247),(192063,'amount',4),
                    (240079,'main',176),(240079,'amount',137)]),
                (130,161,47,1,'main_program',32,[(96031,'main',197),(120037,'enabled',0),(144043,'main',3),
                    (192071,'enabled',1),(240101,'main',143)])]
        for i,(main,amount,cutoff,enabled,source,block,events) in enumerate(specs):
            high=max([amount]+[v for _,k,v in events if k=='amount'])
            add(f'{stage}-{i}',source,main,amount,cutoff,enabled,block=block,tail=90 if high>=192 else 18,
                events=[dict(frame=n,control=k,value=v) for n,k,v in events])
    elif stage == 'sub1-holdout':
        fresh=np.zeros((288000,2))
        fresh[24000:264000]=np.random.default_rng(0xA18C7).normal(0,.019,(240000,2))
        t=np.arange(240000)/48000
        fresh[24000:264000]+=.013*np.column_stack((np.sin(2*np.pi*(317*t+73*t*t)),
                                                  np.cos(2*np.pi*1129*t)+np.sin(2*np.pi*79*t)))
        gap=fresh.copy();gap[96000:192000]=0
        pulses=np.zeros_like(fresh)
        pulses[[24000,96007,120111,192019,240017]]=[[.021,0],[0,-.019],[.017,.011],[-.015,.023],[.012,0]]
        waves=dict(sub1_program=fresh,sub1_gap=gap,sub1_pulses=pulses)
        specs=[(37,91,0,'sub1_program',32,[(96013,239),(96109,13),(144019,177)]),
            (221,230,19,'sub1_program',256,[(96013,19),(144013,247)]),
            (128,3,77,'sub1_program',128,[(72001,4),(72045,0),(120013,3)]),
            (255,254,138,'sub1_program',32,[(96013,255),(96077,250),(144031,0)]),
            (64,96,241,'sub1_pulses',256,[(48049,97),(48095,95),(192019,201)]),
            (176,223,255,'sub1_gap',128,[(144019,9),(145111,201),(192071,0)]),
            (143,241,95,'sub1_pulses',32,[(96013,128),(100019,241),(192013,255)]),
            (129,128,0,'sub1_program',256,[(96013+i*750,int(raw)) for i,raw in enumerate(np.rint(np.linspace(128,224,40)))])]
        for i,(main,amount,cutoff,source,block,events) in enumerate(specs):
            high=max([amount]+[value for _,value in events])
            add(f'sub1-holdout-{i}',source,main,amount,cutoff,block=block,tail=90 if high>=192 else 18,
                events=[dict(frame=frame,control='amount',value=value) for frame,value in events])
    elif stage == 'cutoff-holdout':
        fresh=np.zeros((288000,2))
        fresh[24000:264000]=np.random.default_rng(0xC039A7).normal(0,.019,(240000,2))
        t=np.arange(240000)/48000
        fresh[24000:264000]+=.012*np.column_stack((np.sin(2*np.pi*(173*t+180*t*t)),
                                                  np.cos(2*np.pi*1831*t)+np.sin(2*np.pi*61*t)))
        gap=fresh.copy();gap[96000:192000]=0
        pulses=np.zeros_like(fresh)
        pulses[[24000,96007,120111,192019,240017]]=[[.025,0],[0,-.017],[.013,.009],[-.019,.021],[.01,0]]
        waves=dict(fresh=fresh,gap=gap,pulses=pulses)
        specs=[(47,83,5,'fresh',32,[(120013,255),(121249,0),(144017,91)]),
            (203,221,180,'fresh',256,[(96013,64),(96109,90),(144071,250)]),
            (129,161,1,'fresh',128,[(72001,4),(72045,5),(120013,3)]),
            (255,37,254,'fresh',32,[(96013,255),(96077,250),(144031,0)]),
            (64,224,96,'pulses',256,[(48049,97),(48095,95),(192019,201)]),
            (176,0,223,'gap',128,[(144019,9),(145111,201),(192071,0)]),
            (128,128,0,'fresh',256,[(96013,192),(96111,224),(96143,223),(144197,77)]),
            (143,255,241,'pulses',32,[(96013,1),(120013,241),(192013,255)])]
        for i,(main,amount,cutoff,source,block,events) in enumerate(specs):
            add(f'cutoff-holdout-{i}',source,main,amount,cutoff,block=block,
                events=[dict(frame=frame,control='cutoff',value=value) for frame,value in events])
    else:
        raise ValueError('Unknown motion stage')
    if stage in ('steps','ramps'):
        # A separately rendered original baseline for every initial state/source.
        baselines={}
        for c in cases:
            key=tuple(c[k] for k in ('source','main','amount','cutoff','enabled'))
            if key not in baselines:
                name='down-baseline-'+str(len(baselines))
                baselines[key]=c|dict(name=name,events=[],baseline=None)
            baselines[key]['tail']=max(baselines[key]['tail'],c['tail'])
            c['baseline']=baselines[key]['name']
        cases=[*baselines.values(),*cases]
    return waves,cases


def parameters(case):
    return controls(case)|{'ReverbDownButto':case['enabled']}


def event_values(case):
    return [dict(frame=e['frame'],name=NAMES[e['control']],value=e['value'] if e['control']=='enabled' else e['value']/255)
            for e in case['events']]


def candidate_sources():
    repo=Path(__file__).resolve().parents[1]
    return [Path(__file__),repo/'tools/reverb_down_probe.cpp',repo/'CMakeLists.txt',
            *sorted((repo/'include/rmx').glob('*.h')),*sorted((repo/'src/core').glob('*.cpp')),
            repo/'src/plugin/Plugin.cpp',repo/'src/macos/AudioHost.h',repo/'src/macos/AudioHost.mm']


def prediction_payload(stage):
    waves,cases=recipe(stage)
    repo=Path(__file__).resolve().parents[1]
    paths=candidate_sources()
    return dict(stage=stage,cases=cases,backend='engine' if stage=='engine-holdout' else 'core',source_files_sha256={str(p.relative_to(repo)):sha256(p) for p in paths},
        source_samples_sha256={name:hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for name,x in waves.items()})


def prediction_kind(stage):
    return 'rmx220-reverb-down-'+stage.removesuffix('-holdout')+'-motion-predictions'


def predicted_config(stage):
    # All current prospective stages target the bounded production processor.
    # Earlier experimental configurations remain in their source checkpoints.
    return dict(gate='faded',cutoff_position='post',gain_position='read',control_quantum=32,
        candidate_latency=32,level_position='output',coefficient_ramp_frames=0,
        ramp_components='startup',decay_step_per_32_frames=0)


def predict(args):
    calibration(args.calibration)
    payload=prediction_payload(args.stage)
    save_json(args.report,dict(kind=prediction_kind(args.stage),**payload,
        model_path=str(args.model.resolve()),model_sha256=sha256(args.model),
        renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),
        calibration_sha256=sha256(args.calibration),candidate_config=predicted_config(args.stage),
        expected='All eight complete renders pass whole/wet/tail, every event window and applicable activation-start windows at relative RMS <=0.01.',
        scope=('Complete Engine path at factory Down settings, audio from frame zero, callbacks 8..4096, new programs and early/late controls; no sampler/Isolator/Release, MCU deadline or cross-profile claim.' if args.stage=='engine-holdout'
               else 'Bounded core processor, audio from frame zero, 511/1024/2048/4096-frame callbacks, new programs and early/late controls. Not live Engine routing or MCU deadline validation.' if args.stage=='production-holdout'
               else 'Audio begins at frame zero; callback sizes, early events, initial active/inactive states and simultaneous control changes vary. Fixed comparison offsets remain 32 frames.' if args.stage.startswith('startup-')
               else 'Main moves after active initialization, including simultaneous Sub1/Sub2 and later button changes; immediate-input and pre-activation Main failures remain separate regressions.' if args.stage=='main-v2-holdout'
               else 'Main moves, including simultaneous Sub1/Sub2 and button changes; initial active/inactive states vary.' if args.stage=='main-holdout'
               else 'Only the enabled button moves; Main/Sub1/Sub2 stay fixed. Initial active/inactive states vary.' if args.stage.startswith('activation-')
               else 'Only '+('Sub1' if args.stage=='sub1-holdout' else 'Sub2')+' moves; other controls stay fixed and the effect starts enabled.')))


def capture(args):
    calibration(args.calibration)
    if args.stage in HOLDOUT_STAGES:
        if args.prediction is None:
            raise ValueError('Fresh holdout capture requires frozen prospective predictions')
        prediction=json.loads(args.prediction.read_text())
        if (prediction.get('kind')!=prediction_kind(args.stage)
                or any(prediction.get(k)!=v for k,v in prediction_payload(args.stage).items())
                or prediction.get('candidate_config')!=predicted_config(args.stage)
                or prediction['calibration_sha256']!=sha256(args.calibration)
                or any(sha256(Path(prediction[k+'_path']))!=prediction[k+'_sha256'] for k in ('model','renderer'))):
            raise ValueError('Prediction recipe/model/source/renderer/calibration differs')
    elif args.prediction is not None:
        raise ValueError('Predictions apply only to fresh holdout stages')
    root=new_directory(args.session)
    if args.prediction is not None:
        (root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]))
    if any(inventory[k]!=v for k,v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json',inventory)
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name]
        if len(matches)!=1:
            raise ValueError('Missing or ambiguous control: '+name)
        return {k:matches[0][k] for k in ('index','id','name')}|{'value':value}
    waves,cases=recipe(args.stage)
    for name,x in waves.items():
        write_wav(root/(name+'.wav'),48000,x.ravel())
    for c in cases:
        events=[setting(e['name'],e['value'])|dict(frame=e['frame'],type='parameter') for e in event_values(c)]
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,
            sample_rate=48000,bpm=120,tail_seconds=c['tail'],parameters=[setting(k,v) for k,v in parameters(c).items()],events=events)
        save_json(root/(c['name']+'.json'),plan)
        run([args.host,'render',args.plugin,root/(c['source']+'.wav'),root/(c['name']+'.json'),root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json')
        print(c['name'],flush=True)
    save_json(root/'matrix.json',dict(kind='rmx220-reverb-down-motion-captures',stage=args.stage,cases=cases,
        calibration_sha256=sha256(args.calibration),capture_script_sha256=sha256(Path(__file__)),
        prediction_sha256=sha256(args.prediction) if args.prediction else None))


def checked(session,case,source):
    folder=session/case['name']
    receipt=json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role']!='reference'
            or any(receipt['plugin'][k]!=v for k,v in IDENTITY.items())):
        raise ValueError('Wrong reference: '+str(folder))
    for path,key in ((folder/'audio.wav','output_sha256'),(folder/'plan.json','plan_sha256'),(Path(receipt['input_path']),'input_sha256')):
        if sha256(path)!=receipt[key]:
            raise ValueError('Modified capture: '+str(path))
    plan=json.loads((folder/'plan.json').read_text())
    actual={p['name']:p['value'] for p in plan['parameters']}
    events=[{k:e[k] for k in ('frame','name','value')} for e in plan['events']]
    if (actual!=parameters(case) or events!=event_values(case) or any(e['type']!='parameter' for e in plan['events'])
            or plan['sample_rate']!=48000 or plan['bpm']!=120 or plan['tail_seconds']!=case['tail']
            or receipt['maximum_block_size']!=case['block']):
        raise ValueError('Outside exact motion recipe: '+str(folder))
    rate,audio=float_wav(folder/'audio.wav')
    input_rate,x=float_wav(Path(receipt['input_path']))
    if (rate!=48000 or input_rate!=rate or not np.array_equal(x,source.astype(np.float32))
            or len(audio)!=len(x)+case['tail']*48000):
        raise ValueError('Motion sample/rate/extent differs')
    manifest=json.loads((session/'matrix.json').read_text())
    stored=next(c for c in manifest['cases'] if c['name']==case['name'])
    if stored['receipt_sha256']!=sha256(folder/'receipt.json'):
        raise ValueError('Receipt differs from manifest')
    provenance=dict(case=case['name'],receipt_sha256=sha256(folder/'receipt.json'),input_sha256=receipt['input_sha256'],
        output_sha256=receipt['output_sha256'],plan_sha256=receipt['plan_sha256'])
    return audio.astype(float),x,provenance


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves,cases=recipe(args.stage)
    rows=[checked(args.session,c,waves[c['source']])[2] for c in cases]
    save_json(args.report,dict(kind='rmx220-reverb-down-motion-recipe-verification',stage=args.stage,passed=True,cases=rows,
        script_sha256=sha256(Path(__file__)),scope='Exact samples, controls/events, host block, extent and provenance only.'))
    print('Verified',len(rows),args.stage,'recipes')


def analyze(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    findings={}
    for stage in STAGES:
        session=getattr(args,stage)
        waves,cases=recipe(stage)
        records={c['name']:checked(session,c,waves[c['source']]) for c in cases}
        rows=[]
        for c in cases:
            audio,x,provenance=records[c['name']]
            row=provenance|dict(events=c['events'],block=c['block'],initial=parameters(c))
            if c['baseline']:
                if '/' in c['baseline']:
                    other,name=c['baseline'].split('/',1)
                    ow,oc=recipe(other)
                    baseline=next(b for b in oc if b['name']==name)
                    before,_,baseprov=checked(getattr(args,other),baseline,ow[baseline['source']])
                else:
                    before,_,baseprov=records[c['baseline']]
                length=min(len(audio),len(before))
                changed=np.flatnonzero(np.any(audio[:length]!=before[:length],axis=1))
                row['baseline']=baseprov
                row['baseline_comparison_overlap_frames']=length
                row['baseline_total_frames']=len(before)
                row['bit_exact_to_baseline']=bool(not len(changed))
                row['first_different_output_frame']=int(changed[0]) if len(changed) else None
                row['first_different_frame_after_bypass_offset']=int(changed[0])-32 if len(changed) else None
                if c['events'] and len(changed):
                    row['difference_relative_to_first_event_after_bypass_offset']=int(changed[0])-32-c['events'][0]['frame']
                row['post_input_tail_vs_baseline']=screen(before[len(x):length],audio[len(x):length])
                if c['events']:
                    at=c['events'][0]['frame']
                    row['event_windows']=[]
                    for offset in (-.1,0,.02,.1,.5,1,2):
                        start=int(at+offset*48000)+32
                        end=min(length,start+4800)
                        if start>=0 and end>start:
                            row['event_windows'].append(dict(offset_seconds=offset,comparison=screen(before[start:end],audio[start:end])))
            else:
                if not c['enabled'] and c['events']:
                    stop=c['events'][0]['frame']
                    row['initial_off_prefix_vs_direct_input']=screen(x[:stop],audio[32:32+stop])
            rows.append(row)
        findings[stage]=rows
    save_json(args.report,dict(kind='rmx220-reverb-down-motion-characterization',sample_rate=48000,
        reference_identity=IDENTITY,full_reverb_match=False,physical_hardware=False,
        calibration_sha256=sha256(args.calibration),identifier_sha256=sha256(Path(__file__)),findings=findings,
        limitations=['Original-versus-original state/timing diagnostics, not clone validation.',
            'Parameter timing is reported both in raw output and after the fixed bypass offset; no wet alignment is fitted.']))
    print('Recorded original motion/state diagnostics')


def compare(args):
    calibration(args.calibration)
    model=json.loads(args.model.read_text())
    repo=Path(__file__).resolve().parents[1]
    header=repo/'include/rmx/ReverbDownCalibration.h'
    if (model.get('kind')!='rmx220-reverb-down-static-control-model'
            or model['calibration_sha256']!=sha256(args.calibration) or model['header_sha256']!=sha256(header)):
        raise ValueError('Model/calibration/control header differs')
    root=new_directory(args.output)
    rows=[]
    for stage,directory in args.session:
        waves,cases=recipe(stage)
        for c in cases:
            if args.case and c['name'] not in args.case:
                continue
            audio,source,provenance=checked(Path(directory),c,waves[c['source']])
            receipt=json.loads((Path(directory)/c['name']/'receipt.json').read_text())
            prefix=stage+'-'+c['name']
            schedule,output,dry_trace=root/(prefix+'.tsv'),root/(prefix+'.wav'),root/(prefix+'-dry.wav')
            schedule.write_text('RMX_REVERB_MOTION 1\n'
                +f'initial {c["main"]} {c["amount"]} {c["cutoff"]} {c["enabled"]}\n'
                +f'tail {c["tail"]}\n'
                +(f'block {c["block"]}\n' if args.ramp_components=='startup' else '')
                +''.join(f'event {e["frame"]} {e["control"]} {e["value"]}\n' for e in c['events']))
            command=[args.renderer,receipt['input_path'],output,schedule,args.gate,args.cutoff_position,
                     args.gain_position,args.quantum,dry_trace]
            if args.level_position is not None or args.coefficient_ramp is not None or args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.level_position or 'send')
            if args.coefficient_ramp is not None or args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.coefficient_ramp or 0)
            if args.ramp_components is not None or args.decay_slew is not None:
                command.append(args.ramp_components or 'all')
            if args.decay_slew is not None:
                command.append(args.decay_slew)
            run(command)
            rate,candidate=float_wav(output)
            dry_rate,dry=float_wav(dry_trace)
            if rate!=48000 or dry_rate!=rate or len(candidate)!=len(audio) or len(dry)!=len(audio):
                raise ValueError('Motion renderer extent/rate differs')
            extent=len(audio)-32
            a=audio[32:]
            b=candidate[args.candidate_latency:args.candidate_latency+extent].astype(float)
            dry=dry[args.candidate_latency:args.candidate_latency+extent].astype(float)
            wet_a,wet_b=a-dry,b-dry
            row=provenance|dict(stage=stage,whole=screen(a,b),wet=screen(wet_a,wet_b),
                post_input_tail=screen(a[len(source):],b[len(source):]),
                candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry_trace),schedule_sha256=sha256(schedule),
                event_windows=[],activation_start_windows=[])
            for frame in sorted({e['frame'] for e in c['events']}):
                start,end=max(0,frame-64),min(len(a),frame+4096)
                row['event_windows'].append(dict(frame=frame,whole=screen(a[start:end],b[start:end]),
                    wet=screen(wet_a[start:end],wet_b[start:end])))
            if args.gate=='faded':
                anchors={0,12416} if c['enabled'] else set()
                anchors.update((e['frame']//32+1)*32+12416 for e in c['events'] if e['control']=='enabled' and e['value'])
                for frame in sorted(anchors):
                    start,end=max(0,frame-64),min(len(a),frame+4096)
                    if end>start:
                        row['activation_start_windows'].append(dict(frame=frame,whole=screen(a[start:end],b[start:end]),
                            wet=screen(wet_a[start:end],wet_b[start:end])))
            rows.append(row)
            passed=all(row[k]['passed'] for k in ('whole','wet','post_input_tail'))
            passed=passed and all(w[k]['passed'] for w in row['event_windows'] for k in ('whole','wet'))
            passed=passed and all(w[k]['passed'] for w in row['activation_start_windows'] for k in ('whole','wet'))
            row['passed']=passed
            print('PASS' if passed else 'FAIL',stage,c['name'],flush=True)
    if not rows:
        raise ValueError('No motion cases')
    passed=all(c['passed'] for c in rows)
    paths=candidate_sources()
    save_json(root/'comparison.json',dict(kind='diagnostic-reverb-down-motion-prototype-comparison',passed=passed,
        backend=getattr(args,'backend','core'),
        full_reverb_match=False,physical_hardware=False,sample_rate=48000,reference_identity=IDENTITY,
        model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=sha256(args.renderer),
        candidate_config=dict(gate=args.gate,cutoff_position=args.cutoff_position,gain_position=args.gain_position,control_quantum=args.quantum,candidate_latency=args.candidate_latency,level_position=args.level_position or 'send',coefficient_ramp_frames=args.coefficient_ramp or 0,ramp_components=args.ramp_components or 'all',decay_step_per_32_frames=args.decay_slew or 0),
        source_sha256={str(p.resolve().relative_to(repo)):sha256(p) for p in paths},cases=rows,
        acceptance=dict(relative_rms_error_limit=.01,silent_channel_absolute_rms_limit=1e-8,
            reference_channel_energy_floor=1e-20,reference_offset_frames=32,candidate_offset_frames=args.candidate_latency,gain_fit=False,wet_alignment_search=False,
            activation_start_windows=args.gate=='faded'),
        limitations=['Discovery recipes characterize state handling; fresh independent dynamic validation is still required.',
            'Wet subtraction uses the candidate-predicted dry trace on both sides, without a reference gain fit.',
            'Whole/wet event windows and the separate post-input tail prevent long quiet intervals or dry output from masking errors.']))
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for command in ('capture','verify'):
        p=commands.add_parser(command)
        p.add_argument('--stage',choices=CAPTURE_STAGES,required=True)
        p.add_argument('--session',type=Path,required=True)
        if command=='capture':
            p.add_argument('--prediction',type=Path)
            for name in ('host','plugin','calibration'):
                p.add_argument('--'+name,type=Path,required=True)
        else:
            p.add_argument('--report',type=Path,required=True)
    p=commands.add_parser('predict-cutoff',aliases=['predict-motion'])
    p.add_argument('--stage',choices=HOLDOUT_STAGES,default='cutoff-holdout')
    for name in ('model','calibration','renderer','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('analyze')
    for name in (*STAGES,'calibration','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('compare')
    p.add_argument('--backend',choices=('core','engine'),default='core',help='Identify the frozen renderer path; its binary hash remains authoritative')
    for name in ('model','calibration','renderer','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--session',nargs=2,action='append',required=True,metavar=('STAGE','DIRECTORY'))
    p.add_argument('--gate',choices=('inlet','output','inlet-output','reset','faded'),default='inlet')
    p.add_argument('--cutoff-position',choices=('pre','comb','post'),default='post')
    p.add_argument('--gain-position',choices=('read','write'),default='read')
    p.add_argument('--level-position',choices=('send','output','main-send','amount-send'))
    p.add_argument('--coefficient-ramp',type=int,help='Exploratory linear feedback/level coefficient ramp, 0..200000 frames')
    p.add_argument('--ramp-components',choices=('all','levels','feedback','staged','adaptive','startup'))
    p.add_argument('--decay-slew',type=float,help='Exploratory nominal T60 step per 32 frames; requires levels-only ramp')
    p.add_argument('--case',action='append',help='Exact recipe name; repeat to select diagnostic cases')
    p.add_argument('--candidate-latency',type=int,choices=(0,32),default=32)
    p.add_argument('--quantum',type=int,choices=(1,32,128),default=32)
    args=parser.parse_args()
    result={'capture':capture,'verify':verify,'analyze':analyze,'compare':compare,'predict-cutoff':predict,'predict-motion':predict}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__=='__main__':
    main()
