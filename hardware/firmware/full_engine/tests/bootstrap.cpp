// Host tests only: production firmware initializes explicitly after SDRAM setup.
#include "rmx/SampleReader.h"
#include <cstdlib>
namespace {
const bool initialized = [] {
    if (!rmx::sample_reader::initializeTable()) std::abort();
    return true;
}();
}
