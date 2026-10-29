#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <memory_resource>
#include <numbers>
#include <vector>
#include <span>

namespace rmx {
struct Stereo { float l{},r{}; };
inline Stereo operator+(Stereo a,Stereo b) { return {a.l+b.l,a.r+b.r}; }
inline Stereo operator-(Stereo a,Stereo b) { return {a.l-b.l,a.r-b.r}; }
inline Stereo operator*(Stereo a,float s) { return {a.l*s,a.r*s}; }
inline Stereo mix(Stereo a,Stereo b,float t) { return a*(1-t)+b*t; }
inline float peak(Stereo x) { return std::max(std::abs(x.l),std::abs(x.r)); }
inline float poleCoefficient(float hz,double rate) { return 1-std::exp(-2*std::numbers::pi_v<float>*hz/static_cast<float>(rate)); }

class FractionalDelay {
public:
    void prepare(size_t count) { owned.assign(std::max(size_t{4},count),{});external={};head=written=0; }
    // Borrow storage from mutually exclusive processors; no callback allocation.
    void attach(std::span<Stereo> storage) noexcept {external=storage;invalidate();}
    std::span<Stereo> loanableStorage() noexcept {return storage();}
    void invalidate() noexcept {head=written=0;}
    void reset() noexcept {auto frames=storage(); std::fill(frames.begin(),frames.end(),Stereo{});head=written=0; }
    void push(Stereo value) noexcept {
        auto frames=storage();
        if(frames.empty())return;
        frames[head]=value;if(++head==frames.size())head=0;written=std::min(written+1,frames.size());
    }
    Stereo read(double ago) const noexcept {
        const auto frames=storage();
        if(frames.empty())return {};
        ago=std::isfinite(ago)?std::clamp(ago,1.,static_cast<double>(frames.size()-2)):1.;
        const double position=static_cast<double>(head)-ago,whole=std::floor(position);
        // Wrap the integer index. Adding the ring length to a tiny negative
        // floating position can round to exactly the length (one past the end).
        auto index=static_cast<std::ptrdiff_t>(whole);
        if(index<0)index+=static_cast<std::ptrdiff_t>(frames.size());
        const auto first=static_cast<size_t>(index),next=first+1==frames.size()?0:first+1;
        const auto older=static_cast<size_t>(std::ceil(ago)),newer=older-1;
        return mix(older<=written?frames[first]:Stereo{},newer<=written?frames[next]:Stereo{},static_cast<float>(position-whole));
    }
private:
    std::span<Stereo> storage() noexcept {return external.empty()?std::span<Stereo>{owned}:external;}
    std::span<const Stereo> storage() const noexcept {return external.empty()?std::span<const Stereo>{owned}:external;}
    std::pmr::vector<Stereo> owned;std::span<Stereo> external;size_t head{},written{};
};

// Topology-preserving state-variable filter. Coefficients are updated at the
// control rate; processing remains stable while the cutoff moves.
class StateFilter {
public:
    struct Output { Stereo low,band,high; };
    void configure(float hz,float q,double rate) noexcept {
        const float g=std::tan(std::numbers::pi_v<float>*std::clamp(hz,5.f,static_cast<float>(rate*.45))/static_cast<float>(rate));
        k=1/std::clamp(q,.5f,12.f); a1=1/(1+g*(g+k)); a2=g*a1; a3=g*a2;
    }
    Output process(Stereo input) noexcept {
        const auto v3=input-ic2, v1=ic1*a1+v3*a2, v2=ic2+ic1*a2+v3*a3;
        ic1=v1*2-ic1; ic2=v2*2-ic2;
        return {v2,v1,input-v1*k-v2};
    }
    void reset() noexcept { ic1={};ic2={}; }
private:
    float k{1.41421356f},a1{},a2{},a3{}; Stereo ic1{},ic2{};
};
}
