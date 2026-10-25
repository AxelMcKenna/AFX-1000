#pragma once
#ifndef RMX_EXTERNAL_CONVERTER
#define RMX_EXTERNAL_CONVERTER 0
#endif
static_assert(RMX_EXTERNAL_CONVERTER == 0 || RMX_EXTERNAL_CONVERTER == 1);
namespace rmx::embedded {
inline constexpr bool externalConverter = RMX_EXTERNAL_CONVERTER;
inline constexpr unsigned permitPin = externalConverter ? 29 : 26;
inline constexpr unsigned armedPin = externalConverter ? 30 : 28;
inline constexpr unsigned resetPin = externalConverter ? 0 : 27;
} // namespace rmx::embedded
