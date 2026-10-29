#include "rmx/CalibratedTransRoll.h"

namespace rmx {
void CalibratedTransRoll::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
        timeline=timeline+(32.*120)/(48000.*60);const double position=std::fmod(std::fmod(timeline,96.),.0625);const bool grid=position<previousGrid;previousGrid=position;
        if(grid)elapsed=0;else if(elapsed<=20000)elapsed+=32;
        std::array<Stereo,32> low{},middle{},high{},above{};
        lpLow.process(input,low);hpLow.process(input,above);lpHigh.process(above,middle);hpHigh.process(input,high);
        levels[0].update(high);levels[1].update(middle);levels[2].update(low);
        for(unsigned i=0;i<32;++i){
            const std::array<Stereo,3> values{high[i],middle[i],low[i]};
            for(unsigned band=0;band<3;++band){
                if(storageActive)memory(band*196608+static_cast<unsigned>(rawWriter)+i)=values[band];
                recent[band*1024+recentWriter]=values[band];
            }
            recentWriter=(recentWriter+1)%1024;recentValid=std::min(recentValid+1,1024u);
        }
        rawWriter=(rawWriter+32)%196608;
        if(storageActive)historyValid=std::min(historyValid+32,196608u);
        if(selected&&storageActive){if(initializing){initializeTrans();initializing=false;}processTrans(0,high,grid);processTrans(1,middle,grid);processTrans(2,low,grid);}
        if(enabled!=selected){step=-.00625f;phase=1;}else if(phase==2)step=.00625f;
        for(size_t i=0;i<32;++i){const Stereo sum=selected?(high[i]+middle[i])+low[i]:input[i];master+=step;output[i]={sum.l*master+input[i].l*(1-master),sum.r*master+input[i].r*(1-master)};}
        if(master>1-.00625f){master=1;step=0;phase=0;}
        if(master<.00625f){master=step=0;selected=enabled;phase=2;initializing=selected;}
    }

}
