// Own I/O calibration; Down Main128/Sub1-128/48 kHz only.
#pragma once
#include <array>
constexpr std::array<std::array<int,2>,5> reverbDownDelays{{{{1033,1148}},{{1061,1859}},{{1147,1964}},{{1919,1117}},{{1995,1192}}}};
constexpr std::array<double,5> reverbDownGainL{0.97890943380299711,0.97834341199107988,0.97662730605573289,0.96119757069643985,0.9596898527645279};
constexpr std::array<double,5> reverbDownGainR{0.97660713143521638,0.96238954762633633,0.96030454377346697,0.97723262104726394,0.97571993005741275};
constexpr double reverbDownWetGain=0.13936791521654085;
