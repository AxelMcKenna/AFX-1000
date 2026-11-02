#pragma once
#include <algorithm>

namespace rmx {
// The delay length is latched for a complete 32-frame read cache. A new
// length fades that cache out before the following block reads the new tap.
struct DelayRetiming {
    double current{},read{},target{};
    float gain{},step{};
    bool ready{};
    void beginBlock(double requested) noexcept {
        if(!ready){current=requested;ready=true;}
        read=current;target=requested;step=current==target?.00625f:-.00625f;
    }
    float advance() noexcept {
        gain=std::min(1.f,gain+step);
        if(gain<0){gain=0;current=target;}
        return gain;
    }
};
}
