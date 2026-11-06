/* GPL-3.0. Independent tile model and effective source-access trace.
 * Linked by test_hgr_tile_rows.py against the SDK's NMOS/65C02 models.
 * The host installs no IRQ source, so each decoded load/store executes next.
 * Architectural source reads are recorded; this is not a dummy-bus-cycle log.
 */
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <set>
#include <vector>

using namespace pom2;
using Event = std::pair<unsigned, unsigned>;

static unsigned offset(unsigned y)
{
    return ((y & 7) << 10) + (((y >> 3) & 7) << 7) + (y >> 6) * 40;
}

static unsigned pixel(unsigned i)
{
    return (i / 8 * 61 + (i & 7) * 23 + 7) & 255;
}

struct Model {
    std::array<unsigned char, 1216> maps;
    std::array<unsigned char, 2304> tiles;
    std::array<unsigned char, 16384> screen;
    std::vector<Event> reads, writes;
    bool valid;

    explicit Model(const unsigned char* in)
    {
        const unsigned page = in[0], col = in[1], row = in[2];
        unsigned width = in[3], height = in[4];
        const unsigned count = in[5] | (in[6] << 8), flags = in[8];
        const unsigned mapoff = in[7] * 73 & 255, tileoff = in[7];
        for (unsigned i = 0; i < maps.size(); ++i) maps[i] = (i * 37 + 13) & 255;
        for (unsigned i = 0; i < tiles.size(); ++i) tiles[i] = pixel(i);
        if (count > 0 && count < 256)
            for (unsigned i = 0; i < 960; ++i) maps[mapoff + i] = i % count;
        std::fill(screen.begin(), screen.begin() + 8192, 0xaa);
        std::fill(screen.begin() + 8192, screen.end(), 0x55);
        const bool geometry = col < 40 && row < 24 && width && height;
        if (geometry) {
            width = std::min(width, 40 - col);
            height = std::min(height, 24 - row);
        }
        if ((flags & 8) && geometry)
            maps[mapoff + (row + height - 1) * 40 + col + width - 1] = count & 255;
        valid = geometry && (page == 1 || page == 2)
                && count >= 1 && count <= 256 && !(flags & 7);
        if (valid && count < 256) {
            for (unsigned y = row; y < row + height && valid; ++y) {
                for (unsigned x = col; x < col + width; ++x) {
                    const unsigned at = mapoff + y * 40 + x;
                    reads.emplace_back(0x1400 + at, maps[at]);
                    if (maps[at] >= count) { valid = false; break; }
                }
            }
        }
        if (!valid) return;
        for (unsigned y = row; y < row + height; ++y) {
            for (unsigned x = col; x < col + width; ++x) {
                const unsigned at = mapoff + y * 40 + x, id = maps[at];
                reads.emplace_back(0x1400 + at, id);
                for (unsigned dy = 0; dy < 8; ++dy) {
                    const unsigned source = tileoff + id * 8 + dy;
                    const unsigned dest = (page - 1) * 8192 + offset(y * 8 + dy) + x;
                    reads.emplace_back(0x8000 + source, tiles[source]);
                    writes.emplace_back(0x2000 + dest, tiles[source]);
                    screen[dest] = tiles[source];
                }
            }
        }
    }
};

struct Instance {
    Core core;
    std::map<std::string, unsigned> labels;
    std::vector<unsigned char> image;
    std::set<unsigned> scratch, patches;
    unsigned reads = 0, writes = 0, crossings = 0, reloads = 0;

    unsigned address(const char* name) { return labels.at(std::string(".") + name); }
    unsigned read(unsigned at) { return core.read(at); }
    void write(unsigned at, unsigned value) { core.write(at, (unsigned char)value); }

    Instance(const char* binary, const char* symbols, bool cmos)
        : core(CoreConfig{cmos ? CpuModel::CMOS65C02 : CpuModel::NMOS6502,
                          VideoTiming::NTSC, true})
    {
        probe::labels(labels, symbols);
        std::ifstream stream(binary, std::ios::binary);
        assert(stream);
        image.assign(std::istreambuf_iterator<char>(stream), {});
        assert(!image.empty() && image.size() <= 0x3400);
        std::array<unsigned char, 0xc000> memory;
        memory.fill(0xa5);
        assert(core.writeRam(RamBank::Main, 0, memory.data(), memory.size()));
        memory.fill(0x69);
        assert(core.writeRam(RamBank::Aux, 0, memory.data(), memory.size()));
        assert(core.writeRam(RamBank::Main, 0x6000, image.data(), image.size()));
        for (auto name : {"sp", "ptr1", "ptr2", "ptr3", "ptr4"}) {
            scratch.insert(address(name));
            scratch.insert(address(name) + 1);
        }
        for (auto name : {"tmp1", "tmp2", "tmp3", "tmp4"}) scratch.insert(address(name));
        patches.insert(address("source_low") + 1);
        patches.insert(address("source_high") + 1);
        for (unsigned row = 0; row < 8; ++row) {
            patches.insert(address("draw_store0") + 1 + row * 6);
            patches.insert(address("draw_store0") + 2 + row * 6);
        }
    }

