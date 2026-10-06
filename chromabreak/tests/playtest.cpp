// VERHILLE Arnaud — GPL-3.0. Full POM2 integration, real AppleMouse firmware.
#include "M6502.h"
#include "../src/layout.h"
#include "Memory.h"
#include "MouseCard.h"
#include "MouseCardAppleWin.h"
#include "IIcMouse.h"
#include "IWMDevice.h"
#include "LeChatMauveCard.h"
#include "SuperSerialCard.h"
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
#include <cmath>
#include <complex>

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
    // Original (unenhanced) //e: NMOS 6502 and its own monitor ROM.
    bool nmos=variant=="iie-nmos";
    pom2::IWMDevice iwm;
    Memory mem; M6502 cpu(&mem);
    if(iic) {mem.setIWM(&iwm);mem.setIWMAuthoritative(true);}
    mem.clearRam(); mem.resetSoftSwitches(); mem.setIIEMode(true); mem.setCpu(&cpu);
    mem.setVideoStandard(pal ? VideoStandard::PAL : VideoStandard::NTSC);
    auto rom=roms+(variant=="iic16" ? "/apple2c-16K.rom" : variant=="iic32" ? "/apple2c-32Kv0.rom" : nmos ? "/apple2e_unenh.rom" : "/apple2e.rom");
    require(mem.loadAppleIIRom(rom.c_str(),iic)>0,"main ROM");
    bool hle=variant=="applewin";
    bool alternate=argc==6 && std::string(argv[5])=="space-reset";
    std::string recordTest=argc==6 ? argv[5] : "";
    MouseCard* mouse=nullptr; MouseCardAppleWin* applewin=nullptr; IIcMouse* native=nullptr;
    if (iic) {
        // The //c's two on-board 6551 ACIAs (POM2's //c profile: "ssc" in
        // slots 1 and 2). Its ROM IRQ handler polls their status first; with
        // nothing there it reads the floating bus, and a video byte with
        // bit 7 set looked like a serial interrupt that swallowed the VBL.
        for(int port : {1,2}) mem.slotBus().plug(port,std::make_unique<SuperSerialCard>(port));
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
    // An RGB card that shows mixed DHGR: the game selects it blindly.
    auto chatMauveCard=std::make_unique<LeChatMauveCard>(7,iic ? LeChatMauveCard::Variant::IIcAdapter : LeChatMauveCard::Variant::Feline);
    auto* chatMauve=chatMauveCard.get();mem.slotBus().plug(7,std::move(chatMauveCard));
    cpu.setCpuMode(nmos ? M6502::CpuMode::NMOS : M6502::CpuMode::CMOS); cpu.hardReset(); mem.slotBus().reset();
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
    if(nmos) {
        // The game is 65C02 code: an unenhanced //e must get a clear
        // message on the 40-column text screen, never a crash.
        run(80000000);
        std::string screen;
        for(int row=0;row<24;++row) {
            for(int col=0;col<40;++col)
                screen+=char(mem.memRead(0x400+(row&7)*128+(row>>3)*40+col)&0x7F);
            screen+='\n';
        }
        require(screen.find("ENHANCED")!=std::string::npos,"unenhanced //e shows the requirement message");
        // A key returns to ProDOS (its QUIT selector) rather than hanging.
        mem.queueKey(' ');run(20000000);
        std::string after;
        for(int row=0;row<24;++row)for(int col=0;col<40;++col)
            after+=char(mem.memRead(0x400+(row&7)*128+(row>>3)*40+col)&0x7F);
        require(after.find("65C02")==std::string::npos && cpu.getProgramCounter()>=0xC000,"a key quits to ProDOS");
        std::cout<<"PASS unenhanced //e (6502): requirement message, key back to ProDOS\n";return 0;
    }
    // The title theme plays on arrival: count speaker clicks during boot.
    struct Speaker : pom2::MemoryWatchSink {
        unsigned clicks=0;
        Memory* memory=nullptr;
        std::vector<uint64_t> stamps;   // cycle of each click, for the tune tests
        void noteAccess(uint16_t addr,uint8_t,bool) override {
            if(addr!=0xC030)return;
            ++clicks;if(memory)stamps.push_back(memory->getCycleCounter());
        }
    } speaker;
    speaker.memory=&mem;
    mem.setWatchSink(&speaker);mem.setReadWatch(0xC030,true);
    until(tick,50000000);
    mem.clearReadWatches();mem.setWatchSink(nullptr);
    require(speaker.clicks>2000,"title theme plays at start ("+std::to_string(speaker.clicks)+" clicks)");
    require(read("timing_mode")==unsigned(iic?2:1),"VBL IRQ clock on IIe and IIc");
    require(read("mouse_slot")==4,"AppleMouse not detected in slot 4");
    require(read("mouse_x")==70 && read("mouse_y")==CB_PAD_Y,"initial mouse position/clamps");
    std::cout<<"PASS ProDOS boot + AppleMouse firmware slot 4\n";
    // C stack high-water mark: paint the free part of the 256-byte stack
    // ($BE00-$BEFF, below the cc65 stack pointer), then find the deepest
    // byte touched at the end of a test. Main RAM ends right below it.
    const unsigned stackBottom=0xBE00;
    {unsigned sp=mem.memRead(labels.at(".sp"))+256*mem.memRead(labels.at(".sp")+1);
     for(unsigned a=stackBottom;a<sp;++a)mem.memWrite(a,0x5A);}
    auto stackCheck=[&]() {
        unsigned a=stackBottom;while(a<0xBF00 && mem.memRead(a)==0x5A)++a;
        std::cout<<"C stack: deepest use "<<(0xBF00-a)<<" of "<<(0xBF00-stackBottom)<<" bytes\n";
        require(a>=stackBottom+64,"C stack keeps a 64-byte margin");
    };
    require(chatMauve->dhgrMode()==LeChatMauveCard::DhgrMode::Mixed,"Chat Mauve mixed DHGR selected");
    // Fixtures stay deterministic: no enemy arrives unless a test asks.
    write("enemy_hold",1);
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
        if(recordTest=="records-finetext") {
            // Every glyph at even (AUX-first) and odd (MAIN-first) units, on
            // both pages: seven whole cell rows, untouched neighbours and IRQs.
            const auto routine=at("fine_char");
            mem.memWrite(0x300,0x20);mem.memWrite(0x301,routine&255);mem.memWrite(0x302,routine>>8);
            auto address=[](int page,int row,int unit) {return 0x2000+page*8192+(row&7)*1024+((row>>3)&7)*128+(row>>6)*40+unit/2;};
            auto bank=[&](int unit) {mem.memWrite(unit&1?0xC002:0xC003,0);};
            std::vector<int> chars;
            for(int ch=32;ch<96;++ch)chars.push_back(ch);
            for(int ch : {97,122,0,31,96,127,255})chars.push_back(ch);
            for(int page=0;page<2;++page)for(int unit : {9,10,0,78})for(int ch:chars) {
                mem.memWrite(at("dhgr_base"),0x20+page*0x20);
                for(int row=119;row<=128;++row)for(int u=0;u<80;++u) {
                    bank(u);mem.memWrite(u&1?0xC004:0xC005,0);
                    mem.memWrite(address(page,row,u),(row*19+u*17+page*11)&127);
                    mem.memWrite(0xC004,0);
                }
                mem.memWrite(0xC002,0);
                write("fine_x",unit);write("fine_y",120);
                const unsigned irqFlag=(unit&1)?4:0;
                cpu.setStatusRegister((cpu.getStatusRegister()&~4)|irqFlag);
                cpu.setAccumulator(ch);cpu.setProgramCounter(0x300);until(0x303,10000);
                require((cpu.getStatusRegister()&4)==irqFlag,"fine text changes IRQ state");
                require(!(mem.memRead(0xC013)&128) && !(mem.memRead(0xC014)&128),"fine text leaves auxiliary bank selected");
                require(read("fine_x")==unit+2,"fine text advances one cell");
                int glyph=ch;
                if(glyph>='a' && glyph<='z')glyph-=32;
                if(glyph<32 || glyph>=96)glyph=' ';
                for(int row=119;row<=128;++row)for(int u=0;u<80;++u) {
                    unsigned expected=(row*19+u*17+page*11)&127;
                    if(row>=120 && row<127 && (u==unit || u==unit+1)) {
                        mem.memWrite(0xC002,0);
                        mem.memWrite(0xC003,0);unsigned g=mem.memRead(at("fine_font")+(row-120)*64+glyph-32),wide=0;mem.memWrite(0xC002,0);
                        for(int dot=0;dot<7;++dot)if(g&(1u<<dot))wide|=3u<<(dot*2);
                        expected=u==unit ? wide&127 : wide>>7;
                    }
                    bank(u);
                    require(mem.memRead(address(page,row,u))==expected,"fine glyph mismatch page="+std::to_string(page)+" unit="+std::to_string(unit)+" char="+std::to_string(ch)+" row="+std::to_string(row)+" unit="+std::to_string(u));
                }
                mem.memWrite(0xC002,0);
            }
            std::cout<<"PASS Beautiful Boot text: ASCII, fallback/lowercase, both alignments, both banks/pages, untouched neighbours and IRQs\n";
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
        if(recordTest=="records-music") {
            // Two-voice tunes (duet.inc): every event of the title theme and
            // of the ten sector endings holds its bass under its melody, each a
            // square wave at its share of the speaker's level, and lasts its
            // slices. CHROMA_SPEAKER=file also writes every click's cycle.
            const double slice=255*33+34, turn=slice/255;
            auto aux=[&](unsigned a) {mem.memWrite(0xC003,0);auto v=mem.memRead(a);mem.memWrite(0xC002,0);return unsigned(v);};
            // Mean level over windows of 128 cycles, then the strongest line
            // near a count's frequency (interrupts stretch the turns a little).
            auto line=[&](uint64_t from,int windows,unsigned count,double& shift) {
                const int step=128;
                std::vector<double> mean(windows);
                size_t at=0;while(at<speaker.stamps.size() && speaker.stamps[at]<from)++at;
                int level=at&1;double total=0;
                for(int w=0;w<windows;++w) {
                    uint64_t t=from+uint64_t(w)*step,end=t+step;double high=0;
                    while(at<speaker.stamps.size() && speaker.stamps[at]<end) {high+=level*double(speaker.stamps[at]-t);t=speaker.stamps[at];level^=1;++at;}
                    mean[w]=(high+level*double(end-t))/step;total+=mean[w];
                }
                total/=windows;
                double best=0;
                for(double stretch=0.93;stretch<=1.012;stretch+=0.002) {
                    const double omega=3.14159265358979*step/(count*turn)*stretch;
                    std::complex<double> sum=0;
                    for(int w=0;w<windows;++w)sum+=(mean[w]-total)*std::polar(1.0,-omega*w);
                    const double amplitude=std::abs(sum)*2/windows;
                    if(amplitude>best) {best=amplitude;shift=stretch;}
                }
                return best;
            };
            double worst=1,flattest=1;
            auto tune=[&](unsigned address,uint64_t begin,uint64_t end,const std::string& name) {
                require(end>begin,name+" plays");
                size_t first=0;while(first<speaker.stamps.size() && speaker.stamps[first]<begin)++first;
                require(first<speaker.stamps.size(),name+" reaches the speaker");
                // Where each event starts: interrupts stretch a tune evenly.
                double length=0;
                for(unsigned a=address;aux(a+2);a+=3)length+=aux(a+2)*slice;
                const double origin=double(speaker.stamps[first]),stretch=(double(end)-origin)/length;
                unsigned events=0;double done=0;
                for(;;address+=3) {
                    unsigned melody=aux(address),bass=aux(address+1),slices=aux(address+2);
                    if(!slices)break;
                    ++events;
                    if(melody && slices>=14) {
                        const auto from=uint64_t(origin+(done+1.5*slice)*stretch);
                        int windows=int((slices-3)*slice*stretch/128);
                        double shift=1,shiftBass=1;
                        const double square=2/3.14159265358979;
                        double top=line(from,windows,melody,shift);
                        double low=melody==bass ? top : line(from,windows,bass,shiftBass);
                        const double wantTop=melody==bass ? square : square*20/33;
                        const double wantLow=melody==bass ? square : square*13/33;
                        // A bass three or five times lower puts a harmonic on the melody.
                        const bool harmonic=melody!=bass && bass%melody==0 && (bass/melody)%2==1;
                        const double ratioTop=top/wantTop,ratioLow=low/wantLow;
                        require((harmonic || (ratioTop>0.8 && ratioTop<1.2)) && ratioLow>0.8 && ratioLow<1.2,
                                name+" event "+std::to_string(events)+": melody "+std::to_string(ratioTop)+", bass "+std::to_string(ratioLow)+" of their share");
                        worst=std::min(worst,std::min(harmonic?1.0:ratioTop,ratioLow));
                        flattest=std::min(flattest,std::min(shift,shiftBass));
                    }
                    done+=slices*slice;
                }
                const double played=double(end-begin);
                require(played>length*0.995 && played<length*1.09,name+": "+std::to_string(played/1023000)+" s for "+std::to_string(length/1023000)+" s of events");
                std::cout<<name<<": "<<events<<" events, "<<played/1023000<<" s\n";
            };
            const unsigned tunes=labels.at("._tunes_aux");
            // The title theme played during the boot above.
            require(!speaker.stamps.empty(),"title theme clicks");
            {uint64_t last=speaker.stamps.back(),first=last;
             for(size_t i=speaker.stamps.size();i-->0 && last-speaker.stamps[i]<6000000;)first=speaker.stamps[i];
             tune(tunes,first,last+uint64_t(2*slice),"title theme");}
            // Each sector ending, called as sector_clear calls it.
            const auto jingle=at("play_jingle");
            mem.memWrite(0x300,0x20);mem.memWrite(0x301,jingle&255);mem.memWrite(0x302,jingle>>8);
            mem.setWatchSink(&speaker);mem.setReadWatch(0xC030,true);
            unsigned address=tunes;
            for(int ending=0;ending<10;++ending) {
                while(aux(address+2))address+=3;
                address+=3;
                auto begin=mem.getCycleCounter();
                cpu.setAccumulator(ending);cpu.setProgramCounter(0x300);until(0x303,20000000);
                tune(address,begin,mem.getCycleCounter(),"ending "+std::to_string(ending+1));
            }
            // Muted: as long, and silent.
            {auto clicks=speaker.clicks;auto begin=mem.getCycleCounter();
             write("sound_muted",1);cpu.setAccumulator(0);cpu.setProgramCounter(0x300);until(0x303,20000000);write("sound_muted",0);
             require(speaker.clicks==clicks,"a muted tune is silent");
             require(mem.getCycleCounter()-begin>1000000,"a muted tune keeps its time");}
            mem.clearReadWatches();mem.setWatchSink(nullptr);
            if(const char* path=std::getenv("CHROMA_SPEAKER")) {std::ofstream out(path);for(auto t:speaker.stamps)out<<t<<"\n";}
            std::cout<<"PASS two-voice tunes: weakest voice at "<<worst<<" of its share, slowest "<<flattest<<" of its pitch\n";return 0;
        }
        if(recordTest=="records-nohelp") {
            // '?' without the ENDING file on the disk: the title stays.
            auto pageOne=[&]() {
                std::vector<uint8_t> data;
                for(int bank=0;bank<2;++bank) {
                    mem.memWrite(bank?0xC003:0xC002,0);
                    for(int a=0x2000;a<0x4000;++a)data.push_back(mem.memRead(a));
                }
                mem.memWrite(0xC002,0);return data;
            };
            const auto title=pageOne();
            press('?');
            require(read("state")==0 && pageOne()==title,"help without its file gives the title back");
            require(read("timing_mode")==unsigned(iic?2:1),"VBL clock survives the failed load");
            press(13);
            require(read("state")==1 && read("ball_live"),"a game starts after the failed help");
            std::cout<<"PASS help without the ENDING file: title kept\n";return 0;
        }
        if(recordTest=="records-help") {
            // '?' on the title loads the overlay into page 2 memory and draws
            // the help on page 1: capsules, tiles, points. A key or a click
            // gives the same title back, and the click does not start a game.
            auto pageOne=[&]() {
                std::vector<uint8_t> data;
                for(int bank=0;bank<2;++bank) {
                    mem.memWrite(bank?0xC003:0xC002,0);
                    for(int a=0x2000;a<0x4000;++a)data.push_back(mem.memRead(a));
                }
                mem.memWrite(0xC002,0);return data;
            };
            auto click=[&](bool down) {
                if(native)native->setHostMouse(0,0,down);else if(mouse)mouse->setHostMouse(0,0,down);else applewin->setHostMouse(0,0,down);
            };
            // Colour bytes (bit 7 set, some pixel lit) in the eight bytes of a row.
            auto coloured=[&](const std::vector<uint8_t>& page,int y,int byte) {
                for(int bank=0;bank<2;++bank)for(int b=byte;b<byte+2;++b) {
                    auto v=page[bank*8192+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+b];
                    if(v&0x80 && v&0x7F)return true;
                }
                return false;
            };
            click(false);until(tick,80000000);until(tick,80000000);
            const auto title=pageOne();
            for(int pass=0;pass<2;++pass) {
                mem.queueKey('?');until(at("help"),80000000);
                require(read("state")==0,"help opens on the title");
                until(at("a2_frame_wait"),80000000);
                require(!mem.getDisplayState().page2 && read("dhgr_display")==1,"help is shown on page 1");
                const auto help=pageOne();
                require(help!=title,"help page drawn");
                // Six capsules at colour pixels 10..14, the three tiles and the
                // steel one from pixel 8, two enemies: all colour graphics.
                for(int i=0;i<6;++i)require(coloured(help,20+i*11,2),"capsule "+std::to_string(i+1)+" drawn");
                for(int x : {2,14,26})require(coloured(help,108,x),"tile drawn");
                require(coloured(help,120,2) && coloured(help,149,2) && coloured(help,149,3),"steel tile and enemies drawn");
                // Text is mono (bit 7 clear) and lit on the heading rows.
                bool heading=false;
                for(int b=13;b<27;++b)heading|=(help[(5&7)*1024+b]&0x7F)!=0 && !(help[(5&7)*1024+b]&0x80);
                require(heading,"help heading in mono text");
                run(3000000);
                require(pageOne()==help && read("state")==0,"help waits for a key or a click");
                if(pass) {
                    click(true);until(tick,80000000);until(tick,80000000);
                    require(read("state")==0,"the click that leaves help does not start a game");
                    click(false);until(tick,80000000);until(tick,80000000);
                } else {
                    mem.queueKey(27);until(tick,80000000);until(tick,80000000);
                }
                require(read("state")==0 && pageOne()==title,"help returns to the title unchanged");
                require(read("timing_mode")==unsigned(iic?2:1),"VBL clock survives the overlay load");
            }
            press(13);
            require(read("state")==1 && read("ball_live"),"a game starts after help");
            for(int n=0;n<30;++n)until(tick,3000000);
            require(read("state")==1,"play goes on over the overlay's memory");
            stackCheck();
            std::cout<<"PASS help page: overlay, capsules, tiles, key/click back to the title\n";return 0;
        }
        if(recordTest=="records-victory") {
            press(13);
            // Each sector of a decade has its own ending: the speaker clicks differ.
            std::vector<unsigned> jingleClicks;
            mem.setWatchSink(&speaker);mem.setReadWatch(0xC030,true);
            for(int level=0;level<CB_LEVELS;++level) {
            speaker.clicks=0;
            for(int i=0;i<96;++i)mem.memWrite(at("bricks")+i,i==0?1:0);
            write("remaining",1);write("level",level);write("ball_x",8);write("ball_y",CB_TILE_TOP+8);
            write("ball_live",1);write("round_live",1);write("dx",1);write("dy",255);
            write("vx",0);write("vy",255);write("fraction_y",255);
            if(level==CB_LEVELS-1) {
                until(at("finale"),80000000);
                require(cpu.getProgramCounter()==at("finale"),"sector 60 loads and runs the ENDING overlay");
            }
            until(tick,80000000);
            require(cpu.getProgramCounter()==tick && read("state")==unsigned(level==CB_LEVELS-1?4:1),"last brick opens next level/victory record entry");
            require(read("records_progress")==unsigned(std::min(level+1,CB_LEVELS-1)),"each new sector reached is recorded");
            if(level<10)jingleClicks.push_back(speaker.clicks);
            }
            mem.clearReadWatches();mem.setWatchSink(nullptr);
            for(size_t i=0;i<jingleClicks.size();++i)for(size_t j=0;j<i;++j)
                require(jingleClicks[i]!=jingleClicks[j],"ten distinct sector endings");
            require(jingleClicks.size()==10,"ten sector endings heard");
            std::cout<<"PASS victory record entry\n";return 0;
        }
        const unsigned expected[]={3200,1800,1500,1240,900};
        if(recordTest=="records-v1") {
            // A format 1 file held points: the same records in tens, sector kept.
            const unsigned old[]={3200,1800,1500,1240,900};
            for(int i=0;i<5;++i)require(word(at("records")+i*6)==old[i]/10,"format 1 scores are converted to tens");
            require(mem.memRead(at("records")+2)=='A' && mem.memRead(at("records")+5)==2,"format 1 initials and mode are kept");
            require(read("records_progress")==7,"format 1 keeps the farthest sector");
            std::cout<<"PASS format 1 records: points converted to tens, progress kept\n";return 0;
        }
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
        stackCheck();
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
    require(read("mouse_y")==CB_PAD_Y && read("pad_y")==CB_PAD_Y && read("pad_x")==pad,"mouse pushed down on the floor moves nothing");
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
    // HUD cells: Beautiful Boot glyphs, two 7-dot units each (even = AUX).
    auto unitByte=[&](int page,int unit,int y) {
        mem.memWrite((unit&1)?0xC002:0xC003,0);
        auto value=mem.memRead(0x2000+page*8192+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+unit/2);
        mem.memWrite(0xC002,0);return unsigned(value);
    };
    auto fineCell=[&](int page,int unit,char ch) {
        for(int row=0;row<7;++row) {
            mem.memWrite(0xC003,0);unsigned g=mem.memRead(at("fine_font")+row*64+ch-32),wide=0;mem.memWrite(0xC002,0);
            for(int dot=0;dot<7;++dot)if(g&(1u<<dot))wide|=3u<<(dot*2);
            if(unitByte(page,unit,CB_HUD_Y+row)!=(wide&127) || unitByte(page,unit+1,CB_HUD_Y+row)!=(wide>>7))return false;
        }
        return true;
    };
    for(int page=0;page<2;++page) {
        // Six digits: the fifth is the tens of points, the sixth stays 0.
        require(fineCell(page,CB_HUD_LEFT,'0') && fineCell(page,CB_HUD_LEFT+8,'0'+read("score")%10) && fineCell(page,CB_HUD_LEFT+10,'0'),"HUD score digits");
        require(fineCell(page,CB_HUD_LEFT+2*CB_HUD_LIVES,'0'+read("lives")),"HUD life digit");
        require(fineCell(page,CB_HUD_LEFT+2*(CB_HUD_LIVES-1),' ') && fineCell(page,CB_HUD_LEFT+2*(CB_HUD_LIVES-6),'L'),"HUD life label");
        require(fineCell(page,CB_HUD_LEFT+2*CB_HUD_MULT,'1') && fineCell(page,CB_HUD_LEFT+2*(CB_HUD_MULT-1),'X'),"HUD multiplier");
    }
    std::cout<<"PASS Beautiful Boot HUD: score, lives and multiplier cells on both pages\n";
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
    // The score counts tens of points: a brick is worth its multiplier.
    write("combo",0);write("multiplier",1);
    mem.memWrite(at("score"),0);mem.memWrite(at("score")+1,0);
    for(int k=0;k<3;++k)mem.memWrite(at("score_bcd")+k,0);
    unsigned comboScore=0;
    for(int n=1;n<=24;++n) {
        setup();mem.memWrite(at("bricks"),1);until(tick,3000000);
        auto factor=unsigned(std::min(8,1+n/3));comboScore+=factor;
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
    {
        // The HUD reads the BCD score kept alongside the binary one: five
        // digits of tens, then the units cell that stays 0.
        until(tick,3000000);until(tick,3000000);
        auto actual=read("score")+256*mem.memRead(at("score")+1);
        char digits[6];snprintf(digits,6,"%05u",actual);
        for(int k=0;k<5;++k)require(mem.memRead(at("hud_wanted")+k)==uint8_t(digits[k]),"HUD score digits follow the score");
        require(actual>0 && mem.memRead(at("hud_wanted")+5)=='0' && mem.memRead(at("hud_wanted")+6)==' ',"HUD score ends with the units zero");
    }
    std::cout<<"PASS combo scoring, x8 cap, paddle/life reset\n";
    setup(); write("lives",3);
    auto setWord=[&](const char* name,unsigned v) {mem.memWrite(at(name),v&255);mem.memWrite(at(name)+1,v>>8);};
    auto getWord=[&](const char* name) {return unsigned(mem.memRead(at(name))+256*mem.memRead(at(name)+1));};
    setWord("next_life_score",500);setWord("score",498); // 4980 points
    mem.memWrite(at("bricks"),3);until(tick,3000000);
    require(read("lives")==3 && getWord("score")==499,"no extra life before 5000 points");
    setup();mem.memWrite(at("bricks"),2);until(tick,3000000);
    require(read("lives")==4 && getWord("score")==500 && getWord("next_life_score")==1000,"extra life at 5000 points, the next at 10000");
    // The score stops at 650000 points; the last extra life is the one at
    // 650000 and the threshold must not wrap around 16 bits.
    setup();write("lives",3);write("combo",21);write("multiplier",8);
    setWord("next_life_score",65000);setWord("score",64995);
    mem.memWrite(at("bricks"),1);until(tick,3000000);
    require(getWord("score")==65000 && read("lives")==4 && getWord("next_life_score")==65500,"score capped at 650000 points");
    require(mem.memRead(at("score_bcd"))==0x00 && mem.memRead(at("score_bcd")+1)==0x50 && mem.memRead(at("score_bcd")+2)==0x06,"BCD score follows the cap");
    setup();mem.memWrite(at("bricks"),1);until(tick,3000000);
    require(getWord("score")==65000 && read("lives")==4 && getWord("next_life_score")==65500,"nothing more past the cap");
    // (An even number of frames here keeps the page parity of the cadence
    // fixtures below.)
    until(tick,3000000);until(tick,3000000);until(tick,3000000);
    {char hudText[7];for(int k=0;k<6;++k)hudText[k]=char(mem.memRead(at("hud_wanted")+k));hudText[6]=0;
     require(std::string(hudText)=="650000","HUD shows the capped score");}
    setWord("score",0);setWord("next_life_score",500);for(int k=0;k<3;++k)mem.memWrite(at("score_bcd")+k,0);
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
    // Visible bonuses: red laser cannons on the paddle; red 4x7 piercing ball drawn one
    // line higher (round tips at x+1), cyan paddle again without the laser.
    pickup(5);until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page) {
        const int px=read("pad_x"),pw=read("pad_width"),py=read("pad_y");
        for(int y=py-3;y<py;++y)require(colorAt(page,px+1,y)==1 && colorAt(page,px+pw-2,y)==1,"red laser cannons on the paddle ends");
        require(colorAt(page,px+5,py+2)==14,"paddle body stays cyan");
    }
    pickup(6);setup();write("vx",0);write("vy",0);write("ball_x",80);write("ball_y",140);
    until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page) {
        require(colorAt(page,read("pad_x")+1,read("pad_y")-2)==0,"cannons gone without the laser");
        // Shaded sphere: pink left edge, red core, round tips over pixels 1-2.
        require(colorAt(page,80,139)==0 && colorAt(page,83,139)==0 && colorAt(page,82,139)!=0,"round tips");
        require(colorAt(page,80,141)==11 && colorAt(page,82,141)==1 && colorAt(page,82,144)==1,"shaded 4x7 piercing ball");
    }
    // Bolts: 1x4, white head over a yellow body, on whichever page shows them.
    pickup(5);clear();write("remaining",2);
    for(int b=0;b<2;++b) {mem.memWrite(at("shot_live")+b,1);mem.memWrite(at("shot_x")+b,40+b*30);mem.memWrite(at("shot_y")+b,128);}
    until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page) {
        int found=0;
        for(int y=100;y<=124 && !found;++y)
            if(colorAt(page,40,y)==15 && colorAt(page,40,y+1)==13 && colorAt(page,40,y+3)==13 && colorAt(page,40,y+4)==0
               && colorAt(page,70,y)==15 && colorAt(page,70,y+3)==13) found=y;
        require(found,"1x4 bolts with a white head on page "+std::to_string(page));
    }
    std::cout<<"PASS laser cannons, 1x4 bolts and shaded 4x7 piercing ball, both pages\n";
    // Flash is visible on both hidden pages and then restores the original
    // highlight. Shards are colored and leave the destroyed tile as background.
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
    // The tile shows the level background again (decade tile bg_on).
    for(int page=0;page<2;++page)for(int y=CB_TILE_TOP;y<CB_TILE_TOP+8;++y)for(int c=9;c<15;++c) {
        mem.memWrite((c&1)?0xC002:0xC003,0);
        auto v=mem.memRead(0x2000+page*0x2000+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+c/2);mem.memWrite(0xC002,0);
        require(v==mem.memRead(at("bg_tiles")+(read("bg_on")-1)*32+(y&7)*4+(c&3)),"expired shards/flash must leave no trail");
    }
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
    // The paddle moves diagonally: its whole footprint is erased each frame.
    write("mode",0);write("direction",1);write("vdirection",255);
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
    // Same frame with the P bonus: three red 4x7 balls instead of lasers.
    write("effect",6);mem.memWrite(at("shot_live"),0);mem.memWrite(at("shot_live")+1,0);
    {
        uint64_t low=~uint64_t(0),high=0;auto start=mem.getCycleCounter();
        for(int n=0;n<3;++n) {
            auto time=mem.getCycleCounter();until(tick,3000000);
            auto dt=mem.getCycleCounter()-time;low=std::min(low,dt);high=std::max(high,dt);
            require(read("ball_live") && extraRead(0,2) && extraRead(1,2) && read("capsule"),"piercing fixture remains active");
        }
        const double rate=3.0*clock/(mem.getCycleCounter()-start);
        std::cout<<"Piercing actors: "<<low<<".."<<high<<" cycles, "<<rate<<" fps\n";
        require(rate>=(pal?24.0:29.0) && high-low<uint64_t(pal?8000:5000),"piercing balls below expected VBL cadence or irregular intervals");
    }
    write("direction",0);write("vdirection",0);
    resetRound();
    auto ticks=[&](int n) {for(int k=0;k<n;++k)until(tick,3000000);};
    auto score=[&]() {return unsigned(mem.memRead(at("score"))+256*mem.memRead(at("score")+1));};
    // Vertical paddle: rises to mid-field, never through a tile.
    clear();write("remaining",2);write("mode",0);write("pad_x",60);
    mem.queueKey(0x0B);ticks(40);
    require(read("pad_y")==CB_PAD_MIN,"paddle rises to mid-field");
    require(!read("round_live") && read("ball_y")==CB_PAD_MIN-6,"attached ball follows the raised paddle");
    for(int page=0;page<2;++page) {
        require(colorAt(page,70,CB_PAD_MIN+2)==14 && colorAt(page,70,CB_PAD_MIN)==15,"raised paddle drawn on both pages");
        for(int y=CB_PAD_Y;y<CB_PAD_Y+5;++y)require(colorAt(page,70,y)==0,"previous paddle rows erased on both pages");
    }
    mem.queueKey('S');ticks(1);write("pad_y",CB_PAD_Y);ticks(2);
    mem.memWrite(at("bricks")+90,1);
    mem.queueKey(0x0B);ticks(40);
    require(read("pad_y")==CB_PAD_BLOCK,"a tile above keeps the paddle below the grid");
    mem.queueKey('S');ticks(1);
    mem.memWrite(at("bricks")+90,0);write("pad_x",20);
    mem.queueKey(0x0B);ticks(10);
    require(read("pad_y")==CB_PAD_MIN,"paddle rises where no tile is above");
    mem.queueKey('S');ticks(1);mem.memWrite(at("bricks")+90,1);
    mem.queueKey('D');ticks(12);
    require(read("pad_x")==71-2-read("pad_width"),"paddle stops at the tile on its right");
    mem.queueKey('S');ticks(1);mem.memWrite(at("bricks")+85,1);
    mem.queueKey('A');ticks(12);
    require(read("pad_x")==16+11,"paddle stops at the tile on its left");
    mem.queueKey('S');ticks(1);
    mem.queueKey(0x0A);ticks(40);mem.queueKey('S');ticks(1);
    require(read("pad_y")==CB_PAD_Y,"paddle returns to the floor");
    // Rising in a diagonal from under a bottom-row tile (edge columns and the
    // middle): the paddle slides on below the tile, four pixels a frame and
    // inside the field, and rises only once clear of it.
    for(int col : {0,5,6,11}) {
        const bool leftward=col>5;
        setup();mem.memWrite(at("bricks")+84+col,1);
        const int tx=mem.memRead(at("tile_x")+84+col),w=read("pad_width");
        const int start=std::min(136-w,std::max(4,leftward ? tx+9-w : tx-1));
        write("mode",0);write("pad_x",start);write("pad_y",CB_PAD_BLOCK);
        write("direction",leftward?255:1);write("vdirection",255);
        for(int n=1;n<=12;++n) {
            ticks(1);
            const int x=read("pad_x"),y=read("pad_y");
            require(x==start+(leftward?-4:4)*n,"diagonal rise under a tile: no sideways jump (column "+std::to_string(col)+", x="+std::to_string(x)+")");
            require(x>=4 && x+w<=136,"diagonal rise under a tile: paddle inside the field");
            if(tx<x+w+2 && tx+11>x)require(y==CB_PAD_BLOCK,"diagonal rise: the paddle stays below the tile above it");
        }
        require(read("pad_y")<CB_PAD_BLOCK,"the paddle rises once clear of the tile");
        write("direction",0);write("vdirection",0);
    }
    // ENLARGE caught at tile height, between a bottom-row tile and a wall
    // where the wider paddle has no room: it goes back below the tiles.
    {
        const auto baseWidth=read("base_width"),padWidth=read("pad_width");
        for(int side=0;side<2;++side) {
            setup();write("mode",0);write("effect",0);write("base_width",18);write("pad_width",18);
            const int col=side?9:2,tx=mem.memRead(at("tile_x")+84+col);
            mem.memWrite(at("bricks")+84+col,1);
            const int px=side ? 118 : tx-2-18;
            write("pad_x",px);write("pad_y",105);ticks(1);
            require(read("pad_x")==unsigned(px) && read("pad_y")==105,"an 18-pixel paddle fits between the tile and the wall");
            write("capsule",1);write("cap_x",px+6);write("cap_y",105-4);
            for(int n=0;n<4;++n) {
                ticks(1);
                require(read("effect")==1 && read("pad_width")==26,"ENLARGE caught at tile height");
                require(read("pad_x")>=4 && read("pad_x")+26u<=136u,"the enlarged paddle stays inside the field (x="+std::to_string(read("pad_x"))+")");
                require(read("pad_y")==CB_PAD_BLOCK,"the enlarged paddle goes back below the tiles");
            }
        }
        setup();write("effect",0);write("base_width",baseWidth);write("pad_width",padWidth);write("pad_y",CB_PAD_Y);ticks(1);
    }
    // A paddle that rises past a falling capsule within one frame (a stick
    // or a mouse can) still catches it.
    {
        const auto previousMode=read("mode");
        setup();write("effect",0);write("ball_live",0);write("round_live",0);
        mem.setPaddle(0,128);mem.setPaddle(1,160);mem.queueKey('J');ticks(4);
        const int low=read("pad_y");
        write("capsule",2);write("cap_x",read("pad_x")+6);write("cap_y",low-8);
        mem.setPaddle(1,60);ticks(3);
        require(low-int(read("pad_y"))>=20,"the stick lifts the paddle by 20 lines or more at once");
        require(read("effect")==2 && !read("capsule"),"a paddle rising past a capsule catches it");
        mem.setPaddle(1,255);write("mode",previousMode);write("effect",0);write("pad_y",CB_PAD_Y);ticks(1);
    }
    setup();write("pad_x",60);write("pad_y",140);write("ball_x",70);write("ball_y",140-6);write("dy",1);ticks(1);
    require(read("dy")==255 && read("ball_y")<140-5,"ball rebounds on the raised paddle");
    // The paddle moves before the ball: sliding under a ball already below
    // its top line, or rising into one, must not let it pass through.
    setup();write("pad_x",20);write("pad_y",140);write("ball_x",70);write("ball_y",140-3);
    write("dy",1);write("vx",0);write("vy",0);ticks(1);
    require(read("dy")==1 && read("ball_y")==140-3,"ball beside the paddle keeps falling");
    write("pad_x",60);ticks(1);
    require(read("dy")==255 && read("ball_y")<=140-6,"paddle sliding under a falling ball bounces it");
    write("ball_y",140+2);write("dy",255);ticks(1);
    require(read("ball_y")<=140-6 && read("dy")==255,"rising paddle lifts a ball out of its body");
    // Spin: the paddle's own motion this frame bends the rebound.
    setup();write("pad_x",64);write("pad_y",CB_PAD_Y);write("ball_x",73);write("ball_y",CB_PAD_Y-6);write("dy",1);ticks(1);
    require(read("dy")==255 && read("dx")==255,"still paddle: zone 3 bounces left");
    setup();write("pad_x",60);write("pad_y",CB_PAD_Y);write("ball_x",73);write("ball_y",CB_PAD_Y-6);write("dy",1);
    mem.queueKey('D');ticks(1);mem.queueKey('S');ticks(1);
    require(read("pad_x")==64 && read("dx")==1,"paddle sliding right drags the bounce right");
    setup();write("pad_x",60);write("pad_y",150);write("ball_x",60);write("ball_y",141);write("dy",1);
    mem.queueKey(0x0B);ticks(1);mem.queueKey('S');ticks(1);
    require(read("pad_y")==147 && read("vx")==104,"rising paddle steepens the bounce");
    // Catch keeps the ball where it met the paddle, and carries it there.
    setup();write("effect",3);write("pad_x",60);write("pad_y",CB_PAD_Y);write("ball_x",75);write("ball_y",CB_PAD_Y-6);write("dy",1);ticks(1);
    require(!read("round_live") && read("ball_x")==75,"catch holds the ball at its impact point");
    mem.queueKey('A');ticks(1);mem.queueKey('S');ticks(1);
    require(read("pad_x")==56 && read("ball_x")==56+15,"caught ball rides at its offset");
    write("effect",0);
    std::cout<<"PASS vertical paddle: mid-field limit, tiles above and aside, rebound, spin, catch point, both pages\n";
    // The mouse height is the paddle's, from the floor to mid-field: no
    // travel is lost at either end, nor after a lost life.
    {
        const auto modeBefore=read("mode");
        resetRound();clear();write("remaining",2);write("mode",1);ticks(2);
        auto vertical=[&](int lines) {
            for(int i=0;i<std::abs(lines);++i) {hostY+=lines<0?-1:1; host();run(20000);}
            until(tick,3000000);until(tick,3000000);
        };
        vertical(-(CB_PAD_Y-CB_PAD_MIN)-16);
        require(read("pad_y")==CB_PAD_MIN && read("mouse_y")==CB_PAD_MIN,"mouse pushed up: paddle at mid-field");
        // (How far 30 host steps go depends on the mouse: a //c counts more.)
        vertical(30);
        const auto lowered=read("pad_y");
        require(lowered>CB_PAD_MIN+10 && lowered<CB_PAD_Y && lowered==read("mouse_y"),"mouse pulled back: the paddle comes down at once, no dead travel at the top");
        auto livesBefore=read("lives");
        if(livesBefore<2) {write("lives",3);livesBefore=3;}
        write("ball_live",1);write("round_live",1);write("ball_x",120);write("ball_y",CB_LOST_Y-1);write("dy",1);write("vx",0);write("vy",255);write("fraction_y",255);
        until(tick,3000000);until(tick,3000000);
        require(read("lives")==livesBefore-1 && !read("round_live"),"a life is lost with the paddle raised");
        require(read("pad_y")==lowered,"the paddle stays at the mouse height after a lost life");
        vertical(-(CB_PAD_Y-CB_PAD_MIN));
        require(read("pad_y")==CB_PAD_MIN,"the paddle still rises to mid-field after a lost life");
        vertical(CB_PAD_Y-CB_PAD_MIN+16);
        require(read("pad_y")==CB_PAD_Y && read("mouse_y")==CB_PAD_Y,"mouse pulled down: paddle back on the floor");
        write("lives",livesBefore);write("mode",modeBefore);ticks(1);
        std::cout<<"PASS mouse height: absolute over the paddle's travel, kept after a lost life\n";
    }
    // Joystick / paddles: J selects them; paddle 0 (stick X) sets the
    // paddle centre, paddle 1 (stick Y) its height, button 0 launches. The
    // analog read uses the wait before presentation, never the frame time.
    {
        auto previousMode=read("mode");
        resetRound();mem.setPaddle(0,0);mem.setPaddle(1,0);mem.queueKey('J');ticks(3);
        require(read("mode")==2,"J selects the joystick");
        require(read("pad_x")==4 && read("pad_y")==CB_PAD_MIN,"stick up-left: paddle top-left");
        mem.setPaddle(0,255);mem.setPaddle(1,255);ticks(3);
        require(read("pad_x")+read("pad_width")==136 && read("pad_y")>=CB_PAD_Y-2,"stick down-right: paddle bottom-right");
        mem.setPaddle(0,128);mem.setPaddle(1,128);ticks(3);
        int centre=read("pad_x")+read("pad_width")/2;
        require(centre>=67 && centre<=71,"centred stick: centred paddle ("+std::to_string(centre)+")");
        mem.setPaddleButton(0,true);ticks(2);mem.setPaddleButton(0,false);
        require(read("round_live")==1,"button 0 launches the ball");
        // Worst case for the read: both timers at full scale.
        mem.setPaddle(0,255);mem.setPaddle(1,255);ticks(2);
        shortest=~uint64_t(0);longest=0;stamp=mem.getCycleCounter();
        for(int n=0;n<10;++n) {
            auto time=mem.getCycleCounter();until(tick,3000000);
            auto dt=mem.getCycleCounter()-time;shortest=std::min(shortest,dt);longest=std::max(longest,dt);
        }
        fps=10.0*clock/(mem.getCycleCounter()-stamp);
        std::cout<<"Joystick play: "<<shortest<<".."<<longest<<" cycles, "<<fps<<" fps\n";
        require(fps>=(pal?24.0:29.0) && longest-shortest<uint64_t(pal?8000:5000),"joystick read keeps the frame rate");
        write("mode",previousMode);write("pad_x",60);write("pad_y",CB_PAD_Y);ticks(1);
        std::cout<<"PASS joystick/paddles: J, both axes absolute, button, full-scale read within the frame rate\n";
    }
    // Enemies: tiles block them; ball, laser and paddle destroy them.
    auto enemy=[&](int i,int x,int y,int dx,int dy) {
        mem.memWrite(at("enemy_x")+i,x);mem.memWrite(at("enemy_y")+i,y);
        mem.memWrite(at("enemy_dx")+i,uint8_t(dx));mem.memWrite(at("enemy_dy")+i,uint8_t(dy));
        mem.memWrite(at("enemy_live")+i,1);
    };
    auto alive=[&](int i) {return mem.memRead(at("enemy_live")+i)!=0;};
    resetRound();clear();write("remaining",2);
    mem.memWrite(at("bricks")+13,1);enemy(0,17,19,1,1);ticks(5);
    require(alive(0) && mem.memRead(at("enemy_y"))==20 && mem.memRead(at("enemy_x"))==22,"tile below holds the enemy, which slides sideways");
    for(int i=0;i<3;++i)ticks(1);
    require(mem.memRead(at("enemy_y"))>20,"enemy drops once past the tile");
    write("enemy_live",0);clear();write("remaining",2);
    setup();enemy(0,9,18,1,1);auto points=score();ticks(1);
    require(!alive(0) && read("dy")==1 && score()==points+10,"ball destroys an enemy, rebounds and scores 100");
    require(mem.memRead(at("particle_life"))||mem.memRead(at("particle_life")+1)||mem.memRead(at("particle_life")+2)||mem.memRead(at("particle_life")+3),"enemy bursts into shards");
    resetRound();clear();write("remaining",2);
    mem.memWrite(at("shot_live"),1);mem.memWrite(at("shot_x"),40);mem.memWrite(at("shot_y"),100);
    enemy(0,39,90,1,1);points=score();ticks(1);
    require(!alive(0) && !mem.memRead(at("shot_live")) && score()==points+10,"laser destroys an enemy");
    // Below the grid the first enemy picks a new heading when the frame
    // count is a multiple of sixteen: keep these frames clear of it.
    write("frames",1);
    enemy(0,read("pad_x")+2,CB_PAD_Y-6,1,1);points=score();ticks(1);
    require(!alive(0) && score()==points+10,"paddle contact destroys an enemy");
    enemy(0,120,CB_LOST_Y-7,1,1);points=score();ticks(3);
    require(!alive(0) && score()==points,"enemy leaves through the floor");
    // The second enemy weaves below the grid: up and down, drifting down.
    resetRound();clear();write("remaining",2);enemy(1,60,CB_GRID_END+30,1,1);
    {int lo=255,hi=0,turns=0,last=1;
     for(int k=0;k<64;++k) {
         ticks(1);require(alive(1),"weaving enemy stays on the field");
         int y=mem.memRead(at("enemy_y")+1),d=int8_t(mem.memRead(at("enemy_dy")+1));
         lo=std::min(lo,y);hi=std::max(hi,y);if(d && d!=last){++turns;last=d;}
     }
     require(turns>=3 && hi-lo>=16 && mem.memRead(at("enemy_y")+1)>CB_GRID_END+30,"second enemy weaves down in waves");}
    write("enemy_live",0);mem.memWrite(at("enemy_live")+1,0);
    setup();write("enemy_hold",0);write("enemy_timer",1);ticks(1);
    require(alive(0),"an enemy arrives when its timer expires");
    {
        int x=mem.memRead(at("enemy_x")),y=mem.memRead(at("enemy_y"));
        require((y==CB_FIELD_TOP+1 || y==CB_FIELD_TOP+2 || y>=CB_GRID_END+2) && x>=4 && x<=133,"enemy enters through a gate");
    }
    write("enemy_hold",1);
    resetRound();write("lives",3);write("pad_x",60);enemy(0,20,60,1,1);enemy(1,110,60,-1,1);
    points=score();write("capsule",4);write("cap_x",65);write("cap_y",CB_PAD_Y-5);ticks(1);
    require(read("effect")==4 && !alive(0) && !alive(1) && score()==points+20,"multiball capsule blows up the enemies");
    write("enemy_hold",0);write("enemy_timer",1);ticks(1);
    require(!alive(0) && !alive(1),"no enemy arrives while extra balls fly");
    write("enemy_hold",1);
    // Enemy look: a spool (full bars in its colour, narrow white core), not a
    // ball. Held among the cleared tiles, where it does not wander.
    resetRound();clear();write("remaining",2);enemy(0,60,60,1,0);mem.memWrite(at("enemy_dx"),0);
    until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page) {
        const int ex=mem.memRead(at("enemy_x")),ey=mem.memRead(at("enemy_y"));const unsigned c=mem.memRead(at("enemy_color"));
        const unsigned bar=colorAt(page,ex,ey);(void)c;
        require(bar!=0 && bar!=15 && colorAt(page,ex+3,ey)==bar && colorAt(page,ex,ey+5)==bar && colorAt(page,ex+3,ey+5)==bar,"enemy bars in one colour");
        require(colorAt(page,ex+1,ey+2)==15 && colorAt(page,ex+2,ey+3)==15 && colorAt(page,ex,ey+2)==0 && colorAt(page,ex+3,ey+3)==0,"enemy core narrow and white");
    }
    write("enemy_live",0);
    // The second enemy is a TIE fighter: wings in its colour, white core
    // (held among the cleared tiles, where it does not weave).
    resetRound();clear();write("remaining",2);enemy(1,60,60,1,0);mem.memWrite(at("enemy_dx")+1,0);
    until(tick,3000000);until(tick,3000000);
    for(int page=0;page<2;++page) {
        const int ex=mem.memRead(at("enemy_x")+1),ey=mem.memRead(at("enemy_y")+1);const unsigned c=mem.memRead(at("enemy_color")+1);
        const unsigned wing=colorAt(page,ex,ey);(void)c;
        require(wing!=0 && wing!=15 && colorAt(page,ex+3,ey+5)==wing && colorAt(page,ex,ey+3)==wing && colorAt(page,ex+3,ey+2)==wing,"TIE wings in one colour");
        require(colorAt(page,ex+1,ey)==0 && colorAt(page,ex+2,ey+5)==0 && colorAt(page,ex+1,ey+2)==15 && colorAt(page,ex+2,ey+3)==15,"TIE core white between open ends");
    }
    mem.memWrite(at("enemy_live")+1,0);
    std::cout<<"PASS enemies: tiles, sliding, ball/laser/paddle hits, floor exit, weave, arrival, multiball, spool and TIE looks\n";
    // Heaviest enemy frame: ball, two lasers, capsule, four shards, two
    // enemies and a paddle moving diagonally (full erase every frame).
    resetRound();pickup(5);clear();write("remaining",10);
    setup();write("speed",7);write("ball_x",70);write("ball_y",40);write("dy",1);write("vx",0);write("vy",255);
    for(int b=0;b<2;++b) {mem.memWrite(at("shot_live")+b,1);mem.memWrite(at("shot_x")+b,8+b*10);mem.memWrite(at("shot_y")+b,CB_GRID_END+60);}
    write("capsule",6);write("cap_x",120);write("cap_y",130);
    for(int b=0;b<4;++b) {
        mem.memWrite(at("particle_x")+b,30+b*20);mem.memWrite(at("particle_y")+b,60);mem.memWrite(at("particle_life")+b,6);
        mem.memWrite(at("particle_color")+b,9);mem.memWrite(at("particle_dx")+b,1);
    }
    enemy(0,20,120,1,1);enemy(1,110,120,-1,1);
    write("pad_x",20);mem.queueKey('D');ticks(1);mem.queueKey(0x0B);
    shortest=~uint64_t(0);longest=0;stamp=mem.getCycleCounter();
    for(int n=0;n<3;++n) {
        auto time=mem.getCycleCounter();until(tick,3000000);
        auto dt=mem.getCycleCounter()-time;shortest=std::min(shortest,dt);longest=std::max(longest,dt);
        require(read("ball_live") && alive(0) && alive(1) && read("capsule"),"enemy fixture remains active");
        for(int b=0;b<2;++b)require(mem.memRead(at("shot_live")+b),"two lasers in enemy fixture");
        for(int b=0;b<4;++b)require(mem.memRead(at("particle_life")+b),"four shards in enemy fixture");
    }
    fps=3.0*clock/(mem.getCycleCounter()-stamp);
    std::cout<<"Enemy actors: "<<shortest<<".."<<longest<<" cycles, "<<fps<<" fps\n";
    require(fps>=(pal?24.0:29.0) && longest-shortest<uint64_t(pal?8000:5000),"enemy actors below expected VBL cadence or irregular intervals");
    mem.queueKey('S');ticks(1);
    int ex[2],ey[2];
    for(int i=0;i<2;++i) {ex[i]=mem.memRead(at("enemy_x")+i);ey[i]=mem.memRead(at("enemy_y")+i);mem.memWrite(at("enemy_live")+i,0);}
    // The bolts go too: one may be crossing the place an enemy just left.
    for(int b=0;b<2;++b)mem.memWrite(at("shot_live")+b,0);
    ticks(2);
    for(int page=0;page<2;++page)for(int i=0;i<2;++i)for(int y=0;y<6;++y)for(int x=0;x<4;++x)
        require(colorAt(page,ex[i]+x,ey[i]+y)==0,"enemy sprite restored on both pages");
    std::cout<<"PASS enemy cadence and clean save-under on both pages\n";
    resetRound();
    // Level transitions from either displayed page must never write to it:
    // the SECTOR CLEAR banner is presented, then the board built behind it.
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
        require(videoWrites.flips==previousFlips+2,"sector banner then new board: two hardware page flips");
        require(videoWrites.badFlips==0,"page flip outside vertical blank");
        require(read("level")==previousLevel+1,"new level loaded");
        require(read("dhgr_display")==page,"banner and board each presented once");
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
    // Mixed DHGR: every byte is a colour byte (bit 7 set) except the mono
    // HUD band, whose text shows as 560-dot mono on a Chat Mauve card.
    for(int page=0;page<2;++page)for(int bank=0;bank<2;++bank) {
        mem.memWrite(bank?0xC003:0xC002,0);
        for(int y=0;y<192;++y)for(int b=0;b<40;++b) {
            auto v=mem.memRead(0x2000+page*0x2000+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+b);
            const bool band=y>=CB_HUD_Y && y<CB_HUD_Y+7;
            require(bool(v&0x80)!=band,"bit 7: colour bytes set, HUD text band clear (page "+std::to_string(page)+" y "+std::to_string(y)+" byte "+std::to_string(b)+")");
        }
    }
    mem.memWrite(0xC002,0);
    std::cout<<"PASS Chat Mauve mixed DHGR: colour bytes keep bit 7, HUD band mono, both pages and banks\n";
    // ESC menu: resume keeps the game, any board can be played, sound can be
    // muted, and the title opens and closes the same menu.
    {
        write("paused",0);write("enemy_hold",1);
        auto lv=read("level"),left=read("remaining"),li=read("lives");
        mem.queueKey(27);until(tick,20000000);
        require(read("state")==7 && read("menu_level")==lv,"ESC in play opens the menu on the current level");
        mem.queueKey(27);until(tick,40000000);
        require(read("state")==1 && read("level")==lv && read("remaining")==left && read("lives")==li,"ESC resumes the same game");
        mem.queueKey(27);until(tick,20000000);
        mem.queueKey('S');until(tick,20000000);
        require(read("sound_muted")==1,"S mutes the sound");
        mem.queueKey('S');until(tick,20000000);
        require(read("sound_muted")==0,"S restores the sound");
        // Arrows only reach the sectors reached so far, and wrap.
        write("records_progress",4);write("menu_level",3);mem.queueKey(0x15);until(tick,20000000);
        require(read("menu_level")==4,"arrows choose the level");
        mem.queueKey(0x15);until(tick,20000000);
        require(read("menu_level")==0,"arrows stop at the farthest sector reached");
        mem.queueKey(8);until(tick,20000000);
        require(read("menu_level")==4,"left from the first sector wraps to the farthest reached");
        // The AUX level bank: boards chosen in the menu match levels.txt.
        {
            std::ifstream lt("src/levels.txt");std::string ln;std::vector<std::vector<int>> boards;std::vector<int> cur;
            while(std::getline(lt,ln)) {
                if(ln.empty() || ln[0]==';')continue;
                if(ln.size()==12 && ln.find_first_not_of(".123#")==std::string::npos) {
                    for(char c:ln)cur.push_back(c=='.'?0:c=='#'?255:c-'0');
                    if(cur.size()==96){boards.push_back(cur);cur.clear();}
                }
            }
            require(boards.size()==CB_LEVELS,"levels.txt has every board");
            for(int pick : {CB_LEVELS-1,29,12}) {
                write("menu_level",pick);mem.queueKey(13);until(tick,40000000);
                require(read("state")==1 && read("level")==pick,"menu starts the chosen board");
                for(int i=0;i<96;++i)require(mem.memRead(at("bricks")+i)==boards[pick][i],"board "+std::to_string(pick)+" loaded from the AUX bank");
                mem.queueKey(27);until(tick,20000000);
            }
            // Decade backgrounds above the paddle zone: level 11 uses tile 2.
            write("menu_level",10);mem.queueKey(13);until(tick,40000000);
            require(read("bg_on")==2,"level 11 selects the second background");
            auto byteAt=[&](int page,int y,int c) {
                mem.memWrite((c&1)?0xC002:0xC003,0);
                auto v=mem.memRead(0x2000+page*0x2000+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+c/2);
                mem.memWrite(0xC002,0);return unsigned(v);
            };
            auto tile=[&](int y,int c) {return unsigned(mem.memRead(at("bg_tiles")+32+(y&7)*4+(c&3)));};
            for(int page=0;page<2;++page) {
                for(int y=CB_FIELD_TOP;y<CB_TILE_TOP;++y)for(int c=4;c<76;++c)
                    require(byteAt(page,y,c)==tile(y,c),"background above the tiles, page "+std::to_string(page));
                for(int y=CB_BG_END+20;y<CB_BG_END+40;++y)require(byteAt(page,y,6)==0x80,"paddle zone stays black");
            }
            setup();mem.memWrite(at("bricks"),1);until(tick,3000000);until(tick,3000000);until(tick,3000000);
            require(!mem.memRead(at("bricks")),"brick destroyed over the background");
            for(int n=0;n<4;++n)mem.memWrite(at("particle_life")+n,0);
            write("ball_x",100);write("ball_y",150);until(tick,3000000);until(tick,3000000);
            for(int page=0;page<2;++page)for(int y=CB_TILE_TOP;y<CB_TILE_TOP+8;++y)for(int c=4;c<7;++c)
                require(byteAt(page,y,c)==tile(y,c),"destroyed tile shows the background again");
            mem.queueKey(27);until(tick,20000000);
            write("menu_level",4);
        }
        mem.queueKey(13);until(tick,40000000);
        require(read("state")==1 && read("level")==4 && read("score")==0,"ENTER plays the chosen level");
        mem.queueKey(27);until(tick,20000000);mem.queueKey('T');until(tick,20000000);
        require(read("state")==0,"T returns to the title");
        mem.queueKey(27);until(tick,20000000);
        require(read("state")==7 && read("menu_level")==4,"ESC on the title opens the menu on the farthest sector");
        mem.queueKey(27);until(tick,20000000);
        require(read("state")==0,"ESC goes back to the title");
        mem.queueKey(' ');until(tick,40000000);write("enemy_hold",1);
        require(read("state")==1,"game starts again from the title");
        std::cout<<"PASS ESC menu: resume, level choice, AUX level bank, backgrounds, sound, title\n";
    }
    // Attract mode: 15 s idle on the title start an autopilot demo, silent,
    // without records; a key or a lost life returns to the title.
    {
        require(read("video_pal")==unsigned(pal),"50 Hz detection");
        auto bestScore=mem.memRead(at("best_score"))+256*mem.memRead(at("best_score")+1);
        write("paused",0);write("state",0);write("demo",0);
        // Mouse motion restarts the wait: let the emulated mouse settle first.
        for(int still=0;still<60;) {
            auto mx=read("mouse_x"),my=read("mouse_y");until(tick,3000000);
            still=(mx==read("mouse_x") && my==read("mouse_y")) ? still+1 : 0;
        }
        mem.memWrite(at("demo_idle"),0);mem.memWrite(at("demo_idle")+1,0);
        // The tick that starts the demo also builds its board: time its start.
        auto idleStart=mem.getCycleCounter(),trigger=idleStart;
        while(!read("demo") && mem.getCycleCounter()-idleStart<uint64_t(20*clock)) {
            trigger=mem.getCycleCounter();until(tick,3000000);
        }
        const double idle=double(trigger-idleStart)/clock;
        require(read("demo") && read("state")==1,"demo starts after idle time");
        require(idle>14.8 && idle<15.2,"demo waits 15 s ("+std::to_string(idle)+" s)");
        ticks(60);
        require(read("demo") && read("round_live") && !read("sound_active"),"autopilot plays silently");
        mem.queueKey(' ');ticks(1);
        require(read("state")==0 && !read("demo"),"a key returns from the demo to the title");
        require(bestScore==mem.memRead(at("best_score"))+256*mem.memRead(at("best_score")+1),"demo leaves the best score");
        mem.memWrite(at("demo_idle"),pal?238:132);mem.memWrite(at("demo_idle")+1,pal?2:3);ticks(1);
        require(read("demo"),"demo restarts");
        ticks(30);write("ball_live",0);extra(0,2,0);extra(1,2,0);ticks(1);
        require(read("state")==0 && !read("demo"),"a lost life ends the demo");
        // Left alone, a demo lasts 60 s of game frames at 60 Hz as at 50 Hz,
        // one frame per two refreshes (the balls are kept from the floor so
        // that no lost life ends it sooner).
        mem.memWrite(at("demo_idle"),pal?238:132);mem.memWrite(at("demo_idle")+1,pal?2:3);ticks(1);
        require(read("demo"),"demo restarts again");
        int demoFrames=0;
        while(read("demo") && demoFrames<2400) {
            if(read("ball_y")>150)write("dy",255);
            for(int b=0;b<2;++b)if(extraRead(b,1)>150)extra(b,4,255);
            until(tick,20000000);++demoFrames;
        }
        const double played=demoFrames*2.0/(pal?50:60);
        require(read("state")==0 && !read("demo"),"the demo ends by itself");
        require(played>59.9 && played<60.1,"a demo lasts 60 s ("+std::to_string(played)+" s)");
        std::cout<<"PASS attract mode: 15 s idle, 50 Hz detection, silent autopilot, key/lost-life exit, 60 s\n";
        mem.queueKey(' ');ticks(2);write("enemy_hold",1);
        require(read("state")==1 && !read("demo"),"title still starts a game after the demo");
    }
    // The joystick, once chosen with J, stays the way of playing: through a
    // game over (button or SPACE), and through a demo. K and M change it.
    {
        auto gameOver=[&]() {
            write("lives",1);write("score",0);mem.memWrite(at("score")+1,0);
            for(int k=0;k<3;++k)mem.memWrite(at("score_bcd")+k,0);
            extra(0,2,0);extra(1,2,0);write("ball_live",1);write("round_live",1);
            write("ball_x",120);write("ball_y",CB_LOST_Y-1);write("dy",1);write("vx",0);write("vy",255);write("fraction_y",255);
            ticks(3);
            require(read("state")==2,"game over");
        };
        auto button=[&]() {mem.setPaddleButton(0,true);ticks(2);mem.setPaddleButton(0,false);ticks(1);};
        mem.setPaddle(0,128);mem.setPaddle(1,255);mem.queueKey('J');ticks(3);
        require(read("state")==1 && read("mode")==2,"J selects the joystick in a game");
        gameOver();button();
        require(read("state")==1 && read("mode")==2,"the joystick button starts the next game with the joystick");
        mem.setPaddle(0,0);ticks(3);
        require(read("pad_x")==4,"and the stick still moves the paddle");
        mem.setPaddle(0,128);
        gameOver();mem.queueKey(' ');ticks(2);
        require(read("state")==1 && read("mode")==2,"SPACE starts the next game with the joystick");
        write("state",0);mem.memWrite(at("demo_idle"),pal?238:132);mem.memWrite(at("demo_idle")+1,pal?2:3);ticks(1);
        require(read("demo"),"demo with the joystick chosen");
        ticks(5);mem.queueKey(' ');ticks(1);
        require(read("state")==0 && !read("demo") && read("mode")==2,"a demo leaves the joystick chosen");
        button();
        require(read("state")==1 && read("mode")==2,"the joystick button starts a game after a demo");
        gameOver();mem.queueKey('K');ticks(2);
        require(read("state")==1 && read("mode")==0,"K starts with the keyboard");
        gameOver();mem.queueKey('M');ticks(2);
        require(read("state")==1 && read("mode")==1,"M starts with the mouse");
        mem.setPaddle(1,128);
        std::cout<<"PASS joystick kept through game over and demo; K and M change the way of playing\n";
    }
    // Clean exit must disable mouse and leave a valid empty /RAM.
    if (alternate) cpu.softReset();
    else {
        // ESC opens the menu; Q quits to ProDOS from there.
        mem.queueKey(27);until(tick,20000000);
        require(read("state")==7,"ESC opens the menu");
        mem.queueKey('Q');
    }
    until(at("prodos_quit"),20000000);
    require(!read("mouse_slot"),"mouse disabled on exit");
    require(!read("timing_mode"),"VBL handler deallocated on exit/reset");
    require((mem.memRead(0xC01A)&0x80)!=0,"text restored on exit");
    require(chatMauve->dhgrMode()==LeChatMauveCard::DhgrMode::COL140,"RGB card back to 140 colour on exit");
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
    stackCheck();
    return 0;
 } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
