// Generated. Do not edit.
#pragma once
#include "rmx/Parameters.h"
namespace rmx::board {
inline constexpr unsigned button_load=0;
inline constexpr unsigned button_clock=7;
inline constexpr unsigned button_data=8;
inline constexpr unsigned led_data=9;
inline constexpr unsigned led_clock=10;
inline constexpr unsigned led_latch=13;
inline constexpr unsigned led_oe=14;
inline constexpr unsigned i2c_scl=11;
inline constexpr unsigned i2c_sda=12;
inline constexpr unsigned adc_mux_a=15;
inline constexpr unsigned adc_mux_b=16;
inline constexpr unsigned mux_s0=25;
inline constexpr unsigned mux_s1=26;
inline constexpr unsigned mux_s2=27;
inline constexpr unsigned watchdog_heartbeat=28;
inline constexpr unsigned dsp_ready=17;
inline constexpr Param adcParameters[]={Param::InputGain,Param::OutputGain,Param::Low,Param::Mid,Param::High,Param::SceneDepth,Param::SceneTime,Param::SceneResonance,Param::XLevel,Param::XPitch,Param::ReleaseAmount};
inline constexpr unsigned buttonCount=29;
inline constexpr unsigned releaseBackBit=29,releaseBrakeBit=30,userBit=31;
}
