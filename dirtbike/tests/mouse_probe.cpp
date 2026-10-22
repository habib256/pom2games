// VERHILLE Arnaud — GPL-3.0. DIRTBIKE with real AppleMouse firmware on POM2
// (adapted from pinball/tests/mouse_probe.cpp): the mouse is found, its
// position drives gas / lean, its button brakes, and the disk still loads a
// track with the //c's mouse interrupts on (RWTS_SEI).
#include "M6502.h"
#include "Memory.h"
#include "MouseCard.h"
#include "MouseCardAppleWin.h"
#include "DiskIICard.h"
#include "IIcMouse.h"
#include "IWMDevice.h"
#include "SuperSerialCard.h"
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

static void require(bool ok, const std::string& why) {
    if (!ok) throw std::runtime_error(why);
}
int main(int argc, char** argv) {
 try {
    require(argc == 5, "usage: mouse_probe ROM_DIR DISK.dsk dirtbike.lbl applewin|mame|iic16|iic32");
    std::string roms = argv[1], variant = argv[4];
    std::map<std::string, unsigned> labels;
    {
        std::ifstream f(argv[3]);
        std::string mark, address, name;
        while (f >> mark >> address >> name)
            labels[name.substr(1)] = std::stoul(address, nullptr, 16);
    }
    auto at = [&](const std::string& name) { return uint16_t(labels.at(name)); };
    bool iic = variant == "iic16" || variant == "iic32";
    pom2::IWMDevice iwm;
    Memory mem; M6502 cpu(&mem);
    if (iic) { mem.setIWM(&iwm); mem.setIWMAuthoritative(true); }
    mem.clearRam(); mem.resetSoftSwitches(); mem.setIIEMode(iic); mem.setCpu(&cpu);
    auto rom = roms + (variant == "iic16" ? "/apple2c-16K.rom" : variant == "iic32" ? "/apple2c-32Kv0.rom" : "/apple2p.rom");
    require(mem.loadAppleIIRom(rom.c_str(), iic) > 0, "main ROM");
    MouseCard* mouse = nullptr;
    MouseCardAppleWin* applewin = nullptr;
    IIcMouse* native = nullptr;
    if (iic) {
        for (int port : {1, 2}) mem.slotBus().plug(port, std::make_unique<SuperSerialCard>(port));
        auto card = std::make_unique<IIcMouse>(4);
        native = card.get(); mem.slotBus().plug(4, std::move(card));
    } else if (variant == "applewin") {
        auto card = std::make_unique<MouseCardAppleWin>(4);
        require(card->loadRom(roms + "/mouse_341-0270-c.bin"), "mouse ROM");
        applewin = card.get(); mem.slotBus().plug(4, std::move(card));
    } else {
        auto card = std::make_unique<MouseCard>(4);
        require(card->loadRoms(roms + "/mouse_341-0270-c.bin", roms + "/mouse_341-0269.bin"), "mouse ROMs");
        mouse = card.get(); mem.slotBus().plug(4, std::move(card));
    }
    auto disk = std::make_unique<DiskIICard>(6);
    disk->setCpu(&cpu);
    disk->setIwmHost(iic);
    if (iic) disk->setIWM(&iwm);
    require(disk->loadBootRom(roms + "/disk2.rom"), "Disk II ROM");
    require(disk->insertDisk(argv[2]), "disk image");
    mem.slotBus().plug(6, std::move(disk));
    cpu.setCpuMode(iic ? M6502::CpuMode::CMOS : M6502::CpuMode::NMOS); cpu.hardReset(); mem.slotBus().reset();
    mem.setPaddle(0, 127); mem.setPaddle(1, 127);
    if (!iic) cpu.setProgramCounter(0xC600);
    auto run = [&](long budget) {
        long cycles = 0;
        while (cycles < budget) { cpu.step(); cycles += cpu.getCurrentInstructionCycles(); }
    };
    auto until = [&](const std::string& name, long budget = 60000000) {
        unsigned pc = at(name); long cycles = 0;
        do { cpu.step(); cycles += cpu.getCurrentInstructionCycles(); }
        while (cpu.getProgramCounter() != pc && cycles < budget);
        require(cpu.getProgramCounter() == pc, "timeout " + name + ": PC=" + std::to_string(cpu.getProgramCounter()));
    };
    auto read = [&](const std::string& name) { return mem.memRead(at(name)); };
    auto state = [&]() {
        return " (mouse " + std::to_string(read("_mouse_x")) + "," + std::to_string(read("_mouse_y")) +
               " btn " + std::to_string(read("_mouse_buttons")) + "; gas " + std::to_string(read("in_throttle")) +
               " lean " + std::to_string(read("in_lean")) + " brake " + std::to_string(read("in_brake")) +
               "; state " + std::to_string(read("state")) + " count " + std::to_string(read("count_t")) +
               " crashed " + std::to_string(read("crashed")) + " demo " + std::to_string(read("demo")) +
               " PC " + std::to_string(cpu.getProgramCounter()) + ")";
    };
    uint8_t hostX = 0, hostY = 0; bool down = false;
    auto host = [&]() {
        if (native) native->setHostMouse(hostX, hostY, down);
        else if (mouse) mouse->setHostMouse(hostX, hostY, down);
        else applewin->setHostMouse(hostX, hostY, down);
    };
    host();
    until("attract", 120000000);
    require(read("_mouse_slot") == 4, "mouse detected in slot 4");
    require(read("joy_ok") == 0 && read("inp_dev") == 0, "a new disk: the keyboard alone drives");
    mem.queueKey(' '); until("menu_input");
    mem.queueKey('\r'); until("new_race"); until("main_loop");
    // the mouse chosen in the main menu (3: the next device found), ESC:
    // back to the race, the choice written into DIRTHOF
    mem.queueKey(27); until("mm_key");
    for (int n = 0; read("inp_dev") != 2; ++n) {
        require(n < 3, "menu: 3 never reaches the mouse");
        mem.queueKey('3'); run(2000000); until("mm_key");
    }
    require(read("joy_ok") == 0, "the mouse chosen: the stick not read");
    mem.queueKey(27); until("race_resume"); until("main_loop", 120000000);
    // movement goes through the card, the game reads the firmware's position;
    // the countdown holds the bike meanwhile (no crash: inputs stay live), and
    // the inputs are read at countdown (read_input has finished by then)
    auto hold = [&]() { mem.memWrite(at("count_t"), 250); };
    auto move = [&](int x, int y) {
        for (int n = 0; n < 400; ++n) {
            hold();
            int dx = x - read("_mouse_x"), dy = y - read("_mouse_y");
            if (!dx && !dy) { run(120000); hold(); until("countdown"); return; }
            hostX += dx > 0 ? 1 : dx < 0 ? -1 : 0;
            hostY += dy > 0 ? 1 : dy < 0 ? -1 : 0;
            host(); run(30000);
        }
        throw std::runtime_error("mouse target not reached: x=" + std::to_string(read("_mouse_x")) +
                                 " y=" + std::to_string(read("_mouse_y")));
    };
    move(70, 40);
    require(read("in_throttle") == 8 && read("in_lean") == 0, "mouse up: full gas, no lean" + state());
    move(20, 96);
    require(read("in_throttle") == 0 && read("in_lean") == 0xFC, "mouse left, centre height: lean back" + state());
    move(120, 96);
    require(read("in_lean") == 4, "mouse right: lean forward" + state());
    move(70, 96);
    require(read("in_lean") == 0 && read("in_brake") == 0, "mouse centred: nothing" + state());
    hold(); down = true; host(); run(200000); hold(); until("countdown");
    require(read("in_brake") != 0, "mouse button: brake" + state());
    down = false; host(); run(200000);
    // ESC: the main menu, the title, another race: the disk reads with the
    // mouse running
    mem.queueKey(27); until("main_menu");
    // the main menu with the mouse: its height points at an item (rows
    // 128-159: HALL OF FAME), a click chooses, a click leaves each page
    until("mm_key");
    for (int n = 0; read("_mouse_y") != 130; ++n) {
        require(n < 2000, "menu: mouse y not reached" + state());
        hostY += read("_mouse_y") < 130 ? 1 : -1;
        host(); run(20000);
    }
    run(300000);
    require(read("mm_sel") == 4, "menu: the mouse points at HALL OF FAME (" + std::to_string(read("mm_sel")) + ")");
    // a click until the game reaches `name` (a click while a page draws is
    // not seen: the firmware is polled)
    auto click_to = [&](const std::string& name) {
        unsigned pc = at(name);
        for (int n = 0; n < 6; ++n) {
            down = true; host(); run(300000); down = false; host();
            for (long cycles = 0; cycles < 1500000; cycles += cpu.getCurrentInstructionCycles()) {
                cpu.step();
                if (cpu.getProgramCounter() == pc) return;
            }
        }
        throw std::runtime_error("menu: clicks never reached " + name + state());
    };
    click_to("mm_hof");
    click_to("hof_page");               // the second page
    click_to("main_menu");
    mem.queueKey('1'); until("tick_wait", 120000000);
    mem.queueKey(' '); until("menu_input");
    mem.queueKey('\r'); until("new_race", 120000000);
    // Ctrl-RESET stops the mouse and its set-up is boot code: the disk boots
    // again, DIRTHOF names the mouse, and it drives the next race
    until("main_loop");
    mem.resetSoftSwitchesWarm(); mem.slotBus().reset(); cpu.softReset();
    until("input_init", 200000000);
    until("attract", 120000000);
    require(read("_mouse_slot") == 4 && read("inp_dev") == 2, "after Ctrl-RESET: the mouse again" + state());
    mem.queueKey(' '); until("menu_input");
    mem.queueKey('\r'); until("new_race"); until("main_loop");
    move(70, 96); move(70, 40);
    require(read("in_throttle") == 8, "after Ctrl-RESET: mouse up, full gas" + state());
    std::cout << "mouse (" << variant << "): found in slot 4, gas / lean / brake, chosen and kept, main menu, back to the race, track reloads, Ctrl-RESET: ok\n";
    return 0;
 } catch (const std::exception& e) {
    std::cerr << "mouse (" << argv[4] << "): " << e.what() << "\n";
    return 1;
 }
}
