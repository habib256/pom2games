// a2shot — scripted headless Apple II+ runs on the POM2 core SDK.
//
// Boots a DOS 3.3 disk under the II+ ROM, then walks a script of steps:
//
//   wait:N          run N video frames (17030 cycles each, ~1/60 s)
//   key:TEXT        type TEXT (\r = RETURN, \e = ESC, \< / \> = left / right)
//   shot:FILE.png   render the screen to a PNG (2x vertical, 280/560 wide)
//   peek:ADDR[:LEN] hex-dump guest memory (bus reads, may have side effects)
//   joy:X,Y         joystick axes in [-1,1]      btn:N,0|1  game-port button
//   reset           press RESET (warm: the 6502 RESET line)
//   pc              print the program counter
//   until:ADDR:N    run until PC reaches ADDR, with a limit of N video frames
//   press:TEXT      queue keys without running (for exact until checkpoints)
//
//   a2shot --disk GAME.dsk wait:600 key:" " wait:60 shot:title.png
//
// The disk is copied first: POM2 writes changes back to images, and a test
// must not modify the disk it checks. The ROMs come from roms/ next to this
// binary (apple2p.rom, disk2.rom, diskii_p6.rom; with --iie apple2e.rom and
// apple2e_char.rom), or from --roms DIR.
//
// --iie boots an enhanced Apple //e (65C02, 80-column card with aux memory)
// instead of the ][+.
//
// The run is deterministic: no threads, no wall-clock pacing.
#include <pom2/core.hpp>

#include <unistd.h>
#include <zlib.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

const int kCyclesPerFrame = 17030;

void put32(std::vector<unsigned char>& v, unsigned long x)
{
    v.push_back((x >> 24) & 0xFF); v.push_back((x >> 16) & 0xFF);
    v.push_back((x >> 8) & 0xFF);  v.push_back(x & 0xFF);
}

void chunk(std::vector<unsigned char>& png, const char* type,
           const std::vector<unsigned char>& data)
{
    put32(png, data.size());
    std::vector<unsigned char> body(type, type + 4);
    body.insert(body.end(), data.begin(), data.end());
    png.insert(png.end(), body.begin(), body.end());
    put32(png, crc32(0L, body.data(), static_cast<uInt>(body.size())));
}

bool writePng(const std::string& path, const pom2::FramebufferView& fb)
{
    const int w = fb.width, h = fb.height * 2;         // double rows: 4:3-ish
    std::vector<unsigned char> raw;
    raw.reserve(static_cast<size_t>(h) * (w * 3 + 1));
    for (int y = 0; y < h; ++y) {
        raw.push_back(0);                               // filter: none
        const std::uint32_t* row = fb.pixels + (y / 2) * fb.width;
        for (int x = 0; x < w; ++x) {
            raw.push_back(row[x] & 0xFF);
            raw.push_back((row[x] >> 8) & 0xFF);
            raw.push_back((row[x] >> 16) & 0xFF);
        }
    }
    uLongf zlen = compressBound(static_cast<uLong>(raw.size()));
    std::vector<unsigned char> z(zlen);
    if (compress2(z.data(), &zlen, raw.data(), static_cast<uLong>(raw.size()), 9) != Z_OK)
        return false;
    z.resize(zlen);

    std::vector<unsigned char> png = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n'};
    std::vector<unsigned char> ihdr;
    put32(ihdr, w); put32(ihdr, h);
    ihdr.insert(ihdr.end(), {8, 2, 0, 0, 0});           // 8-bit RGB
    chunk(png, "IHDR", ihdr);
    chunk(png, "IDAT", z);
    chunk(png, "IEND", {});
    FILE* f = std::fopen(path.c_str(), "wb");
    if (!f) return false;
    const bool ok = std::fwrite(png.data(), 1, png.size(), f) == png.size();
    return std::fclose(f) == 0 && ok;
}

std::string unescape(const std::string& s)
{
    std::string out;
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] != '\\' || i + 1 == s.size()) { out += s[i]; continue; }
        switch (s[++i]) {
            case 'r': out += '\r'; break;
            case 'e': out += '\x1B'; break;
            case '<': out += '\x08'; break;             // left arrow
            case '>': out += '\x15'; break;             // right arrow
            default:  out += s[i]; break;
        }
    }
    return out;
}

} // namespace

