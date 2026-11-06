/* GPL-3.0. Native glyph8 oracle: all byte rows, phases, pages, byte-Y wrap,
 * font/page crossings and font data modified by earlier framebuffer writes.
 * Tables have 256 guarded entries: 0..191 are normal HGR rows; the remaining
 * entries use distinct safe RAM offsets to define the raw byte-index domain.
 * Both sources use the same deliberately unaligned table addresses.
 */
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <limits>
#include <vector>

using namespace pom2;
using Event = std::pair<unsigned, unsigned>;

struct Case {
    unsigned top, column, phase, page, seed, kind, source, serial;
    bool alias;
};

static unsigned offset(unsigned y)
{
    return ((y & 7) << 10) + ((y & 56) << 4) + (y >> 6) * 40;
}

static unsigned rowOffset(unsigned y)
{
    return y < 192 ? offset(y) : offset(y - 192) + 1;
}

static unsigned pattern(const Case& input, unsigned row)
{
    if (input.kind == 0) return input.seed;
    if (input.kind == 1) return row % 3 == 0 ? 0 : (input.seed + row * 37) & 255;
    if (input.kind == 2) return (row & 1) ? 255 : 0;
    return ((input.seed + row * 37) & 255) | 1;
}

struct Instance {
    Core core;
    std::map<std::string, unsigned> labels;
    std::vector<unsigned char> image;
    unsigned calls = 0, reads = 0, writes = 0, irqs = 0, alias_changes = 0, deferred = 0;
    unsigned long long cycles = 0;

    unsigned address(const char* name) { return labels.at(std::string(".") + name); }
    unsigned read(unsigned at) { return core.read(at); }
    void write(unsigned at, unsigned value) { core.write(at, value); }

    Instance(const char* binary, const char* symbols, const char* rom, bool cmos)
        : core(CoreConfig{cmos ? CpuModel::CMOS65C02 : CpuModel::NMOS6502,
                          VideoTiming::NTSC, true})
    {
        probe::labels(labels, symbols);
        std::ifstream stream(binary, std::ios::binary);
        image.assign(std::istreambuf_iterator<char>(stream), {});
        assert(!image.empty());
        assert(core.loadRom(rom));
        assert(core.attachMockingboard());
    }

