// VERHILLE Arnaud — GPL-3.0. WARGALAGA II on POM2's //c (and //e): the clock.
// Built by tests/test_iic.py against a POM2 source tree (optional, like
// chromabreak/tests/playtest.cpp): a2shot has no //c.
//   iic_probe ROM_DIR DISK.po game.lbl VARIANT     (iic16, iic32, iie, -pal)
#include "M6502.h"
#include "Memory.h"
#include "IIcMouse.h"
#include "IWMDevice.h"
#include "SuperSerialCard.h"
#include "DiskIICard.h"
#include "MemoryWatchSink.h"
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

static void require(bool ok, const std::string& why) { if (!ok) throw std::runtime_error(why); }

int main(int argc, char** argv) {
 try {
    require(argc == 5, "usage: iic_probe ROM_DIR DISK.po game.lbl VARIANT");
    std::string roms = argv[1], variant = argv[4];
    std::map<std::string, unsigned> labels;
    std::ifstream f(argv[3]); std::string mark, address, name;
    while (f >> mark >> address >> name) labels[name] = std::stoul(address, nullptr, 16);
    auto at = [&](const char* s) { return uint16_t(labels.at(std::string(".") + s)); };
    bool pal = variant.find("-pal") != std::string::npos;
    if (pal) variant.erase(variant.find("-pal"), 4);
    // -joy: the paddle is read while waiting for the flip ($C070 also
    // acknowledges the //c VBL interrupt: a lost one must not stop the clock).
    bool joy = variant.find("-joy") != std::string::npos;
    if (joy) variant.erase(variant.find("-joy"), 4);
    // -reset: leave by Ctrl-RESET instead of ESC (IRQ live on the //c).
    bool reset = variant.find("-reset") != std::string::npos;
    if (reset) variant.erase(variant.find("-reset"), 6);
    // -irqstop (//c): the flip interrupt stops coming mid-game: the bounded
    // wait must fall back to delays, the game go on and still exit cleanly.
    bool irqstop = variant.find("-irqstop") != std::string::npos;
    if (irqstop) variant.erase(variant.find("-irqstop"), 8);
    bool iic = variant == "iic16" || variant == "iic32";
    pom2::IWMDevice iwm;
    Memory mem; M6502 cpu(&mem);
    if (iic) { mem.setIWM(&iwm); mem.setIWMAuthoritative(true); }
    mem.clearRam(); mem.resetSoftSwitches(); mem.setIIEMode(true); mem.setCpu(&cpu);
    mem.setVideoStandard(pal ? VideoStandard::PAL : VideoStandard::NTSC);
    auto rom = roms + (variant == "iic16" ? "/apple2c-16K.rom" : variant == "iic32" ? "/apple2c-32Kv0.rom" : "/apple2e.rom");
    require(mem.loadAppleIIRom(rom.c_str(), iic) > 0, "main ROM");
    if (iic) {
        // The //c's two ACIAs (see chromabreak/tests/playtest.cpp) and its
        // built-in mouse, whose firmware gives the VBL interrupt.
        for (int port : {1, 2}) mem.slotBus().plug(port, std::make_unique<SuperSerialCard>(port));
        mem.slotBus().plug(4, std::make_unique<IIcMouse>(4));
    }
    auto disk = std::make_unique<DiskIICard>(6);
    disk->setCpu(&cpu);
    disk->setIwmHost(iic);
    if (iic) disk->setIWM(&iwm);
    require(disk->loadBootRom(roms + "/disk2.rom"), "Disk II ROM");
    require(disk->insertDisk(argv[2]), "insert disk");
    mem.slotBus().plug(6, std::move(disk));
    cpu.setCpuMode(M6502::CpuMode::CMOS); cpu.hardReset(); mem.slotBus().reset();
    auto read = [&](const char* s, int k = 0) { return unsigned(mem.memRead(uint16_t(at(s) + k))); };
    auto word = [&](const char* s) { return read(s) | read(s, 1) << 8; };
    auto run = [&](long cycles) { long c = 0; while (c < cycles) { cpu.step(); c += cpu.getCurrentInstructionCycles(); } };
    auto until = [&](uint16_t pc, long budget) {
        long c = 0;
        do { cpu.step(); c += cpu.getCurrentInstructionCycles(); } while (cpu.getProgramCounter() != pc && c < budget);
        require(cpu.getProgramCounter() == pc, "timeout at PC=" + std::to_string(cpu.getProgramCounter()));
    };
    const long refresh = pal ? 20280 : 17030;
    until(at("game_tick"), 80000000);
    require(read("timing_mode") == unsigned(iic ? 2 : 1), "clock: mouse VBL IRQ on //c, $C019 on //e");
    if (joy) mem.memWrite(at("joy_mode"), 1);
    // Early, while the ship lives: a shot's effect on the speaker: toggles (STA $C030) only from the wait
    // loops (the //c one too), none before the shot.
    struct Speaker : pom2::MemoryWatchSink {
        std::vector<uint16_t> pcs; M6502* cpu = nullptr;
        void noteAccess(uint16_t addr, uint8_t, bool write) override {
            if (addr == 0xC030 && write) pcs.push_back(cpu->getProgramCounter());
        }
    } speaker;
    speaker.cpu = &cpu;
    mem.setWatchSink(&speaker); mem.setWriteWatch(0xC030, true);
    run(60 * refresh);
    require(speaker.pcs.empty(), "speaker toggles without an effect");
    until(at("logic_step"), 4000000);
    mem.memWrite(at("fire_req"), 0x80);
    run(30 * refresh);
    mem.setWriteWatch(0xC030, false); mem.setWatchSink(nullptr);
    require(speaker.pcs.size() > 20, "shot effect: " + std::to_string(speaker.pcs.size()) + " toggles");
    for (auto pc : speaker.pcs)
        require((pc >= at("next_edge") && pc < at("ne_edge")) || (pc >= at("wait_irq") && pc < at("wi_count") + 4),
                "a toggle outside the wait loops");
    unsigned f0 = word("frame_count"), s0 = word("step_count"), l0 = word("late_count");
    run(1200 * refresh);
    unsigned f1 = word("frame_count"), s1 = word("step_count"), l1 = word("late_count");
    run(2000 * refresh);
    unsigned f2 = word("frame_count"), s2 = word("step_count"), l2 = word("late_count");
    long steps = long(s2 - s0);
    require(std::labs(steps - 1600) <= 2, "game speed: " + std::to_string(steps) + " steps in 3200 refreshes");
    require(l2 == l1, "late frames with the formation seated: " + std::to_string(l2 - l1));
    require(std::labs(long(f2 - f1) - 1000) <= 2, "30 Hz seated: " + std::to_string(f2 - f1) + " frames in 2000");
    require(read("timing_mode") == unsigned(iic ? 2 : 1), "the clock is still running");
    // The page being drawn is never the one shown (the flip, by the
    // interrupt on the //c, happens between two frames only).
    for (int k = 0; k < 300; ++k) {
        static const char* points[] = {"shots_erase", "aliens_pass", "form_draw", "movers_draw",
                                       "stars_draw", "hud_draw", "render_done"};
        until(at(points[k % 7]), 4000000);
        require((mem.memRead(0xC01C) >> 7) != read("page"), "the page being drawn is on screen");
        until(at("game_tick"), 4000000);
    }
    if (irqstop) {
        // The handler stops showing pages: its STZ ready (between vbl_irq
        // and claimed) becomes NOPs, as if the interrupt had stopped.
        bool patched = false;
        for (unsigned pc = at("vbl_irq"); pc < at("claimed"); ++pc)
            if (mem.memRead(uint16_t(pc)) == 0x9C && mem.memRead(uint16_t(pc + 1)) == (at("ready") & 255)
                && mem.memRead(uint16_t(pc + 2)) == (at("ready") >> 8)) {
                for (int k = 0; k < 3; ++k) mem.memWrite(uint16_t(pc + k), 0xEA);
                patched = true;
            }
        require(patched, "STZ ready found in vbl_irq");
        unsigned fa = word("frame_count"), sa = word("step_count"), va = read("vbl_count");
        run(600 * refresh);
        unsigned fb = word("frame_count"), sb = word("step_count"), vb = read("vbl_count");
        std::cout << "  interrupt stopped: clock mode " << read("timing_mode") << ", vbl_count +" << ((vb - va) & 255)
                  << ", frames +" << (fb - fa) << ", steps +" << (sb - sa) << ", PC " << std::hex
                  << cpu.getProgramCounter() << std::dec << '\n';
        require(read("timing_mode") == 0, "fallback to delays once the interrupt stopped");
        require(fb - fa > 200 && sb - sa > 200, "the game goes on: " + std::to_string(fb - fa) + " frames, "
                + std::to_string(sb - sa) + " steps in 600 refreshes");
    }
    // ESC (or Ctrl-RESET): back to ProDOS, interrupt released, text screen.
    if (reset) {
        mem.resetSoftSwitchesWarm();
        mem.slotBus().reset();
        cpu.softReset();
    } else {
        mem.queueKey(0x1B);
    }
    run(400 * refresh);
    require(cpu.getProgramCounter() < 0x6000 || cpu.getProgramCounter() >= 0xC000, "left the game");
    require(read("timing_mode") == 0, "clock closed at exit");
    require(mem.memRead(at("timing_mode")) == 0, "clock closed at exit");
    require(mem.memRead(0xC01A) & 0x80, "text mode after leaving");
    std::string screen;
    for (int row = 0; row < 24; ++row)
        for (int c = 0; c < 40; ++c)
            screen += char(mem.memRead(uint16_t(0x400 + (row & 7) * 128 + (row >> 3) * 40 + c)) & 0x7F);
    require(screen.find("BITSY") != std::string::npos, "ProDOS launcher on screen");
    std::cout << "PASS " << variant << (pal ? " PAL" : "") << (joy ? " joystick" : "") << (irqstop ? " interrupt stopped" : "") << ": clock mode " << (iic ? 2 : 1)
              << ", " << steps << " steps in 3200 refreshes (" << (l1 - l0)
              << " late frames during the entry waves), seated " << (f2 - f1)
              << " frames in 2000 none late, drawn page never shown, "
              << (reset ? "Ctrl-RESET" : "ESC") << " back to ProDOS, " << speaker.pcs.size()
              << " speaker toggles for a shot\n";
    return 0;
 } catch (const std::exception& e) {
    std::cerr << "FAIL " << (argc == 5 ? argv[4] : "") << ": " << e.what() << '\n';
    return 1;
 }
}
