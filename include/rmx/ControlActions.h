#pragma once
#include "Parameters.h"

namespace rmx {
// The persisted source encoding predates the bit mask: 0=input, 1=pad,
// 2=both, 3=neither. Keep that wire/state representation at this boundary.
enum class Source : uint8_t { Input, Pad };
inline float toggleSource(float encoded, Source source) noexcept {
    const int current = static_cast<int>(encoded);
    int bits = current == 0 ? 1 : current == 1 ? 2 : current == 2 ? 3 : 0;
    bits ^= 1 << static_cast<int>(source);
    return bits == 0 ? 3.f : bits == 1 ? 0.f : bits == 2 ? 1.f : 2.f;
}
template <class Read, class Write> void toggleRouting(Source source, Read read, Write write) {
    const float next = toggleSource(read(Param::SceneSource), source);
    write(Param::SceneSource, next);
    write(Param::IsolateSource, next);
}
} // namespace rmx
