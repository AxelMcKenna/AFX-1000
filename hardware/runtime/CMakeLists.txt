cmake_minimum_required(VERSION 3.24)
project(RMXStandaloneRuntime VERSION 0.1.0 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(RMX_BUILD_TESTS "Build standalone runtime and firmware host checks" ON)
get_filename_component(RMX_REPOSITORY_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

add_library(rmx_core
  src/core/Engine.cpp src/core/Primitives.cpp src/core/Sampler.cpp
  src/core/Isolator.cpp src/core/SceneEffects.cpp src/core/ReleaseEffects.cpp
  src/core/SampleBank.cpp src/core/State.cpp src/core/Wav.cpp)
target_include_directories(rmx_core PUBLIC include)
target_compile_options(rmx_core PRIVATE -Wall -Wextra -Wpedantic)

if(RMX_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