    void run(const Case& input, bool irq)
    {
        std::array<unsigned char, 0xc000> original[2], actual[2], expected[2];
        for (unsigned bank = 0; bank < 2; ++bank) {
            for (unsigned at = 0; at < 0xc000; ++at)
                original[bank][at] = (at * 29 + (at >> 8) * 17 + bank * 83 + input.serial * 13) & 255;
            assert(core.writeRam(bank ? RamBank::Aux : RamBank::Main,
                                 0, original[bank].data(), original[bank].size()));
        }
        assert(core.writeRam(RamBank::Main, 0x6000, image.data(), image.size()));
        for (unsigned row = 0; row < 8; ++row) write(input.source + row, pattern(input, row));
        write(address("_hgr_g_glyph"), input.source);
        write(address("_hgr_g_glyph") + 1, input.source >> 8);
        write(address("_hgr_g_col"), input.column);
        write(address("_hgr_g_bit"), input.phase);
        write(address("_hgr_g_y"), input.top);
        for (unsigned y = 0; y < 256; ++y) {
            const unsigned at = input.page * 0x2000 + rowOffset(y);
            write(address("_hgr_rowlo") + y, at);
            write(address("_hgr_rowhi") + y, at >> 8);
        }
        // Save A/X/Y, check main banks, acknowledge VIA T1, count IRQs,
        // restore Y/X/A, SEC, RTI. The handler borrows no ZP scratch.
        const unsigned char handler[] = {
            0x48, 0x8a, 0x48, 0x98, 0x48,
            0xad, 0x13, 0xc0, 0x0d, 0x14, 0xc0, 0x29, 0x80,
            0xf0, 0x03, 0xee, 0x04, 0x10,
            0xad, 0x04, 0xc4, 0xee, 0x02, 0x10, 0xd0, 0x03, 0xee, 0x03, 0x10,
            0x68, 0xa8, 0x68, 0xaa, 0x68, 0x38, 0x40
        };
        assert(core.writeRam(RamBank::Main, 0x900, handler, sizeof(handler)));
        write(0x1002, 0);
        write(0x1003, 0);
        write(0x1004, 0);
        write(0x1fe, 0xff);
        write(0x1ff, 3); // Synthetic native return to $0400.
        write(0xc40e, 0x7f);
        write(0xc404, 0);
        if (irq) {
            write(0xc40b, 0x40);
            write(0xc404, 0x63);
            write(0xc405, 0);
            write(0xc40e, 0xc0);
        }
        for (unsigned bank = 0; bank < 2; ++bank) {
            assert(core.readRam(bank ? RamBank::Aux : RamBank::Main,
                                0, original[bank].data(), original[bank].size()));
            expected[bank] = original[bank];
        }
        std::vector<Event> wanted_reads, wanted_writes, observed_reads, observed_writes;
        for (unsigned row = 0; row < 8; ++row) {
            // Read the current model memory: an earlier OR may have changed
            // a future glyph byte when the font aliases the framebuffer.
            const unsigned bits = expected[0][input.source + row];
            if (input.alias && bits != pattern(input, row)) ++alias_changes;
            wanted_reads.emplace_back(input.source + row, bits);
            const unsigned at = input.page * 0x2000 + rowOffset((input.top + row) & 255) + input.column;
            unsigned masks[2] = {};
            for (unsigned bit = 0; bit < 8; ++bit) {
                if (bits & (1 << bit)) {
                    const unsigned dot = input.phase + bit;
                    masks[dot / 7] |= 1 << (dot % 7);
                }
            }
            for (unsigned byte = 0; byte < 2; ++byte) {
                if (!masks[byte]) continue;
                wanted_reads.emplace_back(at + byte, expected[0][at + byte]);
                expected[0][at + byte] |= masks[byte];
                wanted_writes.emplace_back(at + byte, expected[0][at + byte]);
            }
        }
        auto state = core.cpuState();
        state.accumulator = 0xa5;
        state.x = 0x5a;
        state.y = 0x99;
        state.status = 0x20 | ((input.serial & 1) ? 4 : 0); // D=0 is the HGR ABI.
        state.stackPointer = 0xfd;
        state.programCounter = address("_hgr_blit_glyph8");
        state.halted = false;
        core.setCpuState(state);
        const auto begin = state.cycles;
        const unsigned glyph = address("_hgr_g_glyph"), destination = address("ptr1");
        unsigned steps = 0;
        while (core.cpuState().programCounter != 0x400 && ++steps < 10000) {
            const auto registers = core.cpuState();
            const unsigned opcode = read(registers.programCounter);
            const unsigned operand = read(registers.programCounter + 1);
            const bool consumes = (opcode == 0xb1 && operand == glyph)
                               || (opcode == 0x11 && operand == destination);
            unsigned read_at = 0, value = 0;
            if (consumes) {
                read_at = (read(operand) | (read(operand + 1) << 8)) + registers.y;
                value = read(read_at);
            }
            const auto target = probe::storeTarget(core);
            const bool stores = opcode == 0x91 && operand == destination;
            assert(!(read(0xc013) & 128) && !(read(0xc014) & 128));
            core.step();
            const auto after = core.cpuState();
            if (after.programCounter == 0x901
                && (registers.programCounter < 0x900
                    || registers.programCounter >= 0x900 + sizeof(handler))) {
                // SDK step services IRQ, then executes the handler's first
                // PHA. Require the actual vector, opcode, saved PC, saved A,
                // exact four pushes and I transition. An address alone never
                // exempts a decoded operation from the ordered trace.
                assert(read(0x900) == 0x48);
                assert((read(0xfffe) | (read(0xffff) << 8)) == 0x900);
                assert(!(registers.status & 4) && (after.status & 4));
                const unsigned stack = registers.stackPointer;
                assert(read(0x100 | ((stack - 3) & 255)) == registers.accumulator);
                const unsigned saved_pc = read(0x100 | ((stack - 1) & 255))
                                        | (read(0x100 | stack) << 8);
                assert(saved_pc == registers.programCounter);
                assert(after.stackPointer == ((stack - 4) & 255));
                if (consumes || stores) ++deferred;
                continue;
            }
            if (consumes) observed_reads.emplace_back(read_at, value);
            if (stores) {
                assert(bool(registers.status & 4) == bool(input.serial & 1));
                observed_writes.emplace_back(target, registers.accumulator);
            }
        }
        state = core.cpuState();
        assert(steps < 10000 && state.stackPointer == 255);
        assert((state.status & 12) == ((input.serial & 1) ? 4 : 0));
        assert(observed_reads == wanted_reads);
        if (observed_writes != wanted_writes) {
            std::array<unsigned char, 0x4000> screen;
            assert(core.readRam(RamBank::Main, 0x2000, screen.data(), screen.size()));
            const bool pixels = std::equal(screen.begin(), screen.end(), expected[0].begin() + 0x2000);
            std::fprintf(stderr, "ORDER REJECT serial=%u live_irqs=%u pixels_match=%u actual=%zu expected=%zu\n",
                         input.serial, read(0x1002) | (read(0x1003) << 8), pixels,
                         observed_writes.size(), wanted_writes.size());
        }
        assert(observed_writes == wanted_writes);
        cycles += state.cycles - begin;
        reads += observed_reads.size();
        writes += observed_writes.size();
        ++calls;
        write(0xc40e, 0x7f);
        write(0xc404, 0);
        irqs += read(0x1002) | (read(0x1003) << 8);
        assert(read(0x1004) == 0);
        std::array<bool, 256> scratch{};
        for (unsigned at : {destination, destination + 1,
                            address("tmp1"), address("tmp2"), address("tmp3")}) {
            assert(at < scratch.size());
            scratch[at] = true;
        }
        for (unsigned bank = 0; bank < 2; ++bank) {
            assert(core.readRam(bank ? RamBank::Aux : RamBank::Main,
                                0, actual[bank].data(), actual[bank].size()));
            for (unsigned at = 0; at < 0xc000; ++at) {
                if (!bank && ((at < scratch.size() && scratch[at]) || (at >= 0x1f8 && at < 0x200)
                    || (irq && at >= 0x1002 && at <= 0x1004))) continue;
                assert(actual[bank][at] == expected[bank][at]);
            }
        }
        for (unsigned at : {0xc013, 0xc014, 0xc016, 0xc018, 0xc01c}) assert(!(read(at) & 128));
    }
};

