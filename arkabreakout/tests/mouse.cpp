// Real slot firmware on a 48K NMOS Apple II+, DOS 3.3. GPL-3.0.
#include "M6502.h"
#include "Memory.h"
#include "MouseCard.h"
#include "MouseCardAppleWin.h"
#include "DiskIICard.h"
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
static void check(bool b,const char* s) {if(!b)throw std::runtime_error(s);}
int main(int argc,char** argv) {
 try {
    check(argc==5||argc==6,"usage: mouse ROM_DIR DISK LABELS applewin|mame [reset]");
    std::map<std::string,unsigned> labels;std::ifstream f(argv[3]);std::string m,a,n;
    while(f>>m>>a>>n)labels[n]=std::stoul(a,nullptr,16);
    auto at=[&](const char* s){return uint16_t(labels.at(std::string(".")+s));};
    Memory mem;M6502 cpu(&mem);mem.clearRam();mem.resetSoftSwitches();mem.setIIEMode(false);mem.setCpu(&cpu);
    std::string roms=argv[1];check(mem.loadAppleIIRom((roms+"/apple2p.rom").c_str(),false)>0,"II+ ROM");
    MouseCard* real=nullptr;MouseCardAppleWin* aw=nullptr;
    if(std::string(argv[4])=="mame") {
      auto card=std::make_unique<MouseCard>(4);real=card.get();
      check(real->loadRoms(roms+"/mouse_341-0270-c.bin",roms+"/mouse_341-0269.bin"),"mouse ROMs");
      mem.slotBus().plug(4,std::move(card));
    } else {
      auto card=std::make_unique<MouseCardAppleWin>(4);aw=card.get();
      check(aw->loadRom(roms+"/mouse_341-0270-c.bin"),"mouse ROM");mem.slotBus().plug(4,std::move(card));
    }
    auto disk=std::make_unique<DiskIICard>(6);disk->setCpu(&cpu);
    check(disk->loadBootRom(roms+"/disk2.rom"),"Disk II ROM");check(disk->insertDisk(argv[2]),"disk");mem.slotBus().plug(6,std::move(disk));
    cpu.setCpuMode(M6502::CpuMode::NMOS);cpu.hardReset();mem.slotBus().reset();
    auto read=[&](const char* s){return mem.memRead(at(s));};
    auto write=[&](const char* s,uint8_t v){mem.memWrite(at(s),v);};
    bool keepHgr=false;
    auto step=[&](){
      cpu.step();
      if(keepHgr){auto d=mem.getDisplayState();check(!d.textMode&&d.hiRes&&!d.mixedMode,"full-screen HGR on every instruction during play/menu/loading");}
    };
    auto until=[&](const char* s,long budget=10000000){long c=0;do{step();c+=cpu.getCurrentInstructionCycles();}while(cpu.getProgramCounter()!=at(s)&&c<budget);check(cpu.getProgramCounter()==at(s),s);};
    auto cycles=[&](long count){long c=0;while(c<count){step();c+=cpu.getCurrentInstructionCycles();}};
    until("menu_loop",50000000);check(read("_mouse_slot")==4,"card detected on II+");check(read("mode")==2,"mouse selected");
    keepHgr=true;
    float x=0,y=0;bool button=false;
    auto host=[&](){if(real)real->setHostMouse(x,y,button);else aw->setHostMouse(x,y,button);};
    host();cycles(100000);button=true;host();until("loop");check(read("state")==1&&read("ball_live"),"click starts launched game");
    button=false;host();mem.queueKey('P');cycles(200000);write("ball_live",0);write("enemy_hold",1);mem.queueKey('P');until("loop");
    for(int i=0;i<20;i++){x+=10;host();until("loop");}check(read("pad_x")>180,"mouse X moves right");
    for(int i=0;i<50;i++){x+=20;host();until("loop");}check(read("pad_x")==251-read("pad_width"),"full right stays clamped without wrapping");
    for(int i=0;i<50;i++){x-=30;host();until("loop");}check(read("pad_x")==2,"full left");
    for(int i=0;i<30;i++){y-=10;host();until("loop");}check(read("pad_y")>=100&&read("pad_y")<=128,"mouse Y raises paddle");
    for(int i=0;i<30;i++){y+=20;host();until("loop");}check(read("pad_y")==175,"mouse Y lowers paddle");
    button=true;host();until("loop");check(read("ball_live"),"mouse click launches");
    mem.queueKey('P');cycles(200000);write("effect",5);mem.queueKey('P');until("loop");
    button=false;host();until("loop");until("loop");until("loop");button=true;host();until("loop");until("loop");check(read("shot_live")&&mem.memRead(at("shot_live")+1),"mouse fires two lasers");
    auto start=mem.getCycleCounter();for(int i=0;i<60;i++)until("loop");
    double hz=60.0*1020484.0/(mem.getCycleCounter()-start);check(hz>=26,"mouse cadence");
    // Worst simulation fixture: three balls inside the grid at Expert speed.
    mem.queueKey('P');cycles(200000);
    for(unsigned i=0;i<96;i++)mem.memWrite(at("bricks")+i,i==95 ? 1 : 0);
    write("remaining",1);write("enemy_hold",1);write("effect",4);write("speed",7);
    write("ball_x",100);write("ball_y",100);write("ball_live",1);write("ball_dirx",0);write("ball_diry",1);
    write("ball_speed",104);write("ball_yspeed",208);
    for(int i=0;i<20;i++){y-=20;host();until("loop");}
    for(unsigned i=0;i<2;i++) {
      const uint8_t b[]={uint8_t(120+i*20),100,1,uint8_t(i),1,104,0,208,0};
      for(unsigned j=0;j<9;j++)mem.memWrite(at("extra_balls")+i*9+j,b[j]);
    }
    mem.queueKey('P');until("loop");
    start=mem.getCycleCounter();for(int i=0;i<10;i++){x+=5;host();until("loop");}
    double worst=10.0*1020484.0/(mem.getCycleCounter()-start);
    std::cout<<"Expert multiball measured: "<<worst<<" updates/s\n";
    check(worst>=30,"Expert multiball + real mouse cadence");
    std::cout<<"PASS Expert multiball + "<<argv[4]<<" firmware: "<<worst<<" updates/s\n";
    button=false;host();mem.queueKey(27);until("menu_input");
    // Cross a pack boundary while browsing, then reload the live pack on resume.
    write("furthest",10);
    for(int i=0;i<10;i++){mem.queueKey('D');cycles(100000);until("menu_input");}
    check(read("menu_sector")==10,"preview another disk pack in HGR");
    auto menuY=[&](int target){
      for(int i=0;i<400&&read("_mouse_y")!=target;i++){
        y+=read("_mouse_y")<target ? 1 : -1;host();until("menu_input");
      }
      check(read("_mouse_y")==target,"mouse menu row");
    };
    menuY(144);auto mute=read("sound_muted");button=true;host();
    for(int i=0;i<5;i++)until("menu_input");
    check(read("sound_muted")==(mute^1),"click toggles sound once while held");
    button=false;host();until("menu_input");until("menu_input");
    menuY(110);button=true;host();until("loop");
    check(read("state")==1,"mouse resumes after preview menu");
    button=false;host();until("loop");
    // Victory, DOS BSAVE, records, help and returning to the title also
    // stay in HGR. The flag is checked after every CPU instruction.
    write("paused",0);write("level",59);write("remaining",0);write("ball_live",0);
    write("effect",0);write("enemy_hold",1);
    for(int i=0;i<18;i++)mem.memWrite(at("extra_balls")+i,0);
    for(int i=0;i<6;i++)mem.memWrite(at("score")+i,'0');
    until("menu_loop",100000000);check(read("state")==3,"victory remains in HGR");
    check(read("save_status")==1,"records saved in HGR");
    for(char key : {'H','?'}){
      mem.queueKey(key);until("wait_key");mem.queueKey(' ');until("menu_loop");
    }
    mem.queueKey(27);until("title_menu_key");
    auto menuSound=read("sound_muted");mem.queueKey('S');cycles(100000);until("title_menu_key");
    check(read("sound_muted")==(menuSound^1),"title options sound toggle");
    mem.queueKey(27);until("menu_loop");check(read("state")==0,"ESC returns from options to title");
    std::cout<<"PASS continuous HGR: menu, pack loads, resume, victory/save, records, help and title\n";
    keepHgr=false; // Explicit DOS exit is allowed to restore TEXT.
    if(argc==6)cpu.softReset();
    else {mem.queueKey(27);cycles(300000);mem.queueKey('Q');}
    cycles(10000000);check(!read("_mouse_slot"),"close mouse on DOS exit");check(mem.memRead(0x3f2)==0xbf&&mem.memRead(0x3f3)==0x9d,"DOS reset restored");
    std::cout<<"PASS II+ "<<argv[4]<<": real mouse firmware, X/Y, click/laser, DOS exit, "<<hz<<" updates/s, "<<(argc==6?"RESET":"Q")<<" cleanup\n";
    return 0;
 } catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}
}
