#include "rmx/State.h"
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace rmx {
State::State() {
    for(size_t i=0;i<parameterCount;++i) values[i]=parameters[i].initial;
    cc.fill(-1);
    cc[16]=static_cast<int>(Param::SceneDepth); cc[17]=static_cast<int>(Param::Low);
    cc[18]=static_cast<int>(Param::Mid); cc[19]=static_cast<int>(Param::High);
    cc[20]=static_cast<int>(Param::XPitch); cc[21]=static_cast<int>(Param::ReleaseAmount);
}
void State::capture(const ParameterStore& p) { values=p.snapshot(); }
void State::apply(ParameterStore& p) const { for(size_t i=0;i<parameterCount;++i) p.set(static_cast<Param>(i),values[i]); }
std::string State::serialize() const {
    std::ostringstream out; out<<"RMX_STATE 1\n"<<std::setprecision(9);
    for(size_t i=0;i<parameterCount;++i) {
        auto param=static_cast<Param>(i); float v=values[i];
        // Never reopen a session holding a momentary release lever.
        if(param==Param::ReleaseAmount||param==Param::XHold) v=0;
        out<<"param "<<parameters[i].id<<' '<<sanitize(param,v)<<'\n';
    }
    for(size_t i=0;i<16;++i) if(!samplePaths[i].empty()) out<<"sample "<<i<<' '<<std::quoted(samplePaths[i])<<'\n';
    for(size_t i=0;i<128;++i) if(cc[i]>=0&&cc[i]<static_cast<int>(parameterCount)) out<<"cc "<<i<<' '<<parameters[static_cast<size_t>(cc[i])].id<<'\n';
    return out.str();
}
State State::parse(std::string_view text) {
    if(text.size()>1024*1024) throw std::runtime_error("Preset exceeds 1 MB");
    std::istringstream in{std::string(text)}; std::string magic; int version=0;
    if(!(in>>magic>>version)||magic!="RMX_STATE"||version!=1) throw std::runtime_error("Unsupported RMX state version");
    State state; state.cc.fill(-1); std::string line; std::getline(in,line);
    while(std::getline(in,line)) {
        std::istringstream row(line); std::string kind,id; row>>kind;
        if(kind=="param") {
            float value;
            if(!(row>>id>>value)||!std::isfinite(value)) throw std::runtime_error("Invalid parameter value");
            for(size_t i=0;i<parameterCount;++i) if(parameters[i].id==id) state.values[i]=sanitize(static_cast<Param>(i),value);
        } else if(kind=="sample") {
            size_t slot; std::string path;
            if(!(row>>slot>>std::quoted(path))||slot>=16||path.size()>4096) throw std::runtime_error("Invalid sample reference");
            state.samplePaths[slot]=path;
        } else if(kind=="cc") {
            int control;
            if(!(row>>control>>id)||control<0||control>=128) throw std::runtime_error("Invalid MIDI mapping");
            for(size_t i=0;i<parameterCount;++i) if(parameters[i].id==id) state.cc[static_cast<size_t>(control)]=static_cast<int>(i);
        }
    }
    state.values[static_cast<size_t>(Param::ReleaseAmount)]=0;
    state.values[static_cast<size_t>(Param::XHold)]=0;
    return state;
}
void State::save(const std::filesystem::path& path) const {
    auto temp=path; temp+=".tmp";
    { std::ofstream out(temp,std::ios::binary|std::ios::trunc); if(!out) throw std::runtime_error("Cannot write preset"); out<<serialize(); out.flush(); if(!out) throw std::runtime_error("Preset write failed"); }
    std::filesystem::rename(temp,path);
}
State State::load(const std::filesystem::path& path) {
    std::ifstream in(path,std::ios::binary); if(!in) throw std::runtime_error("Cannot open preset");
    if(std::filesystem::file_size(path)>1024*1024) throw std::runtime_error("Preset exceeds 1 MB");
    return parse(std::string(std::istreambuf_iterator<char>(in),{}));
}
}