int main(int argc, char** argv)
{
    assert(argc == 8);
    const bool cmos = std::stoi(argv[6]), irq = std::stoi(argv[7]);
    Instance before(argv[1], argv[2], argv[5], cmos);
    Instance after(argv[3], argv[4], argv[5], cmos);
    std::vector<Case> cases;
    unsigned serial = 0;
    const auto add = [&](unsigned top, unsigned column, unsigned phase, unsigned page,
                         unsigned seed, unsigned kind, unsigned font) {
        cases.push_back({top, column, phase, page, seed, kind,
                         font < 256 ? 0x8000 + font : font, serial++, font >= 256});
    };
    for (unsigned top = 0; top < 256; ++top)
        for (unsigned phase = 0; phase < 7; ++phase)
            for (unsigned page = 1; page <= 2; ++page)
                add(top, (top * 7 + phase) % 39, phase, page, (top * 37 + phase * 13) & 255,
                    1, (top * 73 + phase * 17) & 255);
    for (unsigned seed = 0; seed < 256; ++seed)
        for (unsigned phase = 0; phase < 7; ++phase)
            for (unsigned page = 1; page <= 2; ++page)
                add((seed * 17 + phase) & 255, (seed * 13 + phase) % 39, phase, page, seed,
                    0, (seed * 73 + phase * 17) & 255);
    for (unsigned column = 0; column < 39; ++column)
        for (unsigned phase = 0; phase < 7; ++phase)
            for (unsigned page = 1; page <= 2; ++page)
                for (unsigned kind = 0; kind < 3; ++kind)
                    add(184, column, phase, page, kind == 0 ? 0 : 255,
                        kind == 2 ? 2 : 0, (column * 19 + phase) & 255);
    for (unsigned page = 1; page <= 2; ++page)
        for (unsigned top : {0, 1, 7, 63, 64, 127, 128, 184, 249, 255})
            for (unsigned phase = 0; phase < 7; ++phase)
                for (unsigned column : {0, 1, 30, 38})
                    for (int shift : {-2, -1, 0, 1, 2, 4})
                        add(top, column, phase, page, (top * 37 + column * 13 + phase) & 255,
                            3, page * 0x2000 + rowOffset(top) + column + shift);
    unsigned faster = 0, equal = 0, slower = 0;
    long minimum = std::numeric_limits<long>::max(), maximum = std::numeric_limits<long>::min();
    for (const auto& input : cases) {
        const auto old_cycles = before.cycles, new_cycles = after.cycles;
        before.run(input, irq);
        after.run(input, irq);
        const long delta = long(after.cycles - new_cycles) - long(before.cycles - old_cycles);
        faster += delta < 0;
        equal += delta == 0;
        slower += delta > 0;
        minimum = std::min(minimum, delta);
        maximum = std::max(maximum, delta);
    }
    assert(before.reads == after.reads && before.writes == after.writes);
    assert(before.alias_changes == after.alias_changes && after.alias_changes > 100);
    if (irq) assert(before.irqs > 100 && after.irqs > 100);
    std::printf("%s IRQ=%u %u calls/source, %u exact effective glyph/pixel reads + %u ordered stores/source; "
                "cycles %llu -> %llu; IRQs %u/%u; full main/aux/code/tables/source/params/stack/bank/I/D guards PASS\n",
                cmos ? "65C02" : "NMOS", irq, after.calls, after.reads, after.writes,
                before.cycles, after.cycles, before.irqs, after.irqs);
    std::printf("%u alias-modified glyph bytes consumed/source; decoded IRQ deferrals %u/%u\n",
                after.alias_changes, before.deferred, after.deferred);
    std::printf("Per-call cycles: %u faster/%u equal/%u slower, range %ld..%ld\n",
                faster, equal, slower, minimum, maximum);
}
