#pragma once
#include <cmath>
#include <iostream>
#include <stdexcept>

inline void require(bool condition, const char* message) {
    if (!condition)
        throw std::runtime_error(message);
}
template <class Test> int runTests(Test test) {
    try {
        test();
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
