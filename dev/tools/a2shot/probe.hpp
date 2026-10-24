// probe.hpp — what the games' C++ test probes share on the POM2 core facade
// (sdk/include/pom2/core.hpp, linked as in sdk.mk): the machine they boot,
// ld65 labels, runs counted in CPU cycles, and the store an instruction is
// about to make (the facade has no bus watch). Header only.
//
//   pom2::Core core = probe::boot(roms, disk, "iic32", "", /*pal=*/false);
//
// Machines: "iip" (][+), "iie" (enhanced //e), "iie-unenh" (the original
// //e: NMOS 6502, apple2e_unenh.rom), "iic16" / "iic32" (//c, 16 or
// 32 KB ROM, the built-in mouse on port 4). Mouse (][+ and //e): "" none,
// "mame" (AppleMouse, Apple's firmware on both chips) or "applewin" (the
// same slot EPROM on AppleWin's model of the MCU), in slot 4. The disk boots
// from the Disk II, in slot 6 unless `diskSlot` says otherwise (DOS 3.3 .dsk
// or ProDOS .po, 140 KB; the //c's drive is slot 6).
#ifndef A2SHOT_PROBE_HPP
#define A2SHOT_PROBE_HPP

#include <pom2/core.hpp>

#include <cstdint>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>

namespace probe {

inline void require(bool ok, const std::string& why)
{
    if (!ok) throw std::runtime_error(why);
}

// An ld65 -Ln file ("al 006123 .name"): name -> address. `prefix` is put in
// front of each name (several modules in one map).
inline void labels(std::map<std::string, unsigned>& out, const std::string& file,
                   const std::string& prefix = "")
{
    std::ifstream f(file);
    std::string mark, address, name;
    while (f >> mark >> address >> name) out[prefix + name] = std::stoul(address, nullptr, 16);
}

inline bool isIIc(const std::string& machine) { return machine == "iic16" || machine == "iic32"; }

inline pom2::Core boot(const std::string& roms, const std::string& disk, const std::string& machine,
                       const std::string& mouse = "", bool pal = false, int diskSlot = 6)
{
    pom2::CoreConfig config;
    config.timing = pal ? pom2::VideoTiming::PAL : pom2::VideoTiming::NTSC;
    const bool iic = isIIc(machine);
    config.machine = iic ? pom2::Machine::AppleIIc
                   : machine == "iie" ? pom2::Machine::AppleIIeEnhanced
                   : machine == "iie-unenh" ? pom2::Machine::AppleIIe
                   : pom2::Machine::AppleIIPlus;
    require(iic || machine == "iie" || machine == "iie-unenh" || machine == "iip",
            "unknown machine " + machine);
    pom2::Core core(config);
    const std::string rom = machine == "iic32" ? "/apple2c-32Kv0.rom" : machine == "iic16"
                          ? "/apple2c-16K.rom" : machine == "iie" ? "/apple2e.rom"
                          : machine == "iie-unenh" ? "/apple2e_unenh.rom" : "/apple2p.rom";
    require(core.loadRom(roms + rom, machine == "iic32"), "main ROM: " + core.lastError());
    if (!mouse.empty()) {
        require(!iic, "the //c has its mouse built in");
        require(core.attachMouse(4, mouse == "applewin" ? pom2::MouseModel::AppleMouseAppleWin
                                                        : pom2::MouseModel::AppleMouse, roms),
                "mouse: " + core.lastError());
    }
    require(core.attachDiskII(roms + "/disk2.rom", roms + "/diskii_p6.rom", diskSlot) &&
            core.insertDisk(0, disk) && core.bootDisk(), "boot: " + core.lastError());
    core.setJoystickAxes(0, 0);
    return core;
}

inline std::uint64_t cycles(const pom2::Core& core) { return core.cpuState().cycles; }
inline unsigned pc(const pom2::Core& core) { return core.cpuState().programCounter; }

// Run at least `count` cycles (whole instructions).
inline void run(pom2::Core& core, long count)
{
    const std::uint64_t end = cycles(core) + std::uint64_t(count);
    while (cycles(core) < end) core.run(int(end - cycles(core)));
}

// Step until the PC is `target`, within `budget` cycles. `each` runs after
// every instruction (a check on each one).
template <class Each>
inline void until(pom2::Core& core, unsigned target, long budget, const std::string& what, Each each)
{
    const std::uint64_t end = cycles(core) + std::uint64_t(budget);
    do { core.step(); each(); } while (pc(core) != target && cycles(core) < end);
    require(pc(core) == target, "timeout " + what + ": PC=" + std::to_string(pc(core)));
}
inline void until(pom2::Core& core, unsigned target, long budget, const std::string& what)
{
    until(core, target, budget, what, [] {});
}

// The address the instruction at the PC is about to store to (STA/STX/STY/
// STZ and read-modify-write, 65C02 opcodes included), or -1. Reads its
// operands by bus reads: not for code running in $C000-$C0FF.
inline long storeTarget(pom2::Core& core)
{
    const auto st = core.cpuState();
    const unsigned at = st.programCounter;
    if (at >= 0xC000 && at < 0xC100) return -1;
    const auto rd = [&](unsigned a) { return unsigned(core.read(std::uint16_t(a))); };
    const auto zp16 = [&](unsigned z) { return rd(z & 0xFF) | (rd((z + 1) & 0xFF) << 8); };
    const auto abs = [&] { return rd(at + 1) | (rd(at + 2) << 8); };
    switch (rd(at)) {
    case 0x85: case 0x86: case 0x84: case 0x64: case 0xE6: case 0xC6: case 0x06:
    case 0x46: case 0x26: case 0x66: case 0x04: case 0x14:
        return rd(at + 1);                                              // zp
    case 0x95: case 0x94: case 0x74: case 0xF6: case 0xD6: case 0x16: case 0x56:
    case 0x36: case 0x76:
        return (rd(at + 1) + st.x) & 0xFF;                              // zp,x
    case 0x96: return (rd(at + 1) + st.y) & 0xFF;                       // zp,y
    case 0x8D: case 0x8E: case 0x8C: case 0x9C: case 0xEE: case 0xCE: case 0x0E:
    case 0x4E: case 0x2E: case 0x6E: case 0x0C: case 0x1C:
        return abs();                                                   // abs
    case 0x9D: case 0x9E: case 0xFE: case 0xDE: case 0x1E: case 0x5E: case 0x3E:
    case 0x7E:
        return (abs() + st.x) & 0xFFFF;                                 // abs,x
    case 0x99: return (abs() + st.y) & 0xFFFF;                          // abs,y
    case 0x81: return zp16(rd(at + 1) + st.x);                          // (zp,x)
    case 0x91: return (zp16(rd(at + 1)) + st.y) & 0xFFFF;               // (zp),y
    case 0x92: return zp16(rd(at + 1));                                 // (zp)
    default: return -1;
    }
}

} // namespace probe

#endif // A2SHOT_PROBE_HPP
