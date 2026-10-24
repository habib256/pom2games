// VERHILLE Arnaud — GPL-3.0. Real AppleMouse firmware integration on POM2.
// On the POM2 core facade (../dev/tools/a2shot/probe.hpp), built by make.
#include "probe.hpp"
#include <algorithm>
#include <iostream>
#include <map>
#include <string>
#include <vector>

using probe::require;
int main(int argc, char** argv) {
 try {
    require(argc == 5, "usage: mouse_probe ROM_DIR DISK.dsk BUILD_DIR applewin|applewin5|mame|iic16|iic32");
    std::string roms = argv[1], build = argv[3], variant = argv[4];
    std::map<std::string, unsigned> labels;
    for (const char* module : {"EDIT", "RUN", "WIRE", "DISK", "mouse"})
        probe::labels(labels, build + "/" + module + ".lbl", module);
    auto at = [&](const std::string& name) { return uint16_t(labels.at(name)); };
    bool iic = variant == "iic16" || variant == "iic32";
    // applewin5: the AppleWin card with the Disk II in slot 5.
    const int diskSlot = variant == "applewin5" ? 5 : 6;
    pom2::Core core = probe::boot(roms, argv[2], iic ? variant : "iip",
                                  iic ? "" : variant == "applewin5" ? "applewin" : variant, false, diskSlot);
    auto run = [&](long budget) { probe::run(core, budget); };
    auto until = [&](const std::string& name, long budget = 20000000) {
        probe::until(core, at(name), budget, name);
    };
    auto read = [&](const std::string& name) { return core.read(at(name)); };
    // The host pointer moves by relative steps (moveMouse), its button with it.
    bool down = false;
    auto host = [&](int dx = 0, int dy = 0) { core.moveMouse(dx, dy, down); };
    host();
    until("EDIT.pcs_MAIN", 60000000);
    require(read("mouse._mouse_slot") == 4, "mouse detected in slot 4");
    {
        const auto video = core.displayState();  // INITMOUSE selects TEXT and LORES
        require(!video.text && video.hiRes && !video.mixed && !video.page2, "editor in full-screen HGR page 1");
    }
    run(200000);
    // GETBUTNS originally preserves X/Y. WORLD's held-slider loop keeps
    // its WSET index in Y across this call; firmware must not replace it.
    const auto resume = core.cpuState();
    constexpr uint16_t thunk = 0x6200;
    uint8_t savedThunk[] = {core.read(thunk), core.read(thunk + 1), core.read(thunk + 2)};
    auto buttons = at("mouse.mouse_buttons");
    core.write(thunk, 0x20); // JSR mouse_buttons
    core.write(thunk + 1, buttons & 255);
    core.write(thunk + 2, buttons >> 8);
    auto call = resume;
    call.x = 0x53; call.y = 2; call.programCounter = thunk;
    core.setCpuState(call);
    probe::until(core, thunk + 3, 200000, "button adapter returns");
    require(core.cpuState().x == 0x53 && core.cpuState().y == 2,
            "button polling preserves the world slider index and X");
    for (int n = 0; n < 3; ++n) core.write(thunk + n, savedThunk[n]);
    core.setCpuState(resume);
    // Movement is injected through the card, never through guest coordinates.
    auto move = [&](int x, int y) {
        int tx = x / 2;
        for (int n = 0; n < 240; ++n) {
            int dx = tx - read("mouse._mouse_x"), dy = y - read("mouse._mouse_y");
            if (!dx && !dy) { run(80000); return; }
            host(dx > 0 ? 1 : dx < 0 ? -1 : 0, dy > 0 ? 1 : dy < 0 ? -1 : 0);
            run(30000);
        }
        throw std::runtime_error("mouse target not reached: x=" + std::to_string(read("mouse._mouse_x")) + " y=" + std::to_string(read("mouse._mouse_y")) + " P=" + std::to_string(core.cpuState().status));
    };
    auto press = [&]() { down = true; host(); run(200000); };
    auto release = [&]() { down = false; host(); };
    move(246, 7);
    require(core.read(0x83)*7 + core.read(0x84) == 246 && core.read(0x82) == 7, "HGR cursor follows both axes");
    press();
    // A normal host movement can cross the palette/table boundary in one
    // guest poll. Do not disguise large deltas as slow one-pixel motions.
    host(40 - read("mouse._mouse_x"), 70 - read("mouse._mouse_y"));
    run(2000000);
    // The MCU card can coalesce quadrature edges during a sudden host
    // jump. Check the actual firmware position, then refine the target.
    require(read("mouse._mouse_x") < 110, "fast mouse movement reaches the table");
    require(read("EDIT.pcs_DRAGX") == 2 * read("mouse._mouse_x") &&
            read("EDIT.pcs_DRAGY") == read("mouse._mouse_y"),
            "dragged ball follows a large mouse delta into the table");
    move(80, 70);
    release(); until("EDIT.pcs_MAIN");
    require(core.read(0x401C) == 3, "mouse drags a ball from the palette into the table");
    // Grab the placed ball away from its right edge, without moving the
    // host pointer. Picking it up must not translate its polygon.
    unsigned ball = 0x401D + core.read(0x401C);
    for (int n = 0; n < core.read(0x401C) - 1; ++n) ball += core.read(0x401D + n);
    int vertices = core.read(ball + 2);
    std::vector<uint8_t> polygon;
    int minX = 255, maxX = 0, minY = 255, maxY = 0;
    for (int n = 0; n < 3 + 2 * vertices; ++n) polygon.push_back(core.read(ball + n));
    for (int n = 0; n < vertices; ++n) {
        int x = polygon[3 + n], y = polygon[3 + vertices + n];
        minX = std::min(minX, x); maxX = std::max(maxX, x);
        minY = std::min(minY, y); maxY = std::max(maxY, y);
    }
    int pickupX = ((minX + maxX) / 2) & ~1, pickupY = (minY + maxY) / 2;
    move(pickupX, pickupY);
    press(); until("EDIT.pcs_DRAGO6");
    require(core.read(at("EDIT.pcs_OBJ")) + 256 * core.read(at("EDIT.pcs_OBJ") + 1) == ball,
            "center click picks the placed ball");
    for (int n = 0; n < int(polygon.size()); ++n)
        require(core.read(ball + n) == polygon[n], "picking up a piece keeps its position");
    move(pickupX + 20, pickupY + 10);
    for (int n = 0; n < vertices; ++n) {
        require(core.read(ball + 3 + n) == polygon[3 + n] + 20 &&
                core.read(ball + 3 + vertices + n) == polygon[3 + vertices + n] + 10,
                "piece movement retains the original grab point");
    }
    move(pickupX, pickupY);
    release(); until("EDIT.pcs_MAIN");
    move(260, 120); press(); release(); until("RUN.pcs_PLAY7");
    // Native input polling must never overwrite the relocated collision tables.
    uint8_t table = core.read(0x687C);
    run(300000); require(core.read(0x687C) == table, "collision pointer survives mouse firmware");
    core.queueKey(27); until("EDIT.pcs_MAIN");
    move(260, 160); press(); release(); until("WIRE.pcs_MAIN");
    move(260, 58); press(); release(); until("EDIT.pcs_MAIN");
    move(260, 180); press(); release(); until("DISK.pcs_MAIN");
    require(read("DISK.pcs_SLOT") == diskSlot, "file menu defaults to the boot drive's slot");
    auto menuStack = core.cpuState().stackPointer;
    move(174, 90); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { core.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); core.queueKey(' '); until("DISK.pcs_MAIN", 40000000);
    require(core.cpuState().stackPointer == menuStack, "successful SAVE restores the menu stack");
    // An error abandons several nested calls. Returning to MAIN must
    // restore the module's stack rather than leak another frame each time.
    for (int attempt = 0; attempt < 3; ++attempt) {
        move(174, 78); press(); release(); until("DISK.pcs_GETN3");
        for (char c : std::string("ABSENT\r")) { core.queueKey(c); run(100000); }
        until("DISK.pcs_WAIT1"); core.queueKey(' '); until("DISK.pcs_ERR7", 40000000);
        require(core.read(at("DISK.pcs_FMPL") + 10) == 6, "missing file reports FILE NOT FOUND");
        core.queueKey(' '); until("DISK.pcs_MAIN");
        require(core.cpuState().stackPointer == menuStack, "file errors restore the menu stack: before=" +
                std::to_string(menuStack) + " after=" + std::to_string(core.cpuState().stackPointer) +
                " entry=" + std::to_string(read("DISK.pcs_STACKTEMP")));
        require(core.read(0x401C) == 3, "missing file preserves the table");
    }
    // DOS clears $0400-$06FF; the next poll must recover firmware mailboxes.
    move(174, 78); press(); release(); until("DISK.pcs_GETN3");
    for (char c : std::string("MOUSE\r")) { core.queueKey(c); run(100000); }
    until("DISK.pcs_WAIT1"); core.queueKey(' ');
    until("DISK.pcs_DECOMPRESS", 40000000);
    until("DISK.pcs_MAIN", 40000000);
    require(core.cpuState().stackPointer == menuStack, "successful LOAD restores the menu stack");
    require(core.read(0x401C) == 3, "mouse SAVE/LOAD preserves the table");
    move(174, 100); press(); release(); until("EDIT.pcs_MAIN");
    move(140, 96);
    require(core.read(0x83)*7 + core.read(0x84) == 140, "mouse still works after SAVE/LOAD and overlays");
    std::cout << "PASS " << variant << ": button X/Y, mouse X/Y, fast ball drag, PLAY/ESC, wiring, SAVE/LOAD, error recovery, mailbox recovery\n";
    return 0;
 } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
