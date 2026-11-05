#include "LinkSession.h"
#include <ableton/Link.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {
using namespace std::chrono_literals;
void write(const std::filesystem::path& path,const std::string& text){
    const auto temp=path.string()+".writing";
    {std::ofstream file(temp);file<<text;if(!file)throw std::runtime_error("Cannot write probe state");}
    std::filesystem::rename(temp,path);
}
int publish(const std::filesystem::path& command,const std::filesystem::path& output){
    ableton::Link peer{120};peer.enableStartStopSync(false);peer.enable(true);
    double applied=-1;size_t previous=0;
    const auto deadline=std::chrono::steady_clock::now()+60s;
    while(std::chrono::steady_clock::now()<deadline){
        std::string request;{std::ifstream file(command);file>>request;}
        if(request=="stop")return 0;
        const auto peers=peer.numPeers();
        if(peers>1)throw std::runtime_error("Additional Link peer detected; stopped test publisher");
        const double target=request.empty()?120:std::stod(request);
        if(!std::isfinite(target)||target<20||target>300)throw std::runtime_error("Invalid test tempo");
        if(target!=applied||(peers&&previous==0)){
            auto state=peer.captureAppSessionState();state.setTempo(target,peer.clock().micros());peer.commitAppSessionState(state);applied=target;
        }
        previous=peers;
        const auto time=peer.clock().micros()+50ms;
        const auto state=peer.captureAppSessionState();
        std::ostringstream row;row<<std::setprecision(17)<<time.count()<<' '<<state.tempo()<<' '<<state.beatAtTime(time,4.)<<' '<<state.beatAtTime(time+100ms,4.)<<' '<<peers<<'\n';
        write(output,row.str());std::this_thread::sleep_for(20ms);
    }
    throw std::runtime_error("Publisher test timed out");
}
}
int main(int argc,char** argv){try{
    if(argc<2)throw std::runtime_error("Usage: link_probe --observe SECONDS | --compare STATE BPM | --publish COMMAND STATE");
    const std::string mode=argv[1];
    if(mode=="--publish"&&argc==4)return publish(argv[2],argv[3]);
    if((mode!="--observe"||argc!=3)&&(mode!="--compare"||argc!=4))throw std::runtime_error("Invalid probe arguments");
    LinkSession follower;ableton::Link timebase{120};rmx::Transport untouched;untouched.bpm=91;untouched.beat=12.5;
    if(!LinkSession::available()||follower.enabled()||follower.capture(timebase.clock().micros().count(),untouched)||untouched.bpm!=91||untouched.beat!=12.5)
        throw std::runtime_error("Disabled adapter changed transport");
    follower.enable(true);
    const double value=std::stod(argv[mode=="--observe"?2:3]);
    if(!std::isfinite(value)||(mode=="--observe"?(value<1||value>15):(value<20||value>300)))throw std::runtime_error("Invalid probe bound");
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(mode=="--observe"?static_cast<int>(value*1000):15000);
    unsigned stable=0,samples=0;double maximumErrorMs=0,maximumPeriodError=0;rmx::Transport last;bool locked=false;unsigned maximumPeers=0;
    while(std::chrono::steady_clock::now()<deadline){
        maximumPeers=std::max(maximumPeers,follower.peers());
        if(mode=="--observe")locked=follower.capture(timebase.clock().micros().count(),last);
        else {
            int64_t at=0;double tempo=0,beat=0,future=0;unsigned peers=0;
            std::ifstream file(argv[2]);
            if(file>>at>>tempo>>beat>>future>>peers){
                if(follower.peers()>1)throw std::runtime_error("Additional Link peer detected; stopped isolated test");
                rmx::Transport current,next;
                const bool a=follower.capture(at,current),b=follower.capture(at+100000,next);
                const auto error=std::max(std::abs(std::remainder(current.beat-beat,4.)),std::abs(std::remainder(next.beat-future,4.)))*60000/value;
                // Link's wire protocol rounds microseconds per beat. Compare
                // that resolution rather than demanding exact decimal BPM.
                const double period=std::llround(60000000/value);
                const double periodError=std::max(std::abs(60000000/current.bpm-period),std::abs(60000000/tempo-period));
                const bool expected=value>=40&&value<=240;
                const bool match=peers==1&&follower.peers()==1&&std::abs(60000000/tempo-period)<2.
                    &&(expected?(a&&b&&current.synced&&current.playing&&periodError<2.&&error<1.):(!a&&!b));
                stable=match?stable+1:0;
                if(match&&expected){maximumErrorMs=std::max(maximumErrorMs,error);maximumPeriodError=std::max(maximumPeriodError,periodError);}
                ++samples;last=current;locked=a;
                if(stable>=20)break;
            }
        }
        std::this_thread::sleep_for(25ms);
    }
    const bool passed=mode=="--observe"||stable>=20;
    follower.enable(false);rmx::Transport stopped;const bool disabled=!follower.capture(timebase.clock().micros().count(),stopped);
    std::cout<<std::setprecision(17)<<"{\"passed\":"<<(passed&&disabled?"true":"false")<<",\"available\":true,\"maximum_peers\":"<<maximumPeers
        <<",\"locked\":"<<(locked?"true":"false")<<",\"bpm\":"<<last.bpm<<",\"beat\":"<<last.beat<<",\"stable_samples\":"<<stable
        <<",\"samples\":"<<samples<<",\"maximum_phase_error_ms\":"<<maximumErrorMs<<",\"maximum_beat_period_error_us\":"<<maximumPeriodError<<",\"disabled_fallback_passed\":"<<(disabled?"true":"false")<<"}\n";
    return passed&&disabled?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
