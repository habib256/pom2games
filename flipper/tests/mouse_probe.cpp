// VERHILLE Arnaud — GPL-3.0. Real AppleMouse firmware integration on POM2.
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
    require(argc == 5, "usage: mouse_probe ROM_DIR DISK.dsk BUILD_DIR applewin|mame|iic16|iic32");
    std::string roms = argv[1], build = argv[3], variant = argv[4];
    std::map<std::string, unsigned> labels;
    for (const char* module : {"EDIT", "RUN", "WIRE", "DISK", "mouse"}) {
        std::ifstream f(build + "/" + module + ".lbl");
        std::string mark, address, name;
        while (f >> mark >> address >> name)
            labels[std::string(module) + name] = std::stoul(address, nullptr, 16);
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
    auto until = [&](const std::string& name, long budget = 20000000) {
        unsigned pc = at(name); long cycles = 0;
        do {
            cpu.step(); cycles += cpu.getCurrentInstructionCycles(); }
        while (cpu.getProgramCounter() != pc && cycles < budget);
        require(cpu.getProgramCounter() == pc, "timeout " + name + ": PC=" + std::to_string(cpu.getProgramCounter()));
    };
    auto read = [&](const std::string& name) { return mem.memRead(at(name)); };
    uint8_t hostX = 0, hostY = 0; bool down = false;
    auto host = [&]() {
        if (native) native->setHostMouse(hostX, hostY, down);
        else if (mouse) mouse->setHostMouse(hostX, hostY, down);
        else applewin->setHostMouse(hostX, hostY, down);
    };
    host();
    until("EDIT.pcs_MAIN", 60000000);
    require(read("mouse._mouse_slot") == 4, "mouse detected in slot 4");
    run(200000);
    // Movement is injected through the card, never through guest coordinates.
    auto move = [&](int x, int y) {
        int tx = x / 2;
        for (int n = 0; n < 240; ++n) {
            int dx = tx - read("mouse._mouse_x"), dy = y - read("mouse._mouse_y");
            if (!dx && !dy) { run(80000); return; }
            hostX += dx > 0 ? 1 : dx < 0 ? -1 : 0;
            hostY += dy > 0 ? 1 : dy < 0 ? -1 : 0;
            host(); run(30000);
        }
        throw std::runtime_error("mouse target not reached: x=" + std::to_string(read("mouse._mouse_x")) + " y=" + std::to_string(read("mouse._mouse_y")) + " P=" + std::to_string(cpu.getStatusRegister()));
    };
    auto press = [&]() { down = true; host(); run(200000); };
    auto release = [&]() { down = false; host(); };
    move(246, 7);
    require(mem.memRead(0x83)*7 + mem.memRead(0x84) == 246 && mem.memRead(0x82) == 7, "HGR cursor follows both axes");
    press();
    move(80, 70);
    release(); until("EDIT.pcs_MAIN");
    require(mem.memRead(0x401C) == 3, "mouse drags a ball from the palette into the table");
    move(260, 120); press(); release(); until("RUN.pcs_PLAY7");
    // Native input polling must never overwrite the relocated collision tables.
    uint8_t table = mem.memRead(0x687C);
    run(300000); require(mem.memRead(0x687C) == table, "collision pointer survives mouse firmware");
    mem.queueKey(27); until("EDIT.pcs_MAIN");
    move(260, 160); press(); release(); until("WIRE.pcs_MAIN");
    move(260, 58); press(); release(); until("EDIT.pcs_MAIN");
    move(260, 180); press(); release(); until("DISK.pcs_MAIN");
    move(174, 90); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { mem.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); mem.queueKey(' '); until("DISK.pcs_MAIN", 40000000);
    // DOS clears $0400-$06FF; the next poll must recover firmware mailboxes.
    move(174, 78); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { mem.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); mem.queueKey(' ');
    until("DISK.pcs_DECOMPRESS", 40000000);
    until("DISK.pcs_MAIN", 40000000);
    require(mem.memRead(0x401C) == 3, "mouse SAVE/LOAD preserves the table");
    move(174, 100); press(); release(); until("EDIT.pcs_MAIN");
    move(140, 96);
    require(mem.memRead(0x83)*7 + mem.memRead(0x84) == 140, "mouse still works after SAVE/LOAD and overlays");
    std::cout << "PASS " << variant << ": mouse X/Y, ball drag, PLAY/ESC, wiring, SAVE/LOAD, mailbox recovery\n";
    return 0;
 } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
