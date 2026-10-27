#pragma once
#include <array>
namespace rmx::research {
// Read-only numeric polynomial observations; full candidate acceptance is separate.
inline constexpr std::array<float,7> kickSineHz{0.f,0.00013092833978589624f,-2.7656446577317695e-11f,-3.643783679733309e-13f,-1.5541412628600493e-18f,4.5646243522925154e-22f,-6.3200989646920986e-27f};
inline constexpr std::array<float,7> kickCosineHz{1.f,-7.0119611450536468e-08f,-8.5055695819846733e-09f,-1.8732750268514453e-14f,1.4848692706159798e-17f,-1.7840119663831942e-22f,-1.8356340670956014e-27f};
}
