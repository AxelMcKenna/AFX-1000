#pragma once
#include "Parameters.h"
#include <vector>
#include <string>

namespace rmx::panel {
inline constexpr float width=2048,height=921;
enum class Kind { Knob, Toggle, Choice, Pad, Strip, Lever, Action };
struct Rect { float x,y,w,h; };
struct Control { Rect rect; Kind kind; Param param; std::string label; float value{}; int action{}; };
inline std::vector<Control> controls() {
    std::vector<Control> out;
    auto add=[&](Rect r,Kind k,Param p,std::string label,float value=0,int action=0) { out.push_back({r,k,p,std::move(label),value,action}); };
    auto knob=[&](float x,float y,float radius,Param p) { add({x-radius,y-radius,radius*2,radius*2},Kind::Knob,p,std::string(parameters[static_cast<size_t>(p)].name)); };
    knob(112,172,42,Param::InputGain); knob(690,172,42,Param::OutputGain);
    add({768,104,120,49},Kind::Toggle,Param::Quantize,"QUANTIZE");
    add({1097,104,88,49},Kind::Toggle,Param::AutoTempo,"AUTO");
    add({1102,187,78,78},Kind::Action,Param::Count,"TAP",0,6);
    add({767,200,61,53},Kind::Action,Param::Tempo,"NUDGE -",-0.1f,7);
    add({829,200,58,53},Kind::Action,Param::Tempo,"NUDGE +",0.1f,7);
    add({925,153,115,53},Kind::Knob,Param::Tempo,"BPM");
    add({54,328,90,50},Kind::Action,Param::SceneSource,"INPUT",0,8);
    add({55,514,90,50},Kind::Action,Param::SceneSource,"X-PAD",1,8);
    constexpr std::array<float,4> isolateX{394,513,747,863};
    for(int i=0;i<4;++i) add({isolateX[static_cast<size_t>(i)],329,88,48},Kind::Choice,Param::IsolateMode,std::string(isolateNames[static_cast<size_t>(i)]),static_cast<float>(i));
    knob(325,464,86,Param::Low); knob(668,464,86,Param::Mid); knob(1019,464,86,Param::High);
    knob(1503,466,78,Param::SceneDepth);
    knob(118,785,40,Param::XLevel); knob(330,782,47,Param::XPitch);
    knob(1198,785,48,Param::SceneTime); knob(1813,781,45,Param::SceneResonance);
    add({198,621,52,55},Kind::Action,Param::Bank,"BANK",0,9);
    add({342,623,89,52},Kind::Toggle,Param::XSource,"ROLL");
    for(int i=0;i<4;++i) add({458.f+i*115,623,89,52},Kind::Pad,Param::Bank,std::string(drumNames[static_cast<size_t>(i)]),static_cast<float>(i));
    add({993,623,54,52},Kind::Toggle,Param::Overdub,"OVERDUB / DELETE");
    add({980,741,79,81},Kind::Toggle,Param::XHold,"HOLD / MUTE");
    add({473,739,410,82},Kind::Strip,Param::XRoll,"X-PAD");
    add({1818,146,93,54},Kind::Toggle,Param::UserSettings,"DEFAULT / USER");
    add({1890,297,84,55},Kind::Action,Param::ReleaseType,"RELEASE FX",0,10);
    add({1880,432,116,101},Kind::Lever,Param::ReleaseAmount,"RELEASE");
    return out;
}
// Front-panel Scene FX buttons occupy a segmented annulus rather than rectangles.
inline int sceneAt(float x,float y) {
    const float dx=x-1503,dy=y-466,r=std::hypot(dx,dy);
    if(r<184||r>326) return -1;
    const float degrees=std::atan2(dy,dx)*180/3.14159265358979323846f;
    if(degrees>=-153&&degrees<=-27) return std::clamp(static_cast<int>((degrees+153)/25.2f),0,4);
    if(degrees>=27&&degrees<=153) return 5+std::clamp(static_cast<int>((153-degrees)/25.2f),0,4);
    return -1;
}
inline Rect meterRect(bool output) { return {263,output?207.f:123.f,368,23}; }
}
