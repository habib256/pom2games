// VERHILLE Arnaud — GPL-3.0. Real AppleMouse firmware integration on POM2.
#include "M6502.h"
#include "Memory.h"
#include "MouseCard.h"
#include "MouseCardAppleWin.h"
#include "DiskIICard.h"
#include "IIcMouse.h"
#include "IWMDevice.h"
#include "SuperSerialCard.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool ok, const std::string& why) {
    if (!ok) throw std::runtime_error(why);
}
int main(int argc, char** argv) {
 try {
    require(argc == 5, "usage: mouse_probe ROM_DIR DISK.dsk BUILD_DIR applewin|applewin5|mame|iic16|iic32");
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
    int diskSlot = variant == "applewin5" ? 5 : 6;
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
    } else if (variant == "applewin" || variant == "applewin5") {
        auto card = std::make_unique<MouseCardAppleWin>(4);
        require(card->loadRom(roms + "/mouse_341-0270-c.bin"), "mouse ROM");
        applewin = card.get(); mem.slotBus().plug(4, std::move(card));
    } else {
        auto card = std::make_unique<MouseCard>(4);
        require(card->loadRoms(roms + "/mouse_341-0270-c.bin", roms + "/mouse_341-0269.bin"), "mouse ROMs");
        mouse = card.get(); mem.slotBus().plug(4, std::move(card));
    }
    auto disk = std::make_unique<DiskIICard>(diskSlot);
    disk->setCpu(&cpu);
    disk->setIwmHost(iic);
    if (iic) disk->setIWM(&iwm);
    require(disk->loadBootRom(roms + "/disk2.rom"), "Disk II ROM");
    require(disk->insertDisk(argv[2]), "disk image");
    mem.slotBus().plug(diskSlot, std::move(disk));
    cpu.setCpuMode(iic ? M6502::CpuMode::CMOS : M6502::CpuMode::NMOS); cpu.hardReset(); mem.slotBus().reset();
    mem.setPaddle(0, 127); mem.setPaddle(1, 127);
    if (!iic) cpu.setProgramCounter(0xC000 + diskSlot * 256);
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
    // GETBUTNS originally preserves X/Y. WORLD's held-slider loop keeps
    // its WSET index in Y across this call; firmware must not replace it.
    auto resumePC = cpu.getProgramCounter();
    auto resumeA = cpu.getAccumulator(), resumeX = cpu.getXRegister();
    auto resumeY = cpu.getYRegister(), resumeP = cpu.getStatusRegister();
    constexpr uint16_t thunk = 0x6200;
    uint8_t savedThunk[] = {mem.memRead(thunk), mem.memRead(thunk + 1), mem.memRead(thunk + 2)};
    auto buttons = at("mouse.mouse_buttons");
    mem.memWrite(thunk, 0x20); // JSR mouse_buttons
    mem.memWrite(thunk + 1, buttons & 255);
    mem.memWrite(thunk + 2, buttons >> 8);
    cpu.setXRegister(0x53); cpu.setYRegister(2);
    cpu.setProgramCounter(thunk);
    long buttonCycles = 0;
    while (cpu.getProgramCounter() != thunk + 3 && buttonCycles < 200000) {
        cpu.step(); buttonCycles += cpu.getCurrentInstructionCycles();
    }
    require(cpu.getProgramCounter() == thunk + 3, "button adapter returns");
    require(cpu.getXRegister() == 0x53 && cpu.getYRegister() == 2,
            "button polling preserves the world slider index and X");
    for (int n = 0; n < 3; ++n) mem.memWrite(thunk + n, savedThunk[n]);
    cpu.setAccumulator(resumeA); cpu.setXRegister(resumeX);
    cpu.setYRegister(resumeY); cpu.setStatusRegister(resumeP);
    cpu.setProgramCounter(resumePC);
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
    // A normal host movement can cross the palette/table boundary in one
    // guest poll. Do not disguise large deltas as slow one-pixel motions.
    hostX += 40 - read("mouse._mouse_x");
    hostY += 70 - read("mouse._mouse_y");
    host(); run(2000000);
    // The MCU card can coalesce quadrature edges during a sudden host
    // jump. Check the actual firmware position, then refine the target.
    require(read("mouse._mouse_x") < 110, "fast mouse movement reaches the table");
    require(read("EDIT.pcs_DRAGX") == 2 * read("mouse._mouse_x") &&
            read("EDIT.pcs_DRAGY") == read("mouse._mouse_y"),
            "dragged ball follows a large mouse delta into the table");
    move(80, 70);
    release(); until("EDIT.pcs_MAIN");
    require(mem.memRead(0x401C) == 3, "mouse drags a ball from the palette into the table");
    // Grab the placed ball away from its right edge, without moving the
    // host pointer. Picking it up must not translate its polygon.
    unsigned ball = 0x401D + mem.memRead(0x401C);
    for (int n = 0; n < mem.memRead(0x401C) - 1; ++n) ball += mem.memRead(0x401D + n);
    int vertices = mem.memRead(ball + 2);
    std::vector<uint8_t> polygon;
    int minX = 255, maxX = 0, minY = 255, maxY = 0;
    for (int n = 0; n < 3 + 2 * vertices; ++n) polygon.push_back(mem.memRead(ball + n));
    for (int n = 0; n < vertices; ++n) {
        int x = polygon[3 + n], y = polygon[3 + vertices + n];
        minX = std::min(minX, x); maxX = std::max(maxX, x);
        minY = std::min(minY, y); maxY = std::max(maxY, y);
    }
    int pickupX = ((minX + maxX) / 2) & ~1, pickupY = (minY + maxY) / 2;
    move(pickupX, pickupY);
    press(); until("EDIT.pcs_DRAGO6");
    require(mem.memRead(at("EDIT.pcs_OBJ")) + 256 * mem.memRead(at("EDIT.pcs_OBJ") + 1) == ball,
            "center click picks the placed ball");
    for (int n = 0; n < int(polygon.size()); ++n)
        require(mem.memRead(ball + n) == polygon[n], "picking up a piece keeps its position");
    move(pickupX + 20, pickupY + 10);
    for (int n = 0; n < vertices; ++n) {
        require(mem.memRead(ball + 3 + n) == polygon[3 + n] + 20 &&
                mem.memRead(ball + 3 + vertices + n) == polygon[3 + vertices + n] + 10,
                "piece movement retains the original grab point");
    }
    move(pickupX, pickupY);
    release(); until("EDIT.pcs_MAIN");
    move(260, 120); press(); release(); until("RUN.pcs_PLAY7");
    // Native input polling must never overwrite the relocated collision tables.
    uint8_t table = mem.memRead(0x687C);
    run(300000); require(mem.memRead(0x687C) == table, "collision pointer survives mouse firmware");
    mem.queueKey(27); until("EDIT.pcs_MAIN");
    move(260, 160); press(); release(); until("WIRE.pcs_MAIN");
    move(260, 58); press(); release(); until("EDIT.pcs_MAIN");
    move(260, 180); press(); release(); until("DISK.pcs_MAIN");
    require(read("DISK.pcs_SLOT") == diskSlot, "file menu defaults to the boot drive's slot");
    auto menuStack = cpu.getStackPointer();
    move(174, 90); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { mem.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); mem.queueKey(' '); until("DISK.pcs_MAIN", 40000000);
    require(cpu.getStackPointer() == menuStack, "successful SAVE restores the menu stack");
    // An error abandons several nested calls. Returning to MAIN must
    // restore the module's stack rather than leak another frame each time.
    for (int attempt = 0; attempt < 3; ++attempt) {
        move(174, 78); press(); release(); until("DISK.pcs_GETN3");
        for (char c : std::string("ABSENT\r")) { mem.queueKey(c); run(100000); }
        until("DISK.pcs_WAIT1"); mem.queueKey(' '); until("DISK.pcs_ERR7", 40000000);
        require(mem.memRead(at("DISK.pcs_FMPL") + 10) == 6, "missing file reports FILE NOT FOUND");
        mem.queueKey(' '); until("DISK.pcs_MAIN");
        require(cpu.getStackPointer() == menuStack, "file errors restore the menu stack: before=" +
                std::to_string(menuStack) + " after=" + std::to_string(cpu.getStackPointer()) +
                " entry=" + std::to_string(read("DISK.pcs_STACKTEMP")));
        require(mem.memRead(0x401C) == 3, "missing file preserves the table");
    }
    // DOS clears $0400-$06FF; the next poll must recover firmware mailboxes.
    move(174, 78); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { mem.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); mem.queueKey(' ');
    until("DISK.pcs_DECOMPRESS", 40000000);
    until("DISK.pcs_MAIN", 40000000);
    require(cpu.getStackPointer() == menuStack, "successful LOAD restores the menu stack");
    require(mem.memRead(0x401C) == 3, "mouse SAVE/LOAD preserves the table");
    move(174, 100); press(); release(); until("EDIT.pcs_MAIN");
    move(140, 96);
    require(mem.memRead(0x83)*7 + mem.memRead(0x84) == 140, "mouse still works after SAVE/LOAD and overlays");
    std::cout << "PASS " << variant << ": button X/Y, mouse X/Y, fast ball drag, PLAY/ESC, wiring, SAVE/LOAD, error recovery, mailbox recovery\n";
    return 0;
 } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