    void run(const unsigned char* in, unsigned serial)
    {
        const Model model(in);
        assert(core.writeRam(RamBank::Main, 0x1400, model.maps.data(), model.maps.size()));
        assert(core.writeRam(RamBank::Main, 0x8000, model.tiles.data(), model.tiles.size()));
        // Set the initial pages independently from the expected final pages.
        std::array<unsigned char, 16384> screen;
        std::fill(screen.begin(), screen.begin() + 8192, 0xaa);
        std::fill(screen.begin() + 8192, screen.end(), 0x55);
        assert(core.writeRam(RamBank::Main, 0x2000, screen.data(), screen.size()));
        const unsigned flags = in[8], count = in[5] | (in[6] << 8);
        const unsigned map = flags & 2 ? 0 : 0x1400 + (in[7] * 73 & 255);
        const unsigned tile = flags & 4 ? 0 : 0x8000 + in[7];
        const unsigned char context[] = {0xa5, (unsigned char)map,
            (unsigned char)(map >> 8), (unsigned char)tile, (unsigned char)(tile >> 8),
            (unsigned char)count, (unsigned char)(count >> 8), 0x5a};
        assert(core.writeRam(RamBank::Main, 0x1000, context, sizeof(context)));
        const unsigned pointer = flags & 1 ? 0 : 0x1001;
        const unsigned char args[] = {in[3], in[2], in[1], in[0],
                                     (unsigned char)pointer, (unsigned char)(pointer >> 8)};
        assert(core.writeRam(RamBank::Main, 0x9000, args, sizeof(args)));
        write(address("sp"), 0);
        write(address("sp") + 1, 0x90);
        if (serial % 3 == 0) {
            const unsigned entry = address("_hgr_tile_restore");
            const unsigned size = address("tile_end") - entry;
            assert(core.writeRam(RamBank::Main, entry, image.data() + entry - 0x6000, size));
            ++reloads;
        }
        std::array<unsigned char, 0xc000> original, actual;
        assert(core.readRam(RamBank::Main, 0, original.data(), original.size()));
        auto state = core.cpuState();
        state.accumulator = in[4];
        state.x = 0x6d;
        state.y = 0x79;
        state.status = 0x20 | ((serial & 1) ? 4 : 0);
        state.stackPointer = 0xfd;
        state.programCounter = address("_hgr_tile_restore");
        state.halted = false;
        core.setCpuState(state);
        write(0x1fe, 0xff);
        write(0x1ff, 3); // Synthetic native return to $0400.
        std::vector<Event> source_reads, screen_writes;
        unsigned steps = 0;
        while (core.cpuState().programCounter != 0x400 && ++steps < 400000) {
            const auto registers = core.cpuState();
            const unsigned pc = registers.programCounter, opcode = read(pc);
            if (opcode == 0xb1) { // LDA (zp),Y: all borrowed map/tile loads.
                const unsigned zp = read(pc + 1);
                const unsigned base = read(zp) | (read((zp + 1) & 255) << 8);
                const unsigned at = (base + registers.y) & 65535;
                if ((at >= 0x1400 && at < 0x1400 + model.maps.size())
                    || (at >= 0x8000 && at < 0x8000 + model.tiles.size())) {
                    source_reads.emplace_back(at, read(at));
                    if ((base & 255) + registers.y > 255) ++crossings;
                }
            }
            const long target = probe::storeTarget(core);
            if (target >= 0) {
                if (target >= 0x2000 && target <= 0x5fff) {
                    assert(opcode == 0x9d || opcode == 0x91);
                    assert((registers.status & 4) == ((serial & 1) ? 4 : 0));
                    screen_writes.emplace_back(target, registers.accumulator);
                } else assert(scratch.count(target) || patches.count(target));
            }
            core.step();
        }
        state = core.cpuState();
        assert(steps < 400000 && state.stackPointer == 255);
        assert(state.accumulator == model.valid && state.x == 0);
        assert((state.status & 12) == ((serial & 1) ? 4 : 0));
        assert((read(address("sp")) | (read(address("sp") + 1) << 8)) == 0x9006);
        assert(source_reads == model.reads);
        assert(screen_writes == model.writes);
        reads += source_reads.size();
        writes += screen_writes.size();
        assert(core.readRam(RamBank::Main, 0, actual.data(), actual.size()));
        for (unsigned at = 0; at < actual.size(); ++at) {
            if (scratch.count(at) || patches.count(at) || (at >= 0x100 && at <= 0x1ff))
                continue;
            if (at >= 0x2000 && at <= 0x5fff) assert(actual[at] == model.screen[at - 0x2000]);
            else assert(actual[at] == original[at]);
        }
        assert(core.readRam(RamBank::Aux, 0, actual.data(), actual.size()));
        for (auto byte : actual) assert(byte == 0x69);
        for (auto at : {0xc013, 0xc014, 0xc016}) assert(!(read(at) & 128));
    }
};

int main(int argc, char** argv)
{
    assert(argc == 7);
    const bool cmos = std::stoi(argv[6]);
    std::ifstream stream(argv[5], std::ios::binary);
    assert(stream);
    const std::vector<unsigned char> cases((std::istreambuf_iterator<char>(stream)), {});
    assert(!cases.empty() && cases.size() % 9 == 0);
    Instance before(argv[1], argv[2], cmos), after(argv[3], argv[4], cmos);
    for (unsigned i = 0; i < cases.size() / 9; ++i) {
        before.run(cases.data() + i * 9, i);
        after.run(cases.data() + i * 9, i);
    }
    assert(before.reads == after.reads && before.writes == after.writes);
    std::printf("%s %zu calls each: %u exact ordered source reads, %u exact ordered screen writes; "
                "indirect-Y crossings old/new %u/%u; %u reloads each; full main/aux/code/source/"
                "context/stack/store/bank/I guards PASS\n", cmos ? "65C02" : "NMOS",
                cases.size() / 9, after.reads, after.writes,
                before.crossings, after.crossings, after.reloads);
}
