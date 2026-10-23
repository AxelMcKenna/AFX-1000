#pragma once
#include <algorithm>
#include <array>
namespace rmx::panel {
// The hardware layout is retained; saturated LED colors use the RMX palette.
inline std::array<float, 3> skinColor(float r, float g, float b) {
    const float minimum = std::min({r, g, b});
    if (r > .12f && r > g * 1.45f && r > b * 1.4f)
        return {r, minimum + (r - minimum) * .68f, minimum + (r - minimum) * .13f};
    if (g > .15f && g > r * 1.08f && g > b * 1.45f)
        return {minimum + (g - minimum) * .10f, g, minimum + (g - minimum) * .78f};
    if (b > .15f && b > r * 1.35f && b > g * 1.1f)
        return {minimum + (b - minimum) * .10f, minimum + (b - minimum) * .79f, b * .92f};
    return {r, g, b};
}
} // namespace rmx::panel
