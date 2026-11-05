#include "rmx/HardwareCalibration.h"
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using namespace rmx;
static void require(bool value,const char* text){if(!value)throw std::runtime_error(text);}
static bool close(float a,float b){return std::abs(a-b)<1e-5f;}
struct File final:SampleFile {
    std::string text;size_t position{},fragment{3},failAfter{SIZE_MAX};bool badSeek{},badCount{};
    uint64_t size()const noexcept override{return text.size();}
    bool seek(uint32_t x)noexcept override{position=x;return !badSeek;}
    size_t read(std::span<std::byte> out)noexcept override {
        if(badCount)return out.size()+1;
        if(position>=failAfter)return 0;
        auto n=std::min({out.size(),fragment,text.size()-position,failAfter-position});
        std::memcpy(out.data(),text.data()+position,n);position+=n;return n;
    }
};
int main(){try{
    ControlCalibration c;
    require(close(c.apply(2,.5f,false),.5f),"default endpoint calibration changed midpoint");
    require(parseControlCalibration("RMX_CAL 1\npot 2 1000 25000 63000\npot 9 64000 36000 2000\n",c)==CardError::None,"valid calibration rejected");
    require(close(c.apply(2,1000.f/65535,true),0)&&close(c.apply(2,25000.f/65535,true),.5f)&&close(c.apply(2,63000.f/65535,true),1),"centered calibration not exact at endpoints/center");
    require(close(c.apply(9,64000.f/65535,true),0)&&close(c.apply(9,36000.f/65535,true),.5f)&&close(c.apply(9,2000.f/65535,true),1),"inverted calibration rejected");
    require(close(c.apply(2,32000.f/65535,false),.5f),"linear controls were center-warped");
    require(c.apply(2,-1,true)==0&&c.apply(2,2,true)==1,"endpoints do not clamp");
    require(c.apply(99,.5f,true)==0&&c.apply(0,std::numeric_limits<float>::quiet_NaN(),false)==0,"bad ADC sample not bounded");
    const auto before=c.pots[2];
    for(const auto& invalid:std::vector<std::string>{"","RMX_CAL 2\n","pot 0 0 32768 65535\n","RMX_CAL 1\npot 0 0 32768 65536\n","RMX_CAL 1\npot 11 0 32768 65535\n","RMX_CAL 1\npot 0 0 32768 65535 extra\n","RMX_CAL 1\npot 0 0 32768 65535\npot 0 0 32000 65000\n","RMX_CAL 1\npot 0 -1 32768 65535\n","RMX_CAL 1\npot 0 0 nan 65535\n","RMX_CAL 1\npot 0 1000 1200 3000\n","RMX_CAL 1\npot 0 0 500 1000\n","RMX_CAL 1\npot 0 0 32768 65535\nunknown 1\n",std::string(1025,' ')}) {
        require(parseControlCalibration(invalid,c)==CardError::Format,"malformed calibration accepted");
        require(c.pots[2].end0==before.end0&&c.pots[2].center==before.center&&c.pots[2].end1==before.end1,"partial calibration committed on failure");
    }
    File f;f.text=" \r\nRMX_CAL 1\r\npot 2 2000 31000 62000";
    std::array<std::byte,1024> scratch{};
    require(readControlCalibration(f,c,scratch)==CardError::None&&c.pots[2].end0==2000,"fragmented CRLF/final line failed");
    f.badSeek=true;require(readControlCalibration(f,c,scratch)==CardError::Read,"seek failure accepted");f.badSeek=false;
    f.failAfter=20;require(readControlCalibration(f,c,scratch)==CardError::Read&&c.pots[2].end0==2000,"read failure installed calibration");f.failAfter=SIZE_MAX;
    f.badCount=true;require(readControlCalibration(f,c,scratch)==CardError::Read,"invalid adapter count accepted");f.badCount=false;
    require(readControlCalibration(f,c,std::span(scratch).first(4))==CardError::Memory,"short calibration buffer accepted");
    StartupEnvelope env;std::array<float,64> left{},right{};size_t frame=0;
    for(unsigned block=0;block<40;++block) {
        left.fill(1);right.fill(-1);env.process(left.data(),right.data(),left.size());
        for(unsigned i=0;i<64;++i,++frame) {
            const float wanted=std::min(1.f,static_cast<float>(frame)/2400.f);
            require(close(left[i],wanted)&&close(right[i],-wanted),"startup fade changed stereo timing/gain");
        }
        require(env.ready()==(frame>=2400),"DSP ready released before the startup fade completed");
    }
    std::cout<<"PASS: calibration endpoints/inversion/center, transactional parser/I/O and startup fade\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
