/* GPL-3.0. Independent native DHGR span pixels, ordered stores and RAM guards.
 * Linked by test_dhgr_span_native.py against both SDK CPU models. The custom
 * ROM dispatches real VIA IRQs directly to a guarded, register-saving handler.
 */
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <vector>

using namespace pom2;

struct Event {
    unsigned bank, address, value;
    bool operator==(const Event& other) const
    {
        return bank == other.bank && address == other.address && value == other.value;
    }
};

static unsigned offset(unsigned y)
{
    return ((y & 7) << 10) + ((y & 56) << 4) + (y >> 6) * 40;
}

struct Case { unsigned x, end, y, rows, page, serial; };

struct Instance {
    Core core;
    std::map<std::string, unsigned> labels;
    std::vector<unsigned char> image;
    unsigned calls = 0, writes = 0, irqs = 0;
    unsigned long long cycles = 0;

    unsigned address(const char* name) { return labels.at(std::string(".") + name); }
    unsigned read(unsigned at) { return core.read(at); }
    void write(unsigned at, unsigned value) { core.write(at, value); }

    Instance(const char* binary, const char* symbols, bool cmos, const char* rom)
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
        std::array<unsigned char, 0xc000> before[2], actual[2], expected[2];
        for (unsigned bank = 0; bank < 2; ++bank) {
            for (unsigned at = 0; at < 0xc000; ++at)
                before[bank][at] = (at * 29 + (at >> 8) * 17 + bank * 83 + input.serial * 13) & 255;
            assert(core.writeRam(bank ? RamBank::Aux : RamBank::Main,
                                 0, before[bank].data(), before[bank].size()));
        }
        // Reload the entire image on every call; no hidden SMC state survives.
        assert(core.writeRam(RamBank::Main, 0x6000, image.data(), image.size()));
        write(address("_dhgr_base"), input.page * 0x20);
        write(address("_dhgr_span_x"), input.x);
        write(address("_dhgr_span_x") + 1, input.x >> 8);
        write(address("_dhgr_span_end"), input.end);
        write(address("_dhgr_span_end") + 1, input.end >> 8);
        unsigned patterns[4];
        for (unsigned index = 0; index < 4; ++index) {
            patterns[index] = (input.serial * 37 + index * 29 + (input.serial >> 3)) & 127;
            write(address("_dhgr_pattern") + index, patterns[index]);
        }
        const unsigned zp = address("aux_read"), pointer = address("ptr1");
        const unsigned char trampoline[] = {
            0x8d, 0x03, 0xc0, 0xb1, (unsigned char)pointer, 0x8d, 0x02, 0xc0, 0x60
        };
        assert(core.writeRam(RamBank::Main, zp, trampoline, sizeof(trampoline)));
        // PHA/TXA/PHA/TYA/PHA; check RAMRD|RAMWRT; acknowledge VIA T1;
        // increment a 16-bit tick counter; restore Y/X/A; SEC; RTI. No ZP use.
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
        write(0xc404, 0); // End any earlier timer.
        if (irq) {
            write(0xc40b, 0x40);
            write(0xc404, 0x63);
            write(0xc405, 0);
            write(0xc40e, 0xc0);
        }
        for (unsigned bank = 0; bank < 2; ++bank) {
            assert(core.readRam(bank ? RamBank::Aux : RamBank::Main,
                                0, before[bank].data(), before[bank].size()));
            expected[bank] = before[bank];
        }
        std::vector<Event> wanted, observed;
        const unsigned first = input.x / 7, last = input.end / 7;
        for (unsigned row = input.y; row < input.y + input.rows; ++row) {
            std::vector<Event> edges, full[2];
            for (unsigned byte = first; byte <= last; ++byte) {
                unsigned mask = 0;
                for (unsigned bit = 0; bit < 7; ++bit)
                    if (byte * 7 + bit >= input.x && byte * 7 + bit <= input.end)
                        mask |= 1 << bit;
                const unsigned bank = !(byte & 1);
                const unsigned at = input.page * 0x2000 + offset(row) + byte / 2;
                unsigned value = (expected[bank][at] & ~mask) | (patterns[byte & 3] & mask);
                if (mask == 127) value = patterns[byte & 3];
                expected[bank][at] = value;
                const Event event{bank, at, value};
                if (mask == 127) full[bank].push_back(event);
                else edges.push_back(event);
            }
            // Partial right/left edges precede the aux and main interiors.
            wanted.insert(wanted.end(), edges.rbegin(), edges.rend());
            wanted.insert(wanted.end(), full[1].begin(), full[1].end());
            wanted.insert(wanted.end(), full[0].begin(), full[0].end());
        }
        auto state = core.cpuState();
        state.accumulator = input.y;
        state.x = input.rows;
        state.y = (input.serial * 17) & 255;
        state.status = 0x20 | ((input.serial & 1) ? 4 : 0);
        state.stackPointer = 0xfd;
        state.programCounter = address("_dhgr_span_asm");
        state.halted = false;
        core.setCpuState(state);
        const auto start = state.cycles;
        unsigned steps = 0;
        while (core.cpuState().programCounter != 0x400 && ++steps < 400000) {
            const auto registers = core.cpuState();
            const unsigned opcode = read(registers.programCounter);
            const auto target = probe::storeTarget(core);
            const unsigned bank = bool(read(0xc014) & 128);
            core.step();
            // A pending IRQ consumes this step instead of the decoded opcode.
            // The handler is entered only through the vector, never a JSR/JMP.
            if (core.cpuState().programCounter == 0x900) continue;
            if (target >= 0x2000 && target <= 0x5fff) {
                assert(opcode == 0x91);
                assert(registers.status & 4);
                observed.push_back({bank, (unsigned)target, registers.accumulator});
            }
        }
        state = core.cpuState();
        assert(steps < 400000 && state.stackPointer == 255);
        assert((state.status & 12) == ((input.serial & 1) ? 4 : 0));
        assert(observed == wanted);
        cycles += state.cycles - start;
        writes += observed.size();
        ++calls;
        write(0xc40e, 0x7f);
        write(0xc404, 0);
        irqs += read(0x1002) | (read(0x1003) << 8);
        assert(read(0x1004) == 0);
        const unsigned scratch_begin = address("ptr1"), scratch_end = address("aux_read");
        const unsigned private_begin = address("span_bss_begin") + 4;
        const unsigned private_end = address("span_bss_end"), first_state = address("_dhgr_first");
        for (unsigned bank = 0; bank < 2; ++bank) {
            assert(core.readRam(bank ? RamBank::Aux : RamBank::Main,
                                0, actual[bank].data(), actual[bank].size()));
            for (unsigned at = 0; at < 0xc000; ++at) {
                // Native JSR/PHP + IRQ frame/handler need at most $1F6..$1FF.
                // Endpoints, patterns, base, tables and the aux trampoline stay guarded.
                const bool scratch = (at >= 0x1f6 && at < 0x200)
                    || (at >= scratch_begin && at < scratch_end)
                    || (at >= private_begin && at < private_end)
                    || (at >= first_state && at < first_state + 4)
                    || (irq && at >= 0x1002 && at <= 0x1004);
                if (!bank && scratch) continue;
                assert(actual[bank][at] == expected[bank][at]);
            }
        }
        for (unsigned at : {0xc013, 0xc014, 0xc016, 0xc018}) assert(!(read(at) & 128));
    }
};

