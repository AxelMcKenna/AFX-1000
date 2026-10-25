#include "../KernelTransport.h"
#include <bit>
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace rmx::sample_reader;
void require(bool value) { if (!value) std::abort(); }
void same(const Level& actual, const Level& expected) {
    require(std::bit_cast<uint32_t>(actual.cutoff) == std::bit_cast<uint32_t>(expected.cutoff));
    for (unsigned p = 0; p <= phases; ++p)
        for (unsigned t = 0; t < taps; ++t)
            require(std::bit_cast<uint32_t>(actual.kernels[p].weights[t]) ==
                    std::bit_cast<uint32_t>(expected.kernels[p].weights[t]));
}
int main() {
    require(!tableReady());
    const std::array<rmx::Stereo, 1> source{{{1, 1}}};
    const auto silent = rmx::readOneShot(source, 0, 1);
    require(silent.l == 0 && silent.r == 0 && !tableReady());
    const auto reference = makeTable(std::make_index_sequence<levels>{});
    std::vector<Level> scratch(levels);
    const auto payload = kernelPayload();
    require(decodeKernelTable(payload, scratch));
    for (unsigned i = 0; i < levels; ++i) same(scratch[i], *reference[i]);
    require(!tableReady());
    for (size_t size : {size_t(0), size_t(1), size_t(4355), payload.size()-1})
        require(!decodeKernelTable(payload.first(size), scratch));
    require(!decodeKernelTable(payload, std::span<Level>(scratch).first(levels-1)));
    std::vector<uint8_t> bad(payload.begin(), payload.end());
    bad[100] ^= 1;
    require(!decodeKernelTable(bad, scratch));
    bad.assign(payload.begin(), payload.end()); bad.push_back(0);
    require(!decodeKernelTable(bad, scratch));
    bad.assign(payload.begin(), payload.end());
    for (size_t i = 4356; i < 4361; ++i) bad[i] = 0xff;
    require(!decodeKernelTable(bad, scratch));
    require(initializeTable() && tableReady());
    for (unsigned i = 0; i < levels; ++i) same(*table[i], *reference[i]);
    const auto* first = table[0];
    require(initializeTable() && table[0] == first);
    require(rmx::readOneShot(source, 0, 1).l == 1);
    std::puts("All 69,729 float words restored bit-exactly; invalid payloads stay unpublished.");
}
