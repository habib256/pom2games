/* GPL-3.0. Exhaustive native corridor comparison on both SDK CPU models.
 * Each invocation selects one CPU and a separately linked alias layout.
 * All writes are checked before execution; no IRQ is pending in this host.
 */
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <limits>
#include <set>
#include <vector>

using namespace pom2;

struct Instance {
    Core core;
    std::map<std::string, unsigned> labels;
    std::set<unsigned> allowed;
    std::array<unsigned char, 0xc000> original, auxiliary;

    unsigned address(const char* name) { return labels.at(std::string(".") + name); }
    unsigned read(unsigned at) { return core.read(at); }
    void write(unsigned at, unsigned value) { core.write(at, (unsigned char)value); }

    Instance(const char* binary, const char* symbols, bool cmos)
        : core(CoreConfig{cmos ? CpuModel::CMOS65C02 : CpuModel::NMOS6502,
                          VideoTiming::NTSC, true})
    {
        std::array<unsigned char, 0xc000> fill;
        fill.fill(0xa5);
        assert(core.writeRam(RamBank::Main, 0, fill.data(), fill.size()));
        fill.fill(0x69);
        assert(core.writeRam(RamBank::Aux, 0, fill.data(), fill.size()));
        probe::labels(labels, symbols);
        std::ifstream stream(binary, std::ios::binary);
        assert(stream);
        std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(stream)), {});
        assert(!bytes.empty() && bytes.size() <= 0x3600);
        assert(core.writeRam(RamBank::Main, 0x6000, bytes.data(), bytes.size()));
        for (auto name : {"PC_BITS", "_sx", "_sy", "_left", "_top", "_depth"})
            allowed.insert(address(name));
        assert(allowed.size() == 6);
        assert(core.readRam(RamBank::Main, 0, original.data(), original.size()));
        assert(core.readRam(RamBank::Aux, 0, auxiliary.data(), auxiliary.size()));
    }

    std::array<unsigned, 9> call(unsigned value, unsigned mode, unsigned flags)
    {
        auto state = core.cpuState();
        state.accumulator = value & 255;
        state.x = value >> 8;
        state.y = (value * 37 + 0x5a) & 255;
        state.status = 0x20 | flags;
        state.stackPointer = 0xfd;
        state.programCounter = address(mode == 0 ? "_perspective"
                                       : mode == 1 ? "_project_x" : "_project_y");
        state.halted = false;
        core.setCpuState(state);
        write(0x1fe, 0xff);
        write(0x1ff, 3); // Synthetic RTS target $0400; JSR cost included below.
        const auto start = state.cycles;
        unsigned steps = 0;
        while (core.cpuState().programCounter != 0x400 && ++steps < 1000) {
            const auto store = probe::storeTarget(core);
            assert(store < 0 || allowed.count((unsigned)store));
            core.step();
        }
        state = core.cpuState();
        assert(steps < 1000 && state.stackPointer == 255);
        assert((state.status & 12) == (flags & 12)); // I and D survive.
        assert(state.y == ((value * 37 + 0x5a) & 255));
        return {read(address("_depth")), read(address("_sx")), read(address("_sy")),
                read(address("_left")), read(address("_top")), state.accumulator,
                state.x, state.status, (unsigned)(state.cycles - start + 6)};
    }

    void guards()
    {
        std::array<unsigned char, 0xc000> memory;
        assert(core.readRam(RamBank::Main, 0, memory.data(), memory.size()));
        for (unsigned at = 0; at < memory.size(); ++at)
            if (!allowed.count(at) && at != 0x1fe && at != 0x1ff)
                assert(memory[at] == original[at]);
        assert(core.readRam(RamBank::Aux, 0, memory.data(), memory.size()));
        assert(memory == auxiliary);
        for (auto at : {0xc013, 0xc014, 0xc016}) assert(!(read(at) & 128));
    }
};

int main(int argc, char** argv)
{
    assert(argc == 9);
    const bool cmos = std::stoi(argv[5]);
    const unsigned shift = std::stoi(argv[6]);
    assert(shift == 1); // This guard comparison targets the Y-preserving common path.
    const unsigned cx = std::stoi(argv[7]), cy = std::stoi(argv[8]);
    Instance before(argv[1], argv[2], cmos), after(argv[3], argv[4], cmos);
    unsigned long long calls = 0;
    long long saved = 0;
    unsigned faster = 0, equal = 0, slower = 0;
    long minimum = std::numeric_limits<long>::max();
    long maximum = std::numeric_limits<long>::min();
    for (unsigned masked = 0; masked < 2; ++masked) {
        for (unsigned distance = 0; distance < 65536; ++distance) {
            const unsigned flags = masked * 4 | ((distance & 1) ? 1 : 0)
                                   | ((distance & 2) ? 0xc0 : 0);
            const auto a = before.call(distance, 0, flags);
            const auto b = after.call(distance, 0, flags);
            for (unsigned i = 0; i < 8; ++i) assert(a[i] == b[i]);
            const unsigned index = std::min(distance >> shift, 255u);
            assert(b[0] == index);
            assert(b[1] == after.read(after.address("_scale_x") + index));
            assert(b[2] == after.read(after.address("_scale_y") + index));
            assert(b[3] == cx - b[1] / 2 && b[4] == cy - b[2] / 2);
            const long delta = (long)b[8] - a[8];
            minimum = std::min(minimum, delta);
            maximum = std::max(maximum, delta);
            saved -= delta;
            ++calls;
            if (delta < 0) ++faster; else if (delta == 0) ++equal; else ++slower;
        }
    }
    // Decimal arithmetic is outside the D=0 public input contract. Still
    // compare every old/new observable byte, and verify D itself survives.
    for (unsigned distance = 0; distance < 65536; ++distance) {
        const auto a = before.call(distance, 0, 8 | ((distance & 1) ? 4 : 0));
        const auto b = after.call(distance, 0, 8 | ((distance & 1) ? 4 : 0));
        for (unsigned i = 0; i < 8; ++i) assert(a[i] == b[i]);
    }
    for (unsigned axis = 0; axis < 2; ++axis) {
        for (unsigned span = 0; span < 256; ++span) {
            const int origin = int(axis ? cy : cx) - int(span / 2);
            if (origin < 0 || origin + int(127 * span / 128) > 255) continue;
            for (unsigned value = 0; value < 128; ++value) {
                for (unsigned masked = 0; masked < 2; ++masked) {
                    for (auto* instance : {&before, &after}) {
                        instance->write(instance->address(axis ? "_sy" : "_sx"), span);
                        instance->write(instance->address(axis ? "_top" : "_left"), origin);
                    }
                    const auto a = before.call(value, axis + 1, masked * 4);
                    const auto b = after.call(value, axis + 1, masked * 4);
                    for (unsigned i = 0; i < 9; ++i) assert(a[i] == b[i]);
                    assert(b[5] == unsigned(origin) + value * span / 128 && b[6] == 0);
                }
            }
        }
    }
    before.guards();
    after.guards();
    std::printf("%s shift%u: %llu depth calls (%u faster/%u equal/%u slower), "
                "deltas%ld..%ld, saved%lld; D=1 equivalence, spans/coordinates, "
                "Y/I/D, public state, full main/aux/store/bank guards PASS\n",
                cmos ? "65C02" : "NMOS", shift, calls, faster, equal, slower,
                minimum, maximum, saved);
}
