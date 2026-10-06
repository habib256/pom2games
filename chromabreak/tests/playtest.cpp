// VERHILLE Arnaud — GPL-3.0. Full POM2 integration, real AppleMouse firmware.
#include "M6502.h"
#include "../src/layout.h"
#include "Memory.h"
#include "MouseCard.h"
#include "MouseCardAppleWin.h"
#include "IIcMouse.h"
#include "IWMDevice.h"
#include "DiskIICard.h"
#include "MemoryWatchSink.h"
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <filesystem>
#include <vector>
#include <set>
#include <algorithm>
#include <cstdlib>

static void require(bool ok,const std::string& why) { if(!ok) throw std::runtime_error(why); }
int main(int argc,char** argv) {
 try {
    require(argc>=4 && argc<=6,"usage: playtest ROM_DIR DISK.po game.lbl");
    std::string roms=argv[1];
    std::map<std::string,unsigned> labels;
    std::ifstream f(argv[3]); std::string mark,address,name;
    while(f>>mark>>address>>name) labels[name]=std::stoul(address,nullptr,16);
    auto at=[&](const char* s) { return uint16_t(labels.at(std::string("._")+s)); };
    std::string variant=argc>=5 ? argv[4] : "mame";
    bool pal=variant.find("-pal")!=std::string::npos;
    if(pal)variant.erase(variant.find("-pal"));
    bool iic=variant=="iic16" || variant=="iic32";
    pom2::IWMDevice iwm;
    Memory mem; M6502 cpu(&mem);
    if(iic) {mem.setIWM(&iwm);mem.setIWMAuthoritative(true);}
    mem.clearRam(); mem.resetSoftSwitches(); mem.setIIEMode(true); mem.setCpu(&cpu);
    mem.setVideoStandard(pal ? VideoStandard::PAL : VideoStandard::NTSC);
    auto rom=roms+(variant=="iic16" ? "/apple2c-16K.rom" : variant=="iic32" ? "/apple2c-32Kv0.rom" : "/apple2e.rom");
    require(mem.loadAppleIIRom(rom.c_str(),iic)>0,"main ROM");
    bool hle=variant=="applewin";
    bool alternate=argc==6 && std::string(argv[5])=="space-reset";
    std::string recordTest=argc==6 ? argv[5] : "";
    MouseCard* mouse=nullptr; MouseCardAppleWin* applewin=nullptr; IIcMouse* native=nullptr;
    if (iic) {
        auto card=std::make_unique<IIcMouse>(4);
        native=card.get();mem.slotBus().plug(4,std::move(card));
    } else if (hle) {
        auto card=std::make_unique<MouseCardAppleWin>(4);
        require(card->loadRom(roms+"/mouse_341-0270-c.bin"),"mouse ROM");
        applewin=card.get(); mem.slotBus().plug(4,std::move(card));
    } else {
        auto card=std::make_unique<MouseCard>(4);
        require(card->loadRoms(roms+"/mouse_341-0270-c.bin",roms+"/mouse_341-0269.bin"),"mouse ROMs");
        mouse=card.get(); mem.slotBus().plug(4,std::move(card));
    }
    auto disk=std::make_unique<DiskIICard>(6);
    auto *drive=disk.get();
    disk->setCpu(&cpu);
    disk->setIwmHost(iic);
    if(iic)disk->setIWM(&iwm);
    require(disk->loadBootRom(roms+"/disk2.rom"),"Disk II ROM");
    // The host wrapper supplies a private image; production image never written.
    require(disk->insertDisk(argv[2]),"insert disk");
    mem.slotBus().plug(6,std::move(disk));
    cpu.setCpuMode(M6502::CpuMode::CMOS); cpu.hardReset(); mem.slotBus().reset();
    auto read=[&](const char* s) { return mem.memRead(at(s)); };
    auto write=[&](const char* s,uint8_t v) { mem.memWrite(at(s),v); };
    auto run=[&](long cycles) { long c=0; while(c<cycles) {cpu.step();c+=cpu.getCurrentInstructionCycles();} };
    const bool profile=std::getenv("CHROMA_PROFILE")!=nullptr;
    bool profileActive=false;
    std::map<unsigned,std::string> profileNames;
    std::map<std::string,uint64_t> profileTime;
    struct Call {std::string name;unsigned returnPC;uint64_t start;};
    std::vector<Call> profileStack;
    if(profile)for(const char* name : {"game_tick","advance_balls","render","hud","input","effects_tick","mouse_poll","damage","fast_draw","fast_restore","fast_fill","fast_paddle","fast_text","sound_tick","timing_present","ball_step","collision","collision_cached","ball_swap","lasers_step"})
        profileNames[at(name)]=name;
    auto until=[&](uint16_t pc,long budget) {
        long c=0; do {
            if(profileActive) {
                auto current=cpu.getProgramCounter();
                while(!profileStack.empty() && profileStack.back().returnPC==current) {
                    auto call=profileStack.back();profileStack.pop_back();profileTime[call.name]+=mem.getCycleCounter()-call.start;
                }
                auto name=profileNames.find(current);
                if(name!=profileNames.end()) {
                    auto sp=cpu.getStackPointer();
                    unsigned target=1+mem.memRead(0x100+uint8_t(sp+1))+256*mem.memRead(0x100+uint8_t(sp+2));
                    auto label=name->second;
                    if(label=="fast_draw" || label=="fast_restore")label+="["+std::to_string(cpu.getAccumulator())+"]";
                    profileStack.push_back({label,target,mem.getCycleCounter()});
                }
            }
            cpu.step();c+=cpu.getCurrentInstructionCycles();}
        while(cpu.getProgramCounter()!=pc && c<budget);
        require(cpu.getProgramCounter()==pc,"timeout at PC="+std::to_string(cpu.getProgramCounter()));
    };
    const auto tick=at("game_tick");
    until(tick,50000000);
    require(read("timing_mode")==unsigned(iic?2:1),"VBL IRQ clock on IIe and IIc");
    require(read("mouse_slot")==4,"AppleMouse not detected in slot 4");
    require(read("mouse_x")==70 && read("mouse_y")==96,"initial mouse position/clamps");
    std::cout<<"PASS ProDOS boot + AppleMouse firmware slot 4\n";
    if(recordTest.rfind("records-",0)==0) {
        drive->driveImage(0).setWriteBackEnabled(recordTest!="records-error");
        auto word=[&](uint16_t p) {return unsigned(mem.memRead(p))+256*mem.memRead(p+1);};
        auto press=[&](char key) {mem.queueKey(key);until(tick,80000000);until(tick,80000000);};
        if(recordTest=="records-collisions") {
            cpu.setStatusRegister(cpu.getStatusRegister()|4);
            auto routine=at("collision");
            mem.memWrite(0x300,0x20);mem.memWrite(0x301,routine&255);mem.memWrite(0x302,routine>>8);
            auto cell=[&](int x,int y)->unsigned {
                x-=5;y-=CB_TILE_TOP;
                if(x<0 || y<0 || x/11>=12 || y/12>=8 || x%11>=9 || y%12>=8)return 255;
                auto index=x/11+12*(y/12);return mem.memRead(at("bricks")+index)?index:255;
            };
            for(int cached=0;cached<2;++cached) {
            for(int pattern=0;pattern<4;++pattern) {
                for(int i=0;i<96;++i)mem.memWrite(at("bricks")+i,pattern==0?0:pattern==1?255:((i*13+pattern*23)%7==0?0:1+i%3));
                for(int order=0;order<2;++order)for(int x=4;x<=133;++x) {
                    if(cached) {
                        auto reset=at("collision_cache_reset");
                        mem.memWrite(0x301,reset&255);mem.memWrite(0x302,reset>>8);
                        cpu.setProgramCounter(0x300);until(0x303,10000);
                    }
                    auto selected=at(cached?"collision_cached":"collision");
                    mem.memWrite(0x301,selected&255);mem.memWrite(0x302,selected>>8);
                    for(int offset=0;offset<CB_LOST_Y-CB_FIELD_TOP;++offset) {
                    int y=order?CB_LOST_Y-1-offset:CB_FIELD_TOP+offset;
                    write("ball_x",x);write("ball_y",y);
                    unsigned expected=255;
                    const int offsets[][2]={{1,0},{0,1},{2,1},{0,4},{2,4},{1,5}};
                    for(auto& offset:offsets)if((expected=cell(x+offset[0],y+offset[1]))!=255)break;
                    cpu.setProgramCounter(0x300);until(0x303,10000);
                    require(cpu.getAccumulator()==expected,"optimized collision differs from six-point round silhouette");
                    }
                }
            }
            }
            std::cout<<"PASS cached/uncached positions in both vertical directions against six-point silhouette\n";return 0;
        }
        if(recordTest=="records-smalltext") {
            // Compare every glyph and alignment against its bitmap, while
            // preserving unrelated pixels in both banks and both draw pages.
            const auto routine=at("dhgr_small_char");
            mem.memWrite(0x300,0x20);mem.memWrite(0x301,routine&255);mem.memWrite(0x302,routine>>8);
            auto address=[](int page,int row,int byte) {return 0x2000+page*8192+(row&7)*1024+((row>>3)&7)*128+(row>>6)*40+byte/2;};
            auto bank=[&](int byte) {mem.memWrite(byte&1?0xC002:0xC003,0);};
            std::vector<int> chars;
            for(int ch=32;ch<96;++ch)chars.push_back(ch);
            for(int ch : {97,122,0,31,96,127,255})chars.push_back(ch);
            for(int page=0;page<2;++page)for(int phase=0;phase<7;++phase)for(int ch:chars) {
                const int left=9+phase;
                mem.memWrite(at("dhgr_base"),0x20+page*0x20);
                for(int row=119;row<=125;++row)for(int byte=0;byte<80;++byte) {
                    bank(byte);mem.memWrite(byte&1?0xC004:0xC005,0);
                    mem.memWrite(address(page,row,byte),(row*19+byte*17+page*11)&127);
                    mem.memWrite(0xC004,0);
                }
                mem.memWrite(0xC002,0);
                write("dhgr_small_x",left);write("dhgr_small_y",120);
                const unsigned irqFlag=(phase&1)?4:0;
                cpu.setStatusRegister((cpu.getStatusRegister()&~4)|irqFlag);
                cpu.setAccumulator(ch);cpu.setProgramCounter(0x300);until(0x303,10000);
                require((cpu.getStatusRegister()&4)==irqFlag,"small text changes IRQ state");
                require(!(mem.memRead(0xC013)&128) && !(mem.memRead(0xC014)&128),"small text leaves auxiliary bank selected");
                int glyph=ch;
                if(glyph>='a' && glyph<='z')glyph-=32;
                if(glyph<32 || glyph>=96)glyph='?';
                for(int row=119;row<=125;++row)for(int byte=0;byte<80;++byte) {
                    unsigned expected=(row*19+byte*17+page*11)&127;
                    if(row>=120 && row<125) {
                        mem.memWrite(0xC002,0);
                        unsigned bitmap=mem.memRead(0x800+(glyph-32)*6+row-120);
                        for(int bit=0;bit<7;++bit) {
                            int pixel=byte*7+bit-left*4;
                            if(pixel>=0 && pixel<20) {
                                expected&=~(1u<<bit);
                                if(pixel<16 && (bitmap&(1u<<(pixel/4))))expected|=1u<<bit;
                            }
                        }
                    }
                    bank(byte);
                    require(mem.memRead(address(page,row,byte))==expected,"small glyph mismatch page="+std::to_string(page)+" phase="+std::to_string(phase)+" char="+std::to_string(ch)+" row="+std::to_string(row)+" byte="+std::to_string(byte)+" expected="+std::to_string(expected)+" actual="+std::to_string(mem.memRead(address(page,row,byte))));
                }
                mem.memWrite(0xC002,0);
            }
            // The last complete cell fits; out-of-range origins do no writes.
            cpu.setStatusRegister(cpu.getStatusRegister()|4);
            for(int x : {135,136})for(int y : {187,188}) {
                write("dhgr_small_x",x);write("dhgr_small_y",y);
                cpu.setAccumulator('A');cpu.setProgramCounter(0x300);until(0x303,10000);
            }
            std::cout<<"PASS compact library font: ASCII, fallback/lowercase, seven phases, both banks/pages, preserved edges and IRQs\n";
            return 0;
        }
        if(recordTest=="records-numbers") {
            cpu.setStatusRegister(cpu.getStatusRegister()|4);
            auto routine=at("fast_number");
            mem.memWrite(0x300,0x20);mem.memWrite(0x301,routine&255);mem.memWrite(0x302,routine>>8);
            uint64_t longest=0;
            for(unsigned value=0;value<65536;++value) {
                const unsigned decimalFlag=(value&1)?8:0;
                cpu.setStatusRegister((cpu.getStatusRegister()&~8)|decimalFlag);
                cpu.setAccumulator(value&255);cpu.setXRegister(value>>8);cpu.setProgramCounter(0x300);
                auto start=mem.getCycleCounter();until(0x303,10000);
                longest=std::max(longest,mem.getCycleCounter()-start);
                auto pointer=unsigned(cpu.getAccumulator())+256*cpu.getXRegister();
                auto digits=std::to_string(value);digits=std::string(5-digits.size(),'0')+digits;
                for(int n=0;n<5;++n)require(mem.memRead(pointer+n)==digits[n],"five-digit unsigned conversion");
                require(mem.memRead(pointer+5)==0,"numeric terminator");
                require((cpu.getStatusRegister()&8)==decimalFlag,"numeric conversion preserves caller decimal mode");
            }
            require(longest<3000,"numeric conversion must fit inside a vertical blank");
            std::cout<<"PASS all 65536 numeric values, bounded to "<<longest<<" cycles\n";return 0;
        }
        if(recordTest=="records-victory") {
            press(13);
            for(int level=0;level<12;++level) {
            for(int i=0;i<96;++i)mem.memWrite(at("bricks")+i,i==0?1:0);
            write("remaining",1);write("level",level);write("ball_x",8);write("ball_y",CB_TILE_TOP+8);
            write("ball_live",1);write("round_live",1);write("dx",1);write("dy",255);
            write("vx",0);write("vy",255);write("fraction_y",255);
            until(tick,80000000);
            require(cpu.getProgramCounter()==tick && read("state")==unsigned(level==11?4:1),"last brick opens next level/victory record entry");
            }
            std::cout<<"PASS victory record entry\n";return 0;
        }
        const unsigned expected[]={3200,1800,1500,1240,900};
        if(recordTest=="records-empty") {
            for(int i=0;i<5;++i)require(word(at("records")+i*6)==0,"invalid/missing record file must use defaults");
            press('H');require(read("state")==5,"empty record table remains usable");
            std::cout<<"PASS missing/corrupt records: safe empty table\n";return 0;
        }
        if(recordTest=="records-load") {
            for(int i=0;i<5;++i)require(word(at("records")+i*6)==expected[i],"persistent records after cold boot");
            require(mem.memRead(at("records")+2)=='A' && mem.memRead(at("records")+3)=='B' && mem.memRead(at("records")+4)=='C',"persistent initials");
            const unsigned modes[]={2,1,0,0,1};
            for(int i=0;i<5;++i)require(mem.memRead(at("records")+i*6+5)==modes[i],"persistent difficulty for each record");
            press('H');require(read("state")==5,"H opens records from title");
            press(27);require(read("state")==0,"ESC returns to title from records");
            std::cout<<"PASS persistent five-record table, initials and menu\n";return 0;
        }
        const unsigned scores[]={1240,900,3200,1500,1800,100};
        for(int n=0;n<6;++n) {
            write("difficulty",n%3);press(13);
            write("lives",1);write("ball_live",1);write("ball_x",4);write("ball_y",CB_LOST_Y-1);
            write("dx",1);write("dy",1);write("vx",0);write("vy",255);write("fraction_y",255);
            mem.memWrite(at("score"),scores[n]&255);mem.memWrite(at("score")+1,scores[n]>>8);
            until(tick,80000000);
            if(n==5) {require(read("state")==2,"low score must not enter full records");break;}
            require(read("state")==4,"qualifying score requests three initials");
            press('A');press('B');press('X');press(8);press('C');
            require(read("record_cursor")==3,"initial entry and backspace");
            press(13);
            if(recordTest=="records-error") {
                require(read("state")==5 && read("save_status")==2,"write-protected disk reports unsaved record");
                require(word(at("records"))==1240,"unsaved record remains available in RAM");
                std::cout<<"PASS write-protected disk: error shown, record retained in RAM\n";return 0;
            }
            require(read("state")==5 && read("save_status")==1,"ProDOS record save and table: state="+std::to_string(read("state"))+" status="+std::to_string(read("save_status"))+" MLI="+std::to_string(read("records_error")));
            require(read("timing_mode")==unsigned(iic?2:1),"VBL restored after record I/O");
        }
        for(int i=0;i<5;++i)require(word(at("records")+i*6)==expected[i],"sorted top five records");
        require(drive->flushPendingWrites(),"flush actual ProDOS disk writes");
        std::cout<<"PASS three initials, ranked top five and actual ProDOS writes\n";return 0;
    }
    uint8_t hostX=0,hostY=0; bool pressed=false;
    auto host=[&]() { if(native) native->setHostMouse(hostX,hostY,pressed); else if(mouse) mouse->setHostMouse(hostX,hostY,pressed); else applewin->setHostMouse(hostX,hostY,pressed); };
    host(); run(80000);
    auto startSound=mem.getSpeakerToggleCount();
    if (alternate) mem.queueKey(32); else { pressed=true; host(); }
    run(100000); until(tick,20000000);
    require(read("state")==1 && read("mode")==1,"click/SPACE starts mouse game");
    require(read("ball_live"),"one menu action starts play and fires the ball");
    require(mem.getSpeakerToggleCount()>=startSound+8,"start tone reaches speaker");
    // Simulate an attached ball while the initial button stays held: no repeat.
    write("ball_live",0);write("round_live",0);until(tick,3000000);until(tick,3000000);
    require(!read("ball_live"),"held initial click must not repeatedly fire");
    pressed=false; host(); until(tick,3000000); until(tick,3000000);
    require(read("speed")==3,"faster initial ball pace");
    for(int i=0;i<12;++i) {++hostX; host();run(20000);}
    until(tick,3000000);
    require(read("mouse_x")>70 && read("pad_x")>60,"mouse X moves paddle");
    run(300000);until(tick,3000000);
    auto pad=read("pad_x");
    for(int i=0;i<12;++i) {++hostY; host();run(20000);}
    until(tick,3000000);
    require(read("mouse_y")>96 && read("pad_x")==pad,"mouse Y does not move paddle");
    auto launchSound=mem.getSpeakerToggleCount();
    pressed=true; host();run(100000);until(tick,3000000);
    require(read("ball_live"),"click launches ball");
    require(mem.getSpeakerToggleCount()>=launchSound+8,"launch tone reaches speaker");
    for(int n=0;n<5;++n)until(tick,3000000);
    require(mem.getSpeakerToggleCount()>=launchSound+40,"launch tone spans multiple frames");
    pressed=false;host();
    std::cout<<"PASS mouse X/Y, click start/launch and button edges\n";
    auto stamp=mem.getCycleCounter();
    uint64_t shortest=~uint64_t(0),longest=0;
    unsigned moves=0;
    for(int i=0;i<60;++i) {
        profileActive=profile;profileTime.clear();profileStack.clear();
        if(i&1)--hostX;else ++hostX;host();
        auto beforePad=read("pad_x");
        auto t=mem.getCycleCounter();until(tick,3000000);
        if(read("pad_x")!=beforePad)++moves;
        auto dt=mem.getCycleCounter()-t;
        if(profile && dt>38000) {
            std::cerr<<"Frame "<<i<<" "<<dt<<" cycles ball="<<unsigned(read("ball_x"))<<","<<unsigned(read("ball_y"))<<"\n";
            for(auto& entry:profileTime)std::cerr<<entry.first<<"="<<entry.second<<" ";
            std::cerr<<"\n";
        }
        shortest=std::min(shortest,dt);longest=std::max(longest,dt);
        require(mem.getDisplayState().page2==(read("dhgr_display")==2),"hardware/software display page agree");
    }
    std::cout<<"Frame interval: "<<shortest<<".."<<longest<<" cycles\n";
    profileActive=false;
    require(moves>=20,"cadence test must move the mouse paddle");
    require(longest-shortest<uint64_t(pal ? 8000 : 5000),"irregular frame intervals during active play");
    require(read("timing_mode")==unsigned(iic?2:1),"VBL pacing remains active");
    auto clock=pal ? 1015600.0 : 1023000.0;
    auto fps=60.0*clock/(mem.getCycleCounter()-stamp);
    require(fps>=(pal?24.0:29.0),"below expected VBL cadence in active mouse play");
    std::cout<<"PASS active mouse-play cadence: "<<fps<<" fps ("<<(pal?"PAL":"NTSC")<<")\n";
    // Pause, move through the standard keyboard input, and resume.
    mem.queueKey('P');until(tick,3000000);until(tick,3000000);
    require(read("paused"),"pause"); auto bx=read("ball_x"),by=read("ball_y");
    auto silence=mem.getSpeakerToggleCount();
    run(500000);until(tick,3000000);
    require(mem.getSpeakerToggleCount()==silence,"pause must silence speaker");
    require(read("ball_x")==bx && read("ball_y")==by,"pause freezes ball");
    mem.queueKey('P');until(tick,3000000);until(tick,3000000);
    require(!read("paused"),"resume");
    mem.queueKey('K');until(tick,3000000);until(tick,3000000);
    require(!read("mode"),"keyboard fallback");
    mem.queueKey('A');until(tick,3000000);until(tick,3000000);
    require(read("pad_x")<pad,"keyboard left");
    mem.queueKey('S');until(tick,3000000);until(tick,3000000);
    std::cout<<"PASS pause/resume + keyboard fallback\n";
    // Restore colored brick backgrounds at all seven DHGR bit phases,
    // checking both main/aux banks and both hidden pages.
    mem.queueKey('P');until(tick,3000000);until(tick,3000000);
    write("ball_live",1);write("ball_x",80);write("ball_y",140);
    until(tick,3000000);until(tick,3000000);
    auto boardVideo=[&]() {
        std::vector<uint8_t> data;
        for(int bank=0;bank<2;++bank) {
            mem.memWrite(bank?0xC003:0xC002,0);
            for(int page=0;page<2;++page) for(int y=CB_TILE_TOP;y<CB_GRID_END;++y) for(int x=0;x<40;++x)
                data.push_back(mem.memRead(0x2000+page*8192+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+x));
        }
        mem.memWrite(0xC002,0); return data;
    };
    auto before=boardVideo();
    for(int phase=0;phase<7;++phase) {
        write("ball_x",6+phase);write("ball_y",CB_TILE_TOP+2);
        until(tick,3000000);until(tick,3000000);
        write("ball_x",80);write("ball_y",140);
        until(tick,3000000);until(tick,3000000);
        require(before==boardVideo(),"DHGR sprite failed to restore both banks/pages");
    }
    std::cout<<"PASS save-under: seven phases, both banks and both pages\n";
    auto colorAt=[&](int page,int x,int y) {
        unsigned nibble=0;
        for(int b=0;b<4;++b) {
            int bit=x*4+b,byte=bit/7;
            mem.memWrite((byte&1)?0xC002:0xC003,0);
            auto value=mem.memRead(0x2000+page*8192+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+byte/2);
            nibble|=((value>>(bit%7))&1)<<b;
        }
        mem.memWrite(0xC002,0);return ((nibble<<1)|(nibble>>3))&15;
    };
    for(int width : {22,30}) {
        std::vector<unsigned> reference;
        for(int phase=0;phase<7;++phase) {
            write("pad_x",6+phase);write("pad_width",width);
            until(tick,3000000);until(tick,3000000);
            for(int page=0;page<2;++page) {
                std::vector<unsigned> pixels;
                for(int x=0;x<width;++x) {
                    pixels.push_back(colorAt(page,6+phase+x,CB_PAD_Y+2));
                    const bool end=x==0 || x==width-1;
                    require(colorAt(page,6+phase+x,CB_PAD_Y)==(end?0:15),"rounded white paddle highlight");
                    require(colorAt(page,6+phase+x,CB_PAD_Y+4)==(end?0:2),"rounded blue paddle shadow");
                    require(colorAt(page,6+phase+x,CB_PAD_Y+2)==(end?5:14),"silver ends and cyan paddle body");
                }
                if(reference.empty())reference=pixels;
                require(pixels==reference,"paddle colors changed with DHGR phase/page");
                require(std::set<unsigned>(pixels.begin(),pixels.end())==std::set<unsigned>{5,14},"restrained cyan and silver paddle");
                require(colorAt(page,5+phase,CB_PAD_Y+2)==0 && colorAt(page,6+phase+width,CB_PAD_Y+2)==0,"paddle spilled outside bounds");
            }
        }
    }
    // White round ball, with transparent tips, in every DHGR alignment.
    for(int phase=0;phase<7;++phase) {
        write("ball_x",80+phase);write("ball_y",140);
        until(tick,3000000);until(tick,3000000);
        for(int page=0;page<2;++page) for(int y=0;y<6;++y)
            for(int x=0;x<3;++x)
                require(colorAt(page,80+phase+x,140+y)==
                    ((y==0 || y==5) && x!=1 ? 0 : 15),"round white ball silhouette");
    }
    write("pad_width",20);write("pad_x",60);
    // Compact score 0: three strokes plus two black spacing columns.
    for(int page=0;page<2;++page) {
        require(colorAt(page,5,CB_HUD_Y)==15 && colorAt(page,7,CB_HUD_Y)==15,"compact score digit strokes");
        require(colorAt(page,8,CB_HUD_Y)==0 && colorAt(page,9,CB_HUD_Y)==0,"compact score glyph spacing");
        require(colorAt(page,41,CB_HUD_Y)==15 && colorAt(page,43,CB_HUD_Y)==0,"compact life digit and spacing");
    }
    std::cout<<"PASS compact DHGR HUD, including spacing and rightmost strokes\n";
    std::cout<<"PASS solid paddles + round white ball: seven phases, both pages\n";

    // Deterministic boundary cases through the actual shipped physics.
    auto clear=[&]() {for(int i=0;i<96;++i) mem.memWrite(at("bricks")+i,0);};
    auto setup=[&]() {
        clear(); write("paused",0);write("ball_live",1);write("round_live",1);write("remaining",2);
        write("ball_x",8);write("ball_y",CB_TILE_TOP+8);write("dx",1);write("dy",255);
        write("vx",0);write("vy",255);write("fraction_x",0);write("fraction_y",255);
        write("speed",2);
    };
    setup();mem.memWrite(at("bricks"),3); until(tick,3000000);
    require(mem.memRead(at("bricks"))==2 && read("dy")==1,"resistant brick rebound");
    setup();mem.memWrite(at("bricks"),255);auto sc=read("score");until(tick,3000000);
    require(mem.memRead(at("bricks"))==255 && read("score")==sc,"steel rebound/no score");
    setup();write("ball_x",4);write("ball_y",140);write("dx",255);
    write("vx",255);write("vy",0);write("fraction_x",255);until(tick,3000000);
    require(read("dx")==1 && read("ball_x")>=4,"left wall");
    for(int zone=0;zone<8;++zone) {
        setup();write("pad_x",60);write("pad_width",20);write("ball_x",60+zone*20/8);
        write("ball_y",CB_PAD_Y-6);write("dy",1);until(tick,3000000);
        require(read("dy")==255,"paddle rebound");
        require(read("dx")==uint8_t(zone<4?255:1),"paddle angle direction");
    }
    setup();write("pad_x",60);write("ball_x",58);write("ball_y",CB_PAD_Y-6);write("dy",1);
    until(tick,3000000);
    require(read("dy")==255 && read("dx")==255,"round ball grazing left paddle edge");
    std::cout<<"PASS brick resistance, steel, wall and eight paddle angles\n";
    write("normal_speed",3);write("ramp_hits",0);write("effect",0);
    for(int n=1;n<=32;++n) {
        setup();mem.memWrite(at("bricks"),1);until(tick,3000000);
        require(read("normal_speed")==unsigned(std::min(6,3+n/8)),"eight-brick pace ramp/cap");
    }
    setup();write("speed",6);mem.memWrite(at("bricks"),3);until(tick,3000000);
    require(mem.memRead(at("bricks"))==2 && read("dy")==1,"no tunneling at maximum speed");
    std::cout<<"PASS acceleration to six substeps and maximum-speed brick collision\n";
    // A destruction combo grows every three bricks and stops at x8.
    write("combo",0);write("multiplier",1);
    mem.memWrite(at("score"),0);mem.memWrite(at("score")+1,0);
    unsigned comboScore=0;
    for(int n=1;n<=24;++n) {
        setup();mem.memWrite(at("bricks"),1);until(tick,3000000);
        auto factor=unsigned(std::min(8,1+n/3));comboScore+=10*factor;
        auto actual=read("score")+256*mem.memRead(at("score")+1);
        require(read("multiplier")==factor && actual==comboScore,"combo multiplier and awarded score");
    }
    setup();write("pad_x",60);write("ball_x",65);write("ball_y",CB_PAD_Y-6);write("dy",1);
    until(tick,3000000);
    require(read("multiplier")==1 && read("combo")==0,"paddle resets combo");
    setup();write("lives",3);write("combo",12);write("multiplier",5);
    write("ball_x",8);write("ball_y",CB_LOST_Y-1);write("dy",1);
    until(tick,3000000);
    require(read("lives")==2 && read("multiplier")==1 && read("combo")==0,"lost life resets combo");
    std::cout<<"PASS combo scoring, x8 cap, paddle/life reset\n";
    setup(); write("lives",3);
    mem.memWrite(at("next_life_score"),0xE8);mem.memWrite(at("next_life_score")+1,3);
    mem.memWrite(at("score"),0xDE);mem.memWrite(at("score")+1,3); // 990
    mem.memWrite(at("bricks"),3);until(tick,3000000);
    require(read("lives")==4,"extra life at 1000 points");
    for(int kind=1;kind<=3;++kind) {
        setup();write("ball_live",0);write("round_live",0);write("capsule",kind);
        write("cap_x",65);write("cap_y",CB_PAD_Y-5);until(tick,3000000);
        require(read("effect")==kind && !read("capsule"),"capsule pickup");
        require(read("pad_width")==uint8_t(kind==1?30:22),"capsule width");
        if(kind==2)require(read("speed")==2,"slow capsule");
    }
    std::cout<<"PASS bonus life and three capsule effects\n";
    auto extra=[&](int ball,int field,uint8_t value) {mem.memWrite(at("extra_ball")+ball*9+field,value);};
    auto extraRead=[&](int ball,int field) {return mem.memRead(at("extra_ball")+ball*9+field);};
    auto resetRound=[&]() {
        setup();write("lives",3);write("effect",0);write("capsule",0);
        extra(0,2,0);extra(1,2,0);write("ball_x",4);write("ball_y",CB_LOST_Y-1);write("dy",1);
        until(tick,3000000);require(!read("round_live"),"round reset fixture");
    };
    auto pickup=[&](int kind) {
        resetRound();write("lives",3);write("pad_x",60);write("capsule",kind);
        write("cap_x",65);write("cap_y",CB_PAD_Y-5);until(tick,3000000);
        require(read("effect")==kind && !read("capsule"),"new capsule pickup");
    };
    pickup(4);
    require(read("round_live") && read("ball_live") && extraRead(0,2) && extraRead(1,2),"multiball launches three balls");
    require(extraRead(0,3)==255 && extraRead(1,3)==1,"multiball fans to both sides");
    write("ball_live",0);until(tick,3000000);
    require(read("lives")==3 && read("ball_live") && !extraRead(0,2) && extraRead(1,2),"primary loss promotes a surviving ball");
    write("vx",0);write("vy",0);
    extra(1,0,4);extra(1,1,CB_LOST_Y-1);extra(1,4,1);extra(1,5,0);extra(1,6,255);extra(1,8,255);
    until(tick,3000000);
    require(read("lives")==3 && !extraRead(1,2) && read("ball_live"),"secondary loss preserves the life");
    write("ball_x",4);write("ball_y",CB_LOST_Y-1);write("dy",1);write("vy",255);write("fraction_y",255);
    until(tick,3000000);
    require(read("lives")==2 && !read("round_live") && !read("ball_live"),"last ball costs one life");
    // Two balls can damage the same resistant brick in a frame, without
    // duplicate dirty work or a lost/doubled hit.
    resetRound();setup();mem.memWrite(at("bricks"),3);
    const uint8_t second[]={8,CB_TILE_TOP+8,1,1,255,0,255,0,255};
    for(int k=0;k<9;++k)extra(0,k,second[k]);
    until(tick,3000000);
    require(mem.memRead(at("bricks"))==1,"two independent resistant-brick hits");
    std::cout<<"PASS three-ball fan, promotion, last-ball life and simultaneous hits\n";
    pickup(5);mem.queueKey(' ');until(tick,3000000);until(tick,3000000);
    require(mem.memRead(at("shot_live")) && mem.memRead(at("shot_live")+1),"SPACE fires two laser bolts");
    require(mem.memRead(at("shot_x"))==read("pad_x")+2 && mem.memRead(at("shot_x")+1)==read("pad_x")+read("pad_width")-3,"lasers leave both paddle ends");
    write("ball_live",0);write("round_live",0);clear();write("remaining",2);
    mem.memWrite(at("bricks"),2);mem.memWrite(at("shot_live"),1);mem.memWrite(at("shot_live")+1,0);
    mem.memWrite(at("shot_x"),8);mem.memWrite(at("shot_y"),CB_TILE_TOP+10);
    until(tick,3000000);
    require(mem.memRead(at("bricks"))==1 && !mem.memRead(at("shot_live")),"laser hits resistant brick without tunneling");
    mem.memWrite(at("bricks"),255);mem.memWrite(at("shot_live"),1);mem.memWrite(at("shot_y"),CB_TILE_TOP+10);
    auto steelScore=mem.memRead(at("score"))+256*mem.memRead(at("score")+1);
    until(tick,3000000);
    require(mem.memRead(at("bricks"))==255 && !mem.memRead(at("shot_live")),"steel absorbs laser");
    require(steelScore==mem.memRead(at("score"))+256*mem.memRead(at("score")+1),"laser steel scores nothing");
    write("mode",1);write("laser_cooldown",0);pressed=true;host();run(80000);until(tick,3000000);
    require(mem.memRead(at("shot_live")) || mem.memRead(at("shot_live")+1),"mouse button fires laser");
    for(int n=0;n<9;++n)until(tick,3000000);
    mem.memWrite(at("shot_live"),0);mem.memWrite(at("shot_live")+1,0);until(tick,3000000);
    require(mem.memRead(at("shot_live")) && mem.memRead(at("shot_live")+1),"held mouse button repeats laser");
    pressed=false;host();write("mode",0);
    pickup(6);setup();mem.memWrite(at("bricks"),3);until(tick,3000000);
    require(!mem.memRead(at("bricks")) && read("dy")==255 && read("ball_y")<CB_TILE_TOP+8,"piercing ball destroys resistance and keeps direction");
    setup();mem.memWrite(at("bricks"),255);until(tick,3000000);
    require(mem.memRead(at("bricks"))==255 && read("dy")==1,"piercing ball reflects from steel");
    std::cout<<"PASS double laser, keyboard/mouse/repeat, resistance/steel and piercing\n";
    // Flash is visible on both hidden pages and then restores the original
    // highlight. Shards are colored and leave the destroyed tile black.
    resetRound();setup();write("ball_x",18);mem.memWrite(at("bricks")+1,3);
    until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page)require(colorAt(page,20,CB_TILE_TOP)==15,"resistant brick flashes white on both pages");
    for(int n=0;n<6;++n)until(tick,3000000);
    for(int page=0;page<2;++page)require(colorAt(page,20,CB_TILE_TOP)==13,"flash restores orange-brick highlight");
    setup();write("ball_x",18);mem.memWrite(at("bricks")+1,1);until(tick,3000000);
    unsigned activeShards=0;
    for(int n=0;n<4;++n)if(mem.memRead(at("particle_life")+n)) {
        ++activeShards;auto x=mem.memRead(at("particle_x")+n),y=mem.memRead(at("particle_y")+n);
        auto page=read("dhgr_display")-1;
        require(colorAt(page,x,y)==mem.memRead(at("particle_color")+n),"colored impact shard actually drawn");
    }
    require(activeShards==2,"destruction emits two bounded shards");
    for(int n=0;n<9;++n)until(tick,3000000);
    for(int n=0;n<4;++n)require(!mem.memRead(at("particle_life")+n),"shard expires");
    for(int page=0;page<2;++page)for(int y=CB_TILE_TOP;y<CB_TILE_TOP+8;++y)for(int x=16;x<25;++x)
        require(colorAt(page,x,y)==0,"expired shards/flash must leave no trail");
    std::cout<<"PASS brief two-page flash, colored shards and clean expiration\n";
    // Exercise the actual multiball + laser combination at Expert pace,
    // with a falling capsule and four real impact shards (all sprite IDs).
    pickup(4);write("capsule",5);write("cap_x",read("pad_x")+2);write("cap_y",CB_PAD_Y-5);
    until(tick,3000000);require(read("effect")==5 && extraRead(0,2) && extraRead(1,2),"laser preserves multiball");
    clear();write("remaining",10);write("speed",0);write("normal_speed",7);
    write("ball_x",20);write("ball_y",75);write("vx",0);write("vy",255);write("dy",1);write("fraction_y",255);
    for(int b=0;b<2;++b) {
        extra(b,0,65+b*45);extra(b,1,80+b*5);extra(b,2,1);extra(b,4,1);
        extra(b,5,0);extra(b,6,255);extra(b,8,255);
    }
    mem.memWrite(at("bricks"),1);mem.memWrite(at("bricks")+1,1);
    for(int b=0;b<2;++b) {mem.memWrite(at("shot_live")+b,1);mem.memWrite(at("shot_x")+b,8+b*10);mem.memWrite(at("shot_y")+b,CB_TILE_TOP+10);}
    until(tick,3000000);
    for(int b=0;b<4;++b)require(mem.memRead(at("particle_life")+b)>0,"two laser impacts emit four shards");
    write("speed",7);write("laser_cooldown",0);write("capsule",6);write("cap_x",120);write("cap_y",140);
    mem.queueKey(' ');until(tick,3000000);
    write("mode",0);write("direction",1);
    shortest=~uint64_t(0);longest=0;stamp=mem.getCycleCounter();
    for(int n=0;n<3;++n) {
        profileActive=profile;profileTime.clear();profileStack.clear();
        auto time=mem.getCycleCounter();until(tick,3000000);
        auto dt=mem.getCycleCounter()-time;shortest=std::min(shortest,dt);longest=std::max(longest,dt);
        if(profile) {for(auto& entry:profileTime)std::cerr<<entry.first<<"="<<entry.second<<" ";std::cerr<<"\n";}
        require(read("ball_live") && extraRead(0,2) && extraRead(1,2) && read("capsule"),"maximum actor fixture remains active");
        for(int b=0;b<2;++b)require(mem.memRead(at("shot_live")+b),"two lasers in maximum actor fixture");
        for(int b=0;b<4;++b)require(mem.memRead(at("particle_life")+b),"four shards in maximum actor fixture");
    }
    fps=3.0*clock/(mem.getCycleCounter()-stamp);
    profileActive=false;
    std::cout<<"Maximum actors: "<<shortest<<".."<<longest<<" cycles, "<<fps<<" fps\n";
    const bool heavyCadenceOK=fps>=(pal?24.0:29.0) && longest-shortest<uint64_t(pal?8000:5000);
    write("direction",0);
    resetRound();
    // Level transitions from either displayed page must never write to it.
    struct VideoWrites : pom2::MemoryWatchSink {
        Memory& mem;unsigned visibleWrites=0,badFlips=0,flips=0;bool page2;
        uint64_t period;
        VideoWrites(Memory& m,bool pal):mem(m),page2(m.getDisplayState().page2),period(65*(pal?312:262)){}
        void noteAccess(uint16_t addr,uint8_t,bool write) override {
            if(!write && (addr==0xC054 || addr==0xC055)) {
                auto current=mem.getDisplayState().page2;
                if(current!=page2) {
                    ++flips;page2=current;
                    if(mem.getCycleCounter()%period<65*192)++badFlips;
                }
            }
            if(write && addr>=0x2000 && addr<0x6000 &&
               (addr>=0x4000)==mem.getDisplayState().page2) ++visibleWrites;
        }
    } videoWrites(mem,pal);
    mem.setWatchSink(&videoWrites);
    mem.setReadWatch(0xC054,true);mem.setReadWatch(0xC055,true);
    for(unsigned a=0x2000;a<0x6000;++a)mem.setWriteWatch(a,true);
    for(int page : {1,2}) {
        write("paused",1);
        while(read("dhgr_display")!=page)until(tick,3000000);
        setup();write("remaining",1);mem.memWrite(at("bricks"),1);
        auto previousLevel=read("level");auto previousFlips=videoWrites.flips;
        until(tick,20000000);
        require(videoWrites.flips==previousFlips+1,"level must have exactly one hardware page flip");
        require(videoWrites.badFlips==0,"page flip outside vertical blank");
        require(read("level")==previousLevel+1,"new level loaded");
        require(read("dhgr_display")==3-page,"new level presented exactly once");
        require(videoWrites.visibleWrites==0,"level rebuilt in the visible page");
        for(int bank=0;bank<2;++bank) {
            mem.memWrite(bank?0xC003:0xC002,0);
            for(unsigned a=0x2000;a<0x4000;++a)
                require(mem.memRead(a)==mem.memRead(a+0x2000),"new level pages differ after clone");
        }
        mem.memWrite(0xC002,0);
        until(tick,3000000);until(tick,3000000);
        require(videoWrites.visibleWrites==0,"cloned save-under causes visible writes");
    }
    mem.clearWriteWatches();mem.clearReadWatches();mem.setWatchSink(nullptr);
    std::cout<<"PASS level transitions: one presentation, no visible writes, identical main/aux pages\n";
    // Clean exit must disable mouse and leave a valid empty /RAM.
    if (alternate) cpu.softReset(); else mem.queueKey(27);
    until(at("prodos_quit"),20000000);
    require(!read("mouse_slot"),"mouse disabled on exit");
    require(!read("timing_mode"),"VBL handler deallocated on exit/reset");
    require((mem.memRead(0xC01A)&0x80)!=0,"text restored on exit");
    // Check /RAM before QUIT starts the dispatcher. $0300 is ProDOS's RAM
    // transfer trampoline: use a distinct caller/landmark at $0800.
    mem.memWrite(0xBF5C,mem.memRead(0xBF5C)&0x3F);
    write("prodos_command",0x80);
    mem.memWrite(at("prodos_params"),0);mem.memWrite(at("prodos_params")+1,6);
    uint8_t params[]={3,0xB0,0,0x20,2,0};
    for(unsigned i=0;i<6;++i)mem.memWrite(0x600+i,params[i]);
    uint8_t stub[]={0x20,uint8_t(at("prodos_call")),uint8_t(at("prodos_call")>>8),
                    0x8D,0xFF,2,0x4C,6,8};
    for(unsigned i=0;i<9;++i)mem.memWrite(0x800+i,stub[i]);
    cpu.setProgramCounter(0x800);until(0x806,3000000);
    require(!mem.memRead(0x2FF),"MLI READ_BLOCK after video release");
    require((mem.memRead(0x2004)&0xF0)==0xF0 && !mem.memRead(0x2025) && !mem.memRead(0x2026),"/RAM rebuilt empty");
    cpu.setProgramCounter(at("prodos_quit"));run(10000000);
    require(cpu.getProgramCounter()<0x6000 || cpu.getProgramCounter()>=0xA000,"ProDOS dispatcher");
    std::cout<<"PASS "<<(alternate?"RESET":"ESC")<<": mouse disabled, text restored, ProDOS + /RAM\n";
    require(heavyCadenceOK,"maximum actors below expected VBL cadence or irregular intervals");
    return 0;
 } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
