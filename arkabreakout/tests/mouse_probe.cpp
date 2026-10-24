// Real slot firmware on II+ and native //c ROMs, DOS 3.3. GPL-3.0.
// On the POM2 core facade (../dev/tools/a2shot/probe.hpp), built by make.
#include "probe.hpp"
#include <iostream>
#include <map>
#include <string>
static void check(bool b,const char* s) {if(!b)throw std::runtime_error(s);}
int main(int argc,char** argv) {
 try {
    check(argc==5||argc==6,"usage: mouse ROM_DIR DISK LABELS applewin|mame|iic16|iic32 [reset]");
    std::map<std::string,unsigned> labels;probe::labels(labels,argv[3]);
    auto at=[&](const char* s){return uint16_t(labels.at(std::string(".")+s));};
    std::string variant=argv[4];bool iic=variant=="iic16"||variant=="iic32";
    std::string roms=argv[1];
    pom2::Core core=probe::boot(roms,argv[2],iic?variant:"iip",iic?"":variant);
    auto read=[&](const char* s){return core.read(at(s));};
    auto write=[&](const char* s,uint8_t v){core.write(at(s),v);};
    bool keepHgr=false;
    auto step=[&](){
      core.step();
      if(keepHgr){auto d=core.displayState();check(!d.text&&d.hiRes&&!d.mixed,"full-screen HGR on every instruction during play/menu/loading");}
    };
    auto until=[&](const char* s,long budget=10000000){auto end=probe::cycles(core)+budget;do step();while(probe::pc(core)!=at(s)&&probe::cycles(core)<end);check(probe::pc(core)==at(s),s);};
    auto cycles=[&](long count){auto end=probe::cycles(core)+count;while(probe::cycles(core)<end)step();};
    until("menu_loop",50000000);check(read("_mouse_slot")==4,"mouse detected");check(read("mode")==2,"mouse selected");
    if(iic)check(!(core.cpuState().status&4),"native mouse IRQ enabled");
    keepHgr=true;
    float x=0,y=0;bool button=false;
    // The host pointer moves by relative steps (within +-127, as moveMouse
    // asks), from where the card last took it.
    int hostX=0,hostY=0;
    auto host=[&](){
      const int dx=int(x)-hostX,dy=int(y)-hostY;
      // //c: inject IOU edges during the frame, after the atomic firmware
      // poll. Queuing an entire host jump at loop entry would deliver its
      // edges while IRQs are masked for the zero-page workspace transaction.
      if(iic&&(dx||dy))cycles(10000);
      hostX+=dx;hostY+=dy;core.moveMouse(dx,dy,button);
    };
    host();cycles(100000);button=true;host();until("loop");check(read("state")==1&&read("ball_live"),"click starts launched game");
    button=false;host();core.queueKey('P');cycles(200000);write("ball_live",0);write("enemy_hold",1);core.queueKey('P');until("loop");
    for(int i=0;i<20;i++){x+=10;host();until("loop");}check(read("pad_x")>180,"mouse X moves right");
    for(int i=0;i<50;i++){x+=20;host();until("loop");}check(read("pad_x")==251-read("pad_width"),"full right stays clamped without wrapping");
    for(int i=0;i<50;i++){x-=30;host();until("loop");}check(read("pad_x")==2,"full left");
    for(int i=0;i<30;i++){y-=10;host();until("loop");}check(read("pad_y")>=100&&read("pad_y")<=128,"mouse Y raises paddle");
    for(int i=0;i<30;i++){y+=20;host();until("loop");}check(read("pad_y")==175,"mouse Y lowers paddle");
    button=true;host();until("loop");check(read("ball_live"),"mouse click launches");
    core.queueKey('P');cycles(200000);write("effect",5);core.queueKey('P');until("loop");
    button=false;host();until("loop");until("loop");until("loop");button=true;host();until("loop");until("loop");check(read("shot_live")&&core.read(at("shot_live")+1),"mouse fires two lasers");
    auto start=probe::cycles(core);for(int i=0;i<60;i++)until("loop");
    double hz=60.0*1020484.0/(probe::cycles(core)-start);check(hz>=26,"mouse cadence");
    // Worst simulation fixture: three balls inside the grid at Expert speed.
    core.queueKey('P');cycles(200000);
    for(unsigned i=0;i<96;i++)core.write(at("bricks")+i,i==95 ? 1 : 0);
    write("remaining",1);write("enemy_hold",1);write("effect",4);write("speed",7);
    write("ball_x",100);write("ball_y",100);write("ball_live",1);write("ball_dirx",0);write("ball_diry",1);
    write("ball_speed",104);write("ball_yspeed",208);
    for(int i=0;i<20;i++){y-=20;host();until("loop");}
    for(unsigned i=0;i<2;i++) {
      const uint8_t b[]={uint8_t(120+i*20),100,1,uint8_t(i),1,104,0,208,0};
      for(unsigned j=0;j<9;j++)core.write(at("extra_balls")+i*9+j,b[j]);
    }
    core.queueKey('P');until("loop");
    start=probe::cycles(core);for(int i=0;i<10;i++){x+=5;host();until("loop");}
    double worst=10.0*1020484.0/(probe::cycles(core)-start);
    std::cout<<"Expert multiball measured: "<<worst<<" updates/s\n";
    check(worst>=30,"Expert multiball + real mouse cadence");
    std::cout<<"PASS Expert multiball + "<<argv[4]<<" firmware: "<<worst<<" updates/s\n";
    button=false;host();core.queueKey(27);until("menu_input");
    // Cross a pack boundary while browsing, then reload the live pack on resume.
    write("furthest",10);
    for(int i=0;i<10;i++){core.queueKey('D');cycles(100000);until("menu_input");}
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
    for(int i=0;i<18;i++)core.write(at("extra_balls")+i,0);
    for(int i=0;i<6;i++)core.write(at("score")+i,'0');
    until("menu_loop",100000000);check(read("state")==3,"victory remains in HGR");
    check(read("save_status")==1,"records saved in HGR");
    for(char key : {'H','?'}){
      core.queueKey(key);until("wait_key");core.queueKey(' ');until("menu_loop");
    }
    core.queueKey(27);until("title_menu_key");
    auto menuSound=read("sound_muted");core.queueKey('S');cycles(100000);until("title_menu_key");
    check(read("sound_muted")==(menuSound^1),"title options sound toggle");
    core.queueKey(27);until("menu_loop");check(read("state")==0,"ESC returns from options to title");
    std::cout<<"PASS continuous HGR: menu, pack loads, resume, victory/save, records, help and title\n";
    keepHgr=false; // Explicit DOS exit is allowed to restore TEXT.
    if(argc==6)core.softReset();
    else {core.queueKey(27);cycles(300000);core.queueKey('Q');}
    cycles(10000000);check(!read("_mouse_slot"),"close mouse on DOS exit");check(core.read(0x3f2)==0xbf&&core.read(0x3f3)==0x9d,"DOS reset restored");
    std::cout<<"PASS "<<(iic?"//c ":"II+ ")<<argv[4]<<": real mouse firmware, X/Y, click/laser, DOS exit, "<<hz<<" updates/s, "<<(argc==6?"RESET":"Q")<<" cleanup\n";
    return 0;
 } catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}
}