int main(int argc, char** argv)
{
    std::string exe = argv[0];
    const size_t slash = exe.rfind('/');
    std::string roms = (slash == std::string::npos ? std::string(".") : exe.substr(0, slash))
                     + "/roms";
    std::string disk;
    bool iie = false;
    std::vector<std::string> script;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--roms" && i + 1 < argc) roms = argv[++i];
        else if (a == "--disk" && i + 1 < argc) disk = argv[++i];
        else if (a == "--iie") iie = true;
        else script.push_back(a);
    }
    if (disk.empty()) {
        std::fprintf(stderr, "usage: a2shot [--iie] [--roms DIR] --disk X.dsk step...\n");
        return 2;
    }

    // POM2 writes disk changes back to the image file. A test must never
    // modify the disk it checks (a SAVE in one run corrupted the next run's
    // game), so boot a private copy and delete it on the way out.
    char tmpl[] = "/tmp/a2shot-XXXXXX";
    const int fd = mkstemp(tmpl);
    if (fd < 0) { std::perror("mkstemp"); return 1; }
    close(fd);
    const std::string copy = tmpl;
    {
        std::ifstream in(disk, std::ios::binary);
        std::ofstream out(copy, std::ios::binary);
        out << in.rdbuf();
        if (!in || !out) {
            std::fprintf(stderr, "cannot copy %s\n", disk.c_str());
            std::remove(copy.c_str());
            return 1;
        }
    }
    struct Cleanup { std::string p; ~Cleanup() { std::remove(p.c_str()); } } cleanup{copy};

    pom2::CoreConfig config;
    if (iie) {
        config.cpu = pom2::CpuModel::CMOS65C02;
        config.iieMemory = true;
    }
    pom2::Core core(config);
    if (iie && !core.loadCharacterRom(roms + "/apple2e_char.rom")) {
        std::fprintf(stderr, "char ROM: %s\n", core.lastError().c_str());
        return 1;
    }
    if (!core.loadRom(roms + (iie ? "/apple2e.rom" : "/apple2p.rom")) ||
        !core.attachDiskII(roms + "/disk2.rom", roms + "/diskii_p6.rom") ||
        !core.insertDisk(0, copy) || !core.bootDisk()) {
        std::fprintf(stderr, "boot failed: %s\n", core.lastError().c_str());
        return 1;
    }

    for (const std::string& step : script) {
        const size_t colon = step.find(':');
        const std::string op = step.substr(0, colon);
        const std::string arg = colon == std::string::npos ? "" : step.substr(colon + 1);
        if (op == "wait") {
            // In chunks: N * 17030 overflows Core::run's int past ~126 000 frames.
            for (long n = std::atol(arg.c_str()); n > 0; n -= 100000)
                core.run(static_cast<int>(n < 100000 ? n : 100000) * kCyclesPerFrame);
        } else if (op == "until") {
            const size_t split = arg.find(':');
            if (split == std::string::npos) return 2;
            const unsigned target = std::strtoul(arg.substr(0, split).c_str(), nullptr, 16);
            const std::uint64_t limit = core.cpuState().cycles +
                std::strtoull(arg.substr(split + 1).c_str(), nullptr, 10) * kCyclesPerFrame;
            while (core.cpuState().programCounter != target && core.cpuState().cycles < limit)
                core.run(1);
            const auto state = core.cpuState();
            std::printf("until %04X cycles=%llu PC=%04X\n", target,
                        static_cast<unsigned long long>(state.cycles), state.programCounter);
            if (state.programCounter != target) return 3;
        } else if (op == "press") {
            for (unsigned char c : unescape(arg)) core.queueKey(c);
        } else if (op == "key") {
            for (unsigned char c : unescape(arg)) {
                core.queueKey(c);
                core.run(3 * kCyclesPerFrame);          // let the guest take it
            }
        } else if (op == "shot") {
            if (!writePng(arg, core.renderFrame())) {
                std::fprintf(stderr, "cannot write %s\n", arg.c_str());
                return 1;
            }
            std::printf("shot %s\n", arg.c_str());
        } else if (op == "peek") {
            const size_t c2 = arg.find(':');
            unsigned addr = std::strtoul(arg.substr(0, c2).c_str(), nullptr, 16);
            unsigned len = c2 == std::string::npos ? 1 : std::strtoul(arg.substr(c2 + 1).c_str(), nullptr, 0);
            for (unsigned k = 0; k < len; ++k) {
                if (k % 16 == 0) std::printf("%s%04X:", k ? "\n" : "", addr + k);
                std::printf(" %02X", core.read(static_cast<std::uint16_t>(addr + k)));
            }
            std::printf("\n");
        } else if (op == "joy") {
            const size_t c2 = arg.find(',');
            core.setJoystickAxes(std::strtof(arg.substr(0, c2).c_str(), nullptr),
                                 std::strtof(arg.substr(c2 + 1).c_str(), nullptr));
        } else if (op == "btn") {
            const size_t c2 = arg.find(',');
            core.setPaddleButton(std::atoi(arg.substr(0, c2).c_str()),
                                 std::atoi(arg.substr(c2 + 1).c_str()) != 0);
        } else if (op == "reset") {
            core.softReset();
        } else if (op == "pc") {
            std::printf("PC=%04X\n", core.cpuState().programCounter);
        } else {
            std::fprintf(stderr, "unknown step: %s\n", step.c_str());
            return 2;
        }
    }
    return 0;
}
