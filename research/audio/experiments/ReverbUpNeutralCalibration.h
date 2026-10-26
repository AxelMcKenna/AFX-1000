// Own I/O identification. Static factory Up Main128/Sub1-128/48 kHz only.
#pragma once
#include <array>
constexpr std::array<std::array<int,2>,5> reverbUpDelays{{{{509,565}},{{523,915}},{{565,967}},{{945,550}},{{983,587}}}};
constexpr std::array<double,5> reverbUpGainL{0.989554269384189,0.98927325821821988,0.98841909948984141,0.98069511821772237,0.9799317316229913};
constexpr std::array<double,5> reverbUpGainR{0.98840768656785793,0.98129214396345965,0.98024331870398118,0.98871808105477266,0.98796777819495563};
constexpr std::array<double,2> reverbUpInputA{-1.906901401479743,0.9100260226575746};
constexpr double reverbUpWetGain=0.0062061353667316656;