int main(int argc, char** argv)
{
    assert(argc == 8);
    const bool cmos = std::stoi(argv[6]), irq = std::stoi(argv[7]);
    Instance before(argv[1], argv[2], cmos, argv[5]);
    Instance after(argv[3], argv[4], cmos, argv[5]);
    std::vector<Case> cases;
    unsigned serial = 0;
    const auto add = [&](unsigned x, unsigned end, unsigned y, unsigned rows, unsigned page) {
        cases.push_back({x, end, y, rows, page, serial++});
    };
    for (unsigned x = 0; x < 560; ++x) {
        for (unsigned page = 1; page <= 2; ++page) {
            const unsigned y = x * 13 % 192;
            add(x, x, y, 1, page);
            add(x, std::min(559u, x + 6 + (x % 19) * 7), y,
                std::min(192 - y, 1 + x % 9), page);
        }
    }
    for (unsigned x = 0; x < 28; ++x)
        for (unsigned end = x; end < 80; end += 7)
            add(x, end, 0, 192, 1 + (x & 1));
    add(0, 559, 0, 192, 1);
    add(0, 559, 0, 192, 2);
    unsigned faster = 0, equal = 0, slower = 0;
    long min_delta = 0, max_delta = 0;
    for (const auto& input : cases) {
        const auto old_cycles = before.cycles, new_cycles = after.cycles;
        before.run(input, irq);
        after.run(input, irq);
        const long delta = long(after.cycles - new_cycles) - long(before.cycles - old_cycles);
        faster += delta < 0;
        equal += delta == 0;
        slower += delta > 0;
        min_delta = std::min(min_delta, delta);
        max_delta = std::max(max_delta, delta);
    }
    assert(before.writes == after.writes);
    if (irq) assert(before.irqs > 100 && after.irqs > 100);
    std::printf("%s IRQ=%u: %u calls/source, %u ordered stores/source; cycles %llu -> %llu; "
                "IRQs %u/%u; complete RAM/code/params/banks/I/D/stack guards PASS\n",
                cmos ? "65C02" : "NMOS", irq, after.calls, after.writes,
                before.cycles, after.cycles, before.irqs, after.irqs);
    std::printf("Per-call cycles: %u faster/%u equal/%u slower, range %ld..%ld\n",
                faster, equal, slower, min_delta, max_delta);
}
