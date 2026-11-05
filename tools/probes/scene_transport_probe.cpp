#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <iostream>
int main(int argc,char**argv){try{
 if(argc!=4)throw std::runtime_error("INPUT NEW_OUTPUT BLOCK");if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output exists");
 const auto source=rmx::readWav(argv[1],30);const auto block=std::stoul(argv[3]);if(source.rate!=48000||block<1||block>4096)throw std::runtime_error("Invalid format/block");
 rmx::Engine engine;engine.setOutputProtection(false);engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);engine.prepare(48000,block);
 rmx::Sample result;result.rate=48000;result.frames.resize(source.frames.size());std::array<float,4096> l{},r{},a{},b{};
 for(size_t start=0;start<source.frames.size();start+=block){const auto n=std::min<size_t>(block,source.frames.size()-start);for(size_t i=0;i<n;++i){l[i]=source.frames[start+i].l;r[i]=source.frames[start+i].r;}engine.process(l.data(),r.data(),a.data(),b.data(),n);for(size_t i=0;i<n;++i)result.frames[start+i]={a[i],b[i]};}
 rmx::writeWav(argv[2],result);
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
