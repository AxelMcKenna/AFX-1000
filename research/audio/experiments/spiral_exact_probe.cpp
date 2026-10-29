// Research-only active-filter/clock reconstruction. Neutral Main128/Sub2-zero/120BPM.
// Qualification is separate; this is not a production Spiral implementation.
#include "rmx/Wav.h"
#include "rmx/FactoryEchoReturn.h"
#include "IsolateNeutral.h"
#include <iostream>
int main(int argc,char** argv){try{
 if(argc!=6)throw std::runtime_error("INPUT OUTPUT up|down SUB1 TAIL");
 if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output exists");
 const std::string direction=argv[3];if(direction!="down"&&direction!="up")throw std::runtime_error("Direction must be up or down");
 const bool down=direction=="down";const unsigned delay=down?12144:2496;const float loopGain=down?1.2f:1.5f;
 const auto source=rmx::readWav(argv[1],180);if(source.rate!=48000)throw std::runtime_error("Requires 48 kHz");
 const auto raw=std::stoi(argv[4]);const auto tailSeconds=std::stod(argv[5]);if(raw<0||raw>255||!std::isfinite(tailSeconds)||tailSeconds<0||tailSeconds>30)throw std::runtime_error("Invalid control/tail");rmx::Sample output;output.rate=48000;output.frames.resize(source.frames.size()+std::lround(tailSeconds*48000));
 using Biquad=rmx::research::IsolateNeutral::Biquad;Biquad inputFilter,high,low,post,pitchFilter;
 pitchFilter.c={.7878031134605408f,0.f,-.7878031134605408f,-.42026737332344055f,-.5756062865257263f};
 inputFilter.c={.29287490248680115f,.5857498049736023f,.29287490248680115f,-7.176304665877298e-17f,.1714995801448822f};
 high.c={.9682207107543945f,-1.936441421508789f,.9682207107543945f,-1.9362547397613525f,.9366280436515808f};
 low.c={.29549500346183777f,.5909900069236755f,.29549500346183777f,.015271740034222603f,.1667083203792572f};
 post.c={.1419954150915146f,.2839908301830292f,.1419954150915146f,-.19833816587924957f,-.23368017375469208f};
 std::vector<rmx::Stereo> history(196608);unsigned writer=0;std::vector<rmx::Stereo> pitch(down?640:1792);unsigned pitchWriter=0;
 rmx::FactoryEchoReturn echoes;echoes.prepare(48000);echoes.restart(rmx::FactoryEchoReturn::Profile::spiral);
 float average=0,held=0,phase=0;bool descending=false;unsigned quiet=0;
 const float outGain=(std::min(1-( (1-std::min(static_cast<float>(delay)*1.0416666555101983e-5f,1.f))*.1809999942779541f+.3199999928474426f)*loopGain,.30000001192092896f)*1.4125374555587769f)*1.2999999523162842f;

 for(size_t base=0;base<output.frames.size();base+=32){
  std::array<rmx::Stereo,32> input{},wet{},delayed{};float peak=0;
  for(unsigned i=0;i<32;++i)if(base+i<source.frames.size()){input[i]=source.frames[base+i];peak=std::max(peak,std::abs((input[i].l+input[i].r)*.5f));}
  const float weighted=average*186.f+peak;average=static_cast<float>(static_cast<double>(weighted)/187.);held=std::max(held,average);
  inputFilter.process(input,wet);
  for(unsigned i=0;i<32;++i){
   // The first active original Spiral block follows the shared 32-frame startup.
   if(base>=32){if(descending){phase-=2.0833333843036924e-6f;if(phase < -1){descending=false;phase=-2-phase;}}
   else{phase+=2.0833333843036924e-6f;if(phase>1){descending=true;phase=2-phase;}}}
   const int integer=static_cast<int>(phase);const float fraction=phase-integer+(phase<0?1.f:0.f);const int whole=integer-(phase<0?1:0);
   const auto first=history[(writer+i+196608-delay-whole)%196608],previous=history[(writer+i+196608-delay-whole-1)%196608];
   const auto tap=first*(1-fraction)+previous*fraction;wet[i]={std::clamp(wet[i].l+tap.l,-held,held),std::clamp(wet[i].r+tap.r,-held,held)};
  }
  high.process(wet,wet);low.process(wet,wet);
  for(unsigned i=0;i<32;++i)history[(writer+i)%196608]=wet[i]*loopGain;
  writer=(writer+32)%196608;post.process(wet,wet);
  for(unsigned i=0;i<32;++i){
   wet[i]=(wet[i]*1.2999999523162842f)*(outGain/1.2999999523162842f);++quiet;if(std::abs((wet[i].l+wet[i].r)*.5f)>=held*.001f)quiet=0;
   delayed[i]=pitch[pitchWriter];pitch[pitchWriter]=wet[i];pitchWriter=(pitchWriter+1)%pitch.size();
  }
  pitchFilter.process(delayed,delayed);
  for(unsigned i=0;i<32;++i){
   const auto old=delayed[i];const auto tail=echoes.process({old.l,old.r},raw,1,120);
   if(base+i<output.frames.size())output.frames[base+i]={static_cast<float>(input[i].l+old.l+tail[0]),static_cast<float>(input[i].r+old.r+tail[1])};
  }
  if(quiet>=4801){held*=.8912509083747864f;quiet=0;}
 }
 rmx::writeWav(argv[2],output);std::cout<<outGain<<'\n';
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
