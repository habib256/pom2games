/* GPL-3.0. Independent native DHGR transfers/masks: pixels, effective reads,
 * exact ordered stores, real VIA IRQs and complete main/aux/parameter guards.
 * The public wrappers' clipping and C-stack ABI are tested separately.
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

struct Event {
    unsigned bank, address, value;
    bool operator==(const Event& other) const
    {
        return bank == other.bank && address == other.address && value == other.value;
    }
};

struct Case { unsigned bank, count, buffer, screen, serial; };

struct Instance {
    unsigned mode; // 0 write, 1 read, 2 masked sprite
    Core core;
    std::map<std::string, unsigned> labels;
    std::vector<unsigned char> image;
    unsigned calls = 0, reads = 0, writes = 0, irqs = 0;
    unsigned long long cycles = 0;

    unsigned address(const char* name) { return labels.at(std::string(".") + name); }
    unsigned read(unsigned at) { return core.read(at); }
    void write(unsigned at, unsigned value) { core.write(at, value); }

    Instance(const char* binary, const char* symbols, bool cmos,
             const char* rom, unsigned transfer_mode)
        : mode(transfer_mode), core(CoreConfig{cmos ? CpuModel::CMOS65C02 : CpuModel::NMOS6502,
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
        const bool reading = mode == 1, masked = mode == 2;
        const unsigned mask_address = 0x8a00 + ((input.serial * 131 + 17) & 255);
        const unsigned ptr1 = address("ptr1"), ptr2 = address("ptr2"), ptr3 = address("ptr3");
        std::array<unsigned char, 0xc000> before[2], actual[2], expected[2];
        for (unsigned bank = 0; bank < 2; ++bank) {
            for (unsigned at = 0; at < 0xc000; ++at)
                before[bank][at] = (at * 29 + (at >> 8) * 17 + bank * 83 + input.serial * 13) & 255;
            assert(core.writeRam(bank ? RamBank::Aux : RamBank::Main,
                                 0, before[bank].data(), before[bank].size()));
        }
        assert(core.writeRam(RamBank::Main, 0x6000, image.data(), image.size()));
        write(address("_dhgr_addr"), input.screen);
        write(address("_dhgr_addr") + 1, input.screen >> 8);
        write(address("_dhgr_aux"), input.bank);
        write(address("_dhgr_buffer"), input.buffer);
        write(address("_dhgr_buffer") + 1, input.buffer >> 8);
        write(address("_dhgr_count"), input.count);
        write(address("_dhgr_sprite_mask"), mask_address);
        write(address("_dhgr_sprite_mask") + 1, mask_address >> 8);
        const unsigned char trampoline[] = {
            0x8d, 0x03, 0xc0, 0xb1, (unsigned char)ptr1, 0x8d, 0x02, 0xc0, 0x60
        };
        assert(core.writeRam(RamBank::Main, address("aux_read"), trampoline, sizeof(trampoline)));
        // PHA/TXA/PHA/TYA/PHA; test RAMRD|RAMWRT; acknowledge VIA T1;
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
        write(0xc404, 0);
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
        std::vector<Event> wanted_reads, wanted_writes, observed_reads, observed_writes;
        unsigned screen = input.screen, bank = input.bank;
        for (unsigned index = 0; index < (input.count ? input.count : 256); ++index) {
            const unsigned buffer = input.buffer + index;
            if (masked) {
                const unsigned raw = expected[0][mask_address + index], bits = (~raw) & 127;
                wanted_reads.push_back({0, mask_address + index, raw});
                if (bits) {
                    const unsigned data = expected[0][buffer];
                    wanted_reads.push_back({0, buffer, data});
                    unsigned value = data & bits;
                    if (bits != 127) {
                        const unsigned old = expected[!!bank][screen];
                        wanted_reads.push_back({!!bank, screen, old});
                        value |= old & ~bits;
                    }
                    wanted_writes.push_back({!!bank, screen, value});
                    expected[!!bank][screen] = value;
                }
            } else if (reading) {
                const unsigned value = expected[!!bank][screen];
                wanted_reads.push_back({!!bank, screen, value});
                wanted_writes.push_back({0, buffer, value & 127});
                expected[0][buffer] = value & 127;
            } else {
                const unsigned value = expected[0][buffer];
                wanted_reads.push_back({0, buffer, value});
                wanted_writes.push_back({!!bank, screen, value & 127});
                expected[!!bank][screen] = value & 127;
            }
            // Model the historical raw bank XOR, including all values >=2.
            if (!bank) ++screen;
            bank ^= 1;
        }
        const unsigned status = 0x20 | ((input.serial & 1) ? 4 : 0)
                                     | ((input.serial & 2) ? 8 : 0);
        auto state = core.cpuState();
        state.accumulator = 0xa5;
        state.x = 0x5a;
        state.y = 0x99;
        state.status = status;
        state.stackPointer = 0xfd;
        state.programCounter = address(masked ? "_dhgr_sprite_asm"
                                     : reading ? "_dhgr_read_block_asm" : "_dhgr_write_block_asm");
        state.halted = false;
        core.setCpuState(state);
        const auto start = state.cycles;
        const unsigned load_pointer = reading ? ptr1 : ptr2;
        const unsigned store_pointer = reading ? ptr2 : ptr1;
        unsigned steps = 0;
        while (core.cpuState().programCounter != 0x400 && ++steps < 400000) {
            const auto registers = core.cpuState();
            const unsigned opcode = read(registers.programCounter);
            const unsigned operand = read(registers.programCounter + 1);
            // The new masked path uses AND (data),Y; the old one uses LDA.
            const bool consumes = masked
                ? ((opcode == 0xb1 || opcode == 0x31)
                    && (operand == ptr1 || operand == ptr2 || operand == ptr3))
                : (opcode == 0xb1 && operand == load_pointer);
            unsigned source = 0, value = 0;
            if (consumes) {
                source = (read(operand) | (read(operand + 1) << 8)) + registers.y;
                value = read(source);
            }
            const auto target = probe::storeTarget(core);
            const unsigned read_bank = bool(read(0xc013) & 128);
            const unsigned write_bank = bool(read(0xc014) & 128);
            const bool stores = opcode == 0x91 && operand == store_pointer;
            core.step();
            // A pending IRQ consumes the step instead of the decoded opcode.
            // No tested routine calls/jumps to the handler at $0900.
            if (core.cpuState().programCounter == 0x900) continue;
            if (consumes) observed_reads.push_back({read_bank, source, value});
            if (stores) {
                assert(registers.status & 4);
                observed_writes.push_back({write_bank, (unsigned)target, registers.accumulator});
            }
        }
        state = core.cpuState();
        assert(steps < 400000 && state.stackPointer == 255);
        assert((state.status & 12) == (status & 12));
        assert(observed_reads == wanted_reads);
        assert(observed_writes == wanted_writes);
        cycles += state.cycles - start;
        reads += observed_reads.size();
        writes += observed_writes.size();
        ++calls;
        write(0xc40e, 0x7f);
        write(0xc404, 0);
        irqs += read(0x1002) | (read(0x1003) << 8);
        assert(read(0x1004) == 0);
        const unsigned scratch_end = address("aux_read");
        for (unsigned which = 0; which < 2; ++which) {
            assert(core.readRam(which ? RamBank::Aux : RamBank::Main,
                                0, actual[which].data(), actual[which].size()));
            for (unsigned at = 0; at < 0xc000; ++at) {
                // Only the active hardware stack, declared cc65 scratch, and
                // IRQ counters may differ from the independently modeled RAM.
                const bool scratch = (at >= 0x1f6 && at < 0x200)
                    || (at >= ptr1 && at < scratch_end)
                    || (irq && at >= 0x1002 && at <= 0x1004);
                if (!which && scratch) continue;
                assert(actual[which][at] == expected[which][at]);
            }
        }
        for (unsigned at : {0xc013, 0xc014, 0xc016, 0xc018}) assert(!(read(at) & 128));
    }
};

int main(int argc, char** argv)
{
    assert(argc == 9);
    const bool cmos = std::stoi(argv[6]), irq = std::stoi(argv[7]);
    const unsigned mode = std::stoi(argv[8]);
    assert(mode < 3);
    Instance before(argv[1], argv[2], cmos, argv[5], mode);
    Instance after(argv[3], argv[4], cmos, argv[5], mode);
    std::vector<Case> cases;
    unsigned serial = 0;
    const auto add = [&](unsigned bank, unsigned count, unsigned buffer, unsigned screen) {
        cases.push_back({bank, count, buffer, screen, serial++});
    };
    for (unsigned bank = 0; bank < 2; ++bank)
        for (unsigned page = 1; page <= 2; ++page)
            for (unsigned count = 0; count < 256; ++count)
                add(bank, count, 0x8000 + ((count * 73 + page * 17) & 255),
                    page * 0x2000 + 0xf0 + (count & 15));
    for (unsigned bank = 2; bank < 256; ++bank)
        for (unsigned count : {0, 1, 2, 3, 127, 128, 255})
            add(bank, count, 0x8000 + ((bank * 37 + count) & 255),
                0x4000 + ((bank * 13) & 255));
    for (unsigned low = 0; low < 256; ++low)
        for (unsigned bank = 0; bank < 2; ++bank)
            add(bank, (low * 131) & 255, 0x8000 + low, 0x2000 + low);
    // Buffer aliases precede and follow screen writes/reads independently.
    for (unsigned bank = 0; bank < 2; ++bank)
        for (unsigned shift = 0; shift < 8; ++shift) {
            add(bank, 0, 0x2100 + shift, 0x20fc);
            add(bank, 0, 0x20f0 + shift, 0x20fc);
        }
    unsigned faster = 0, equal = 0, slower = 0;
    long min_delta = std::numeric_limits<long>::max();
    long max_delta = std::numeric_limits<long>::min();
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
        if (delta > 0 && !irq)
            std::printf("Raw slow case: bank=%u count=%u buffer=$%04X screen=$%04X delta=%ld\n",
                        input.bank, input.count, input.buffer, input.screen, delta);
    }
    assert(before.reads == after.reads && before.writes == after.writes);
    if (irq) assert(before.irqs > 100 && after.irqs > 100);
    std::printf("%s %s IRQ=%u: %u calls/source, %u ordered reads + %u ordered writes/source; "
                "cycles %llu -> %llu; IRQs %u/%u; complete RAM/code/params/banks/I/D/stack guards PASS\n",
                cmos ? "65C02" : "NMOS", mode == 2 ? "masked" : mode ? "read" : "write", irq,
                after.calls, after.reads, after.writes, before.cycles, after.cycles,
                before.irqs, after.irqs);
    std::printf("Per-call cycles %u faster/%u equal/%u slower, range %ld..%ld\n",
                faster, equal, slower, min_delta, max_delta);
}
