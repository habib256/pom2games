// GPL-3.0. Native HUD pointer-lifetime audit; independent pixels/cache and
// paired ordered stores/BSS/register results. The IRQ saves, borrows, restores
// all cc65 pointer/tmp scratch, with actual VIA T1 entry-frame verification.
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <vector>
#ifndef HGRC_TEST_BAD_IRQ
#define HGRC_TEST_BAD_IRQ 0
#endif
#ifndef HGRC_TEST_BAD_LOW
#define HGRC_TEST_BAD_LOW 0
#endif
using namespace pom2;
using Event=std::pair<unsigned,unsigned>;
static unsigned offset(unsigned y) {
    return ((y&7)<<10)+((y&56)<<4)+(y>>6)*40;
}
struct Result {
    unsigned a,x,y,p;
    unsigned long long cycles;
    std::vector<Event> stores;
    std::vector<unsigned char>bss;
};
struct Instance {
    Core core;
    std::map<std::string,unsigned>L;
    std::vector<unsigned char>image,font;
    unsigned base,bss,bss_size,ready,audit_field,serial=0,calls=0,irqs=0,deferrals=0,large_borrows=0,pixel_writes=0,cache_writes=0,entry_irqs=0;
    unsigned long long cycles=0;
    std::map<unsigned,unsigned> preserves;
    std::map<unsigned,unsigned> entry_fields;
    std::vector<unsigned char>handler;
    unsigned a(const char*n) {
        return L.at(std::string(".")+n);
    }
    unsigned rd(unsigned p) {
        return core.read(p);
    }
    void wr(unsigned p,unsigned v) {
        core.write(p,v);
    }
    unsigned word(unsigned p) {
        return rd(p)|(rd(p+1)<<8);
    }
    void put(unsigned p,unsigned v) {
        wr(p,v);
        wr(p+1,v>>8);
    }
    Instance(const char*binary,const char*labels,const char*rom,unsigned start,bool cmos):core(CoreConfig{cmos?CpuModel::CMOS65C02:CpuModel::NMOS6502,VideoTiming::NTSC,true}),base(start) {
        probe::labels(L,labels);
        std::ifstream f(binary,std::ios::binary);
        image.assign(std::istreambuf_iterator<char>(f),{});
        assert(core.loadRom(rom));
        assert(core.attachMockingboard());
        std::array<unsigned char,0xc000>ram;
        for (unsigned i=0;i<ram.size();++i)ram[i]=(i*37+(i>>8)*11)&255;
        for (auto bank:{RamBank::Main,RamBank::Aux})assert(core.writeRam(bank,0,ram.data(),ram.size()));
        assert(core.writeRam(RamBank::Main,base,image.data(),image.size()));
        audit_field=L.count(".hud8_audit_field")?a("hud8_audit_field"):0;
        assert(a("__ZEROPAGE_RUN__")+a("__ZEROPAGE_SIZE__")<=0xA0);
        bss=a("__BSS_RUN__");
        bss_size=a("__BSS_SIZE__");
        for (unsigned p=bss;p<bss+bss_size;++p)wr(p,0);
        assert(rd(a("_hgr_build_rows"))==0xad);
        ready=word(a("_hgr_build_rows")+1);
        for (unsigned i=0;i<768;++i)font.push_back(rd(a("_hgr_font")+i));
        handler={
            0x48,0x8a,0x48,0x98,0x48
        };
        std::vector<unsigned>scratch;
        for (const char*n:{"ptr1","ptr2","ptr3","ptr4"}) {
            scratch.push_back(a(n));
            scratch.push_back(a(n)+1);
        }
        for (const char*n:{"tmp1","tmp2","tmp3","tmp4"})scratch.push_back(a(n));
        for (unsigned p:scratch)handler.insert(handler.end(),{0xa5,(unsigned char)p,0x48});
        handler.insert(handler.end(),{0xa9,0xa5});
        for (unsigned p:scratch)handler.insert(handler.end(),{0x85,(unsigned char)p});
        handler.insert(handler.end(),{0xad,0x04,0xc4,0xee,0x02,0x10,0xd0,0x03,0xee,0x03,0x10});
        for (auto it=scratch.rbegin();it!=scratch.rend();++it) {
            if (HGRC_TEST_BAD_IRQ && *it==a("ptr3"))handler.insert(handler.end(),{0x68,0xea,0xea});
            else handler.insert(handler.end(),{0x68,0x85,(unsigned char)*it});
        }
        handler.insert(handler.end(),{0x68,0xa8,0x68,0xaa,0x68,0x38,0x40});
        assert(handler.size()<256);
        assert(core.writeRam(RamBank::Main,0x900,handler.data(),handler.size()));
        for (const char*n:{"_hgr_get_draw_page","_hgr_utoa","_hgr_build_rows","_hgr_hud8_cell_run"})preserves[a(n)]=0;
    }
    void draw(std::array<unsigned char,0xc000>&wanted,bool small,unsigned x,unsigned y,unsigned width,unsigned ch,unsigned page) {
        unsigned scale=small?1:2;
        for (unsigned row=0;row<8*scale;++row) {
            unsigned from=x/7,to=(x+width-1)/7;
            for (unsigned col=from;col<=to;++col)wanted[page*0x2000+offset(y+row)+col]&=127;
            for (unsigned dx=0;dx<width;++dx) {
                unsigned px=x+dx,at=page*0x2000+offset(y+row)+px/7,bit=1<<(px%7);
                bool lit=dx<8*scale&&(font[(ch-32)*8+row/scale]&(1<<(dx/scale)));
                wanted[at]=(wanted[at]&~bit)|(lit?bit:0);
            }
        }
    }
    Result run(unsigned kind,bool small,unsigned value,unsigned field,unsigned x,unsigned y,unsigned width,unsigned page,bool irq) {
        // kind=0 init, 1 put, 2 invalidate; host page selection defines either
        // a cold row build or a warm fixed scanline table without invoking drawing.
        ++serial;
        unsigned page2=page==2;
        wr(a("_hgr_draw_page2"),page2);
        wr(a("_hgr_base"),page2?0x40:0x20);
        if (kind==0) {
            wr(ready,0);
            for (unsigned i=0;i<384;++i)wr(a("_hgr_rowlo")+i,0);
        }
        if (small||kind==0) {
        }
        else if (rd(ready))for (unsigned row=0;row<192;++row) {
            wr(a("_hgr_rowlo")+row,offset(row));
            wr(a("_hgr_rowhi")+row,(page*0x2000+offset(row))>>8);
        }
        unsigned stack=0xb000+((serial&2)?255:0),argbytes=kind==0?5:2;
        put(a("sp"),stack);
        if (kind==0) {
            wr(stack,y);
            wr(stack+1,x);
            wr(stack+2,x>>8);
            wr(stack+3,field);
            wr(stack+4,field>>8);
        }
        else{
            wr(stack,field);
            wr(stack+1,field>>8);
        }
        wr(0x1fe,0xff);
        wr(0x1ff,3);
        wr(0x1002,0);
        wr(0x1003,0);
        wr(0xc40e,0x7f);
        wr(0xc404,0);
        if (irq) {
            wr(0xc40b,0x40);
            unsigned first=36+(serial%32)*3;
            wr(0xc404,first);
            wr(0xc405,0);
            wr(0xc406,0xf3);
            wr(0xc407,1);
            wr(0xc40e,0xc0);
        }
        std::array<unsigned char,0xc000>before,aux,wanted,after;
        assert(core.readRam(RamBank::Main,0,before.data(),before.size()));
        assert(core.readRam(RamBank::Aux,0,aux.data(),aux.size()));
        wanted=before;
        unsigned expected=0,max=small?5:14;
        if (kind==0) {
            unsigned extent=small?8*width:18*(width-1)+16;
            bool good=field&&width&&width<=max&&y<=(small?184:176)&&x+extent<=280;
            if (good) {
                wanted[field]=x;
                wanted[field+1]=x>>8;
                wanted[field+2]=y;
                wanted[field+3]=width;
                wanted[field+4]=0;
                expected=1;
            }
        }
        if (kind==2&&field) {
            if (value==0)wanted[field+4]=0;
            else if (value<=2)wanted[field+4]&=value==1?2:1;
        }
        if (kind==1) {
            expected=255;
            if (field&&before[field+3]&&before[field+3]<=max) {
                unsigned w=before[field+3],origin=before[field]|(before[field+1]<<8),top=before[field+2];
                auto str=std::to_string(value);
                if (str.size()<=w) {
                    std::string digits(w-str.size(),' ');
                    digits+=str;
                    unsigned bit=1<<page2,vo=page2?7:5,chars=9+max*page2;
                    bool valid=before[field+4]&bit;
                    unsigned cached=before[field+vo]|(before[field+vo+1]<<8);
                    expected=0;
                    if (!valid||cached!=value) {
                        for (unsigned i=0;i<w;++i)if (!valid||before[field+chars+i]!=unsigned(digits[i])) {
                            draw(wanted,small,origin+i*(small?8:18),top,small?8:(i+1==w?16:18),digits[i],page);
                            wanted[field+chars+i]=digits[i];
                            ++expected;
                        }
                        wanted[field+vo]=value;
                        wanted[field+vo+1]=value>>8;
                        wanted[field+4]|=bit;
                    }
                }
            }
        }
        unsigned null_ptr3=word(a("ptr3"));
        unsigned entry=kind==0?a(small?"_hgr_hud8_init":"_hgr_hud_init"):kind==1?a(small?"_hgr_hud8_putu":"_hgr_hud_putu"):a("_hgr_hud_invalidate");
        auto s=core.cpuState();
        s.programCounter=entry;
        s.stackPointer=0xfd;
        s.accumulator=kind==0?width:value;
        s.x=kind==0?0x5a:value>>8;
        s.y=0x99;
        s.status=0x20|((serial&1)?4:0)|((serial&2)?1:0)|((serial&4)?0x40:0);
        s.halted=false;
        core.setCpuState(s);
        auto begin=s.cycles;
        unsigned original_p=s.status,steps=0,ptr3=a("ptr3");
        struct Frame {
            unsigned ret,sp,pointer,target;
            bool preserve;
        };
        std::vector<Frame>frames;
        std::vector<Event>stores;
        while (core.cpuState().programCounter!=0x400&&++steps<100000) {
            auto pre=core.cpuState();
            unsigned pc=pre.programCounter,op=rd(pc),target=probe::storeTarget(core);
            bool store=target>=0x2000&&target<0x6000||field&&target>=field&&target<field+9+2*max;
            unsigned called=op==0x20?word(pc+1):0,held=word(ptr3);
            core.step();
            auto post=core.cpuState();
            if (post.programCounter==0x901&&(pc<0x900||pc>=0x900+handler.size())) {
                assert(rd(0x900)==0x48&&word(0xfffe)==0x900);
                assert(!(pre.status&4)&&(post.status&4));
                unsigned sp=pre.stackPointer;
                assert(rd(0x100|((sp-3)&255))==pre.accumulator);
                assert((rd(0x100|((sp-1)&255))|(rd(0x100|sp)<<8))==pc);
                assert(post.stackPointer==((sp-4)&255));
                ++deferrals;
                if(kind==1 && small && field && L.count(".hud8_audit_low_live") && pc>=a("hud8_audit_low_live") && pc<a("hud8_audit_low_done")) {
                    ++entry_irqs;
                    ++entry_fields[field];
                    if(HGRC_TEST_BAD_LOW) {
                        unsigned changed=0;
                        for(unsigned p=0;p+2<handler.size();++p)if(handler[p]==0x68&&handler[p+1]==0x85&&handler[p+2]==a("tmp1")){wr(0x901+p,0xea);wr(0x902+p,0xea);++changed;}
                        assert(changed==1);
                        fprintf(stderr,"ENTRY TMP1 IRQ fault injected at actual IRQ entry %u\n",entry_irqs);
                    }
                }
                continue;
            }
            if (called&&(preserves.count(called)||called==a("_hgr_hud_cell_run"))) {
                assert(post.programCounter==called);
                frames.push_back({pc+3,pre.stackPointer,held,called,preserves.count(called)!=0});
            }
            if (!frames.empty()&&post.programCounter==frames.back().ret&&post.stackPointer==frames.back().sp) {
                auto f=frames.back();
                frames.pop_back();
                if (f.preserve) {
                    if (word(ptr3)!=f.pointer)fprintf(stderr,"HELPER ptr3 REJECT actual_irqs=%u\n",word(0x1002));
                    assert(word(ptr3)==f.pointer);
                    ++preserves[f.target];
                }
                else{
                    assert(word(ptr3)!=f.pointer);
                    ++large_borrows;
                }
            }
            if (store)stores.emplace_back(target,rd(target));
            assert(post.stackPointer>=0xe0);
            assert(!(rd(0xc013)&128)&&!(rd(0xc014)&128));
        }
        s=core.cpuState();
        if(kind==1&&!field)assert(word(a("ptr3"))==null_ptr3);
        assert(steps<100000&&frames.empty()&&s.stackPointer==255);
        assert((s.status&12)==(original_p&12));
        assert(word(a("sp"))==stack+argbytes);
        if (kind!=2)assert(s.accumulator==expected&&s.x==0);
        if (kind==1&&field)assert(word(ptr3)==field);
        assert(core.readRam(RamBank::Main,0,after.data(),after.size()));
        std::array<bool,256>scratch{
        };
        for (const char*n:{"ptr1","ptr2","ptr3","ptr4","sp","_hgr_g_glyph","_hgr_t_font","_hgr_u_ptr"})scratch[a(n)]=scratch[a(n)+1]=true;
        for (const char*n:{"tmp1","tmp2","tmp3","tmp4","_hgr_g_col","_hgr_g_bit","_hgr_g_y","_hgr_u_lo","_hgr_u_hi"})scratch[a(n)]=true;
        for (unsigned p=0;p<after.size();++p) {
            if (p<256&&scratch[p]||p>=bss&&p<bss+bss_size||p>=0x1e0&&p<=0x1ff||p>=0x1002&&p<=0x1003)continue;
            assert(after[p]==wanted[p]);
        }
        assert(core.readRam(RamBank::Aux,0,after.data(),after.size()));
        assert(after==aux);
        for (unsigned p:{0xc013,0xc014,0xc016,0xc018,0xc01c})assert(!(rd(p)&128));
        unsigned count=word(0x1002);
        if (!irq||original_p&4)assert(count==0);
        irqs+=count;
        wr(0xc40e,0x7f);
        wr(0xc404,0);
        std::vector<unsigned char>state(bss_size);
        assert(core.readRam(RamBank::Main,bss,state.data(),state.size()));
        for (auto event:stores) {
            if(field&&event.first>=field&&event.first<field+9+2*max)++cache_writes;
            else ++pixel_writes;
        }
        if (audit_field)state.erase(state.begin()+audit_field-bss,state.begin()+audit_field-bss+2);
        ++calls;
        cycles+=s.cycles-begin;
        return{
            s.accumulator,s.x,s.y,s.status,s.cycles-begin,stores,state
        };
    }
};
int main(int argc,char**argv) {
    assert(argc==9);
    unsigned base=std::stoul(argv[6]);
    bool cmos=std::stoi(argv[7]),irq=std::stoi(argv[8]);
    Instance old(argv[1],argv[2],argv[5],base,cmos),now(argv[3],argv[4],argv[5],base,cmos);
    assert(old.bss_size-(old.audit_field?2:0)==now.bss_size-(now.audit_field?2:0));
    unsigned fast=0,equal=0,slow=0,slow_small=0,slow_large=0;
    long largest=0;
    double largest_relative=0;
    auto call=[&](unsigned kind,bool small,unsigned value,unsigned field,unsigned x,unsigned y,unsigned width,unsigned page) {
        unsigned old_width=field?old.rd(field+3):0,old_x=field?old.word(field):0,old_y=field?old.rd(field+2):0,old_valid=field?old.rd(field+4):0;
        auto b=old.run(kind,small,value,field,x,y,width,page,irq),a=now.run(kind,small,value,field,x,y,width,page,irq);
        if(!(a.a==b.a&&a.x==b.x&&a.y==b.y&&(((a.p^b.p)&(irq?0xef:0xff))==0)&&a.stores==b.stores&&a.bss==b.bss)){fprintf(stderr,"COMPARE kind=%u small=%u value=%u field=%04X serial=%u A/X/Y/P %u/%u/%u/%u -> %u/%u/%u/%u stores=%zu/%zu BSS=%zu/%zu\n",kind,small,value,field,old.serial,b.a,b.x,b.y,b.p,a.a,a.x,a.y,a.p,b.stores.size(),a.stores.size(),b.bss.size(),a.bss.size());for(unsigned i=0;i<std::min(a.bss.size(),b.bss.size());++i)if(a.bss[i]!=b.bss[i]){fprintf(stderr,"BSSdiff offset=%u before=%u after=%u\n",i,b.bss[i],a.bss[i]);break;}for(unsigned i=0;i<std::min(a.stores.size(),b.stores.size());++i)if(a.stores[i]!=b.stores[i]){fprintf(stderr,"STOREdiff i=%u before=%04X/%u after=%04X/%u\n",i,b.stores[i].first,b.stores[i].second,a.stores[i].first,a.stores[i].second);break;}}
// B is a pushed PHP/IRQ marker, not a CPU latch. The SDK shadow may
        // differ when faster NULL returns avoid an IRQ. Check every other
        // status bit under live IRQs, and the entire P byte without IRQs.
        assert(a.a==b.a&&a.x==b.x&&a.y==b.y&&(((a.p^b.p)&(irq?0xef:0xff))==0)&&a.stores==b.stores&&a.bss==b.bss);
        if (kind==1) {
            long d=long(a.cycles)-long(b.cycles);
            fast+=d<0;
            equal+=d==0;
            slow+=d>0;
            double relative=100.0*d/b.cycles;
            if (d>0) {
                small?++slow_small:++slow_large;
            }
            if (d>largest||relative>largest_relative) {
                printf("WORST small=%u value=%u field=%04X width=%u x=%u y=%u page=%u valid_before=%u changed=%u cycles=%llu->%llu delta=%ld relative=%.5f%%\n",small,value,field,old_width,old_x,old_y,page,old_valid,a.a,b.cycles,a.cycles,d,relative);
            }
            largest=std::max(largest,d);
            largest_relative=std::max(largest_relative,relative);
        }
    };
    for (unsigned field:{0x1200u,0xA0u,0x2110u,0xB1F8u})for (bool small:{false,true})for (unsigned width=1;width<=(small?5u:14u);++width)for (unsigned phase=0;phase<7;++phase)for (unsigned top:{0u,small?184u:176u}) {
        unsigned extent=small?8*width:18*(width-1)+16,maxx=280-extent,x=phase+7*((maxx-phase)/14);
        if (phase>maxx)continue;
        call(0,small,0,field,x,top,width,1);
        unsigned n=0;
        for (unsigned value:{0,0,1,2,9,10,12,99,100,999,1000,65534,65535,0,54321,54322,54324}) {
            unsigned page=(n++%4)<2?1:2;
            call(1,small,value,field,0,0,0,page);
            if (n==9)call(2,small,0,field,0,0,0,page);
        }
        if(small&&width==5&&phase==0&&top==0) {
            for(unsigned invalid=0;invalid<256;++invalid)if(invalid==0||invalid>5) {
                old.wr(field+3,invalid);now.wr(field+3,invalid);
                call(1,small,0,field,0,0,0,1);
                old.wr(field+3,5);now.wr(field+3,5);
            }
        }
        call(1,small,1,0,0,0,0,1);
    }
    if(irq&&now.L.count(".hud8_audit_low_live")){assert(now.entry_irqs>100&&now.entry_fields.size()==4);for(auto [where,count]:now.entry_fields){assert(count>0);printf("ENTRY field=$%04X IRQs=%u\n",where,count);}}printf("ENTRY live-low IRQs=%u\n",now.entry_irqs);printf("SLOW small=%u large=%u maximum_relative=%.5f%%\n",slow_small,slow_large,largest_relative);
    assert(old.large_borrows&&now.large_borrows&&old.large_borrows==now.large_borrows);
    for (auto [target,count]:now.preserves) {
        assert(count>100);
        printf("preserved helper $%04X: %u returns\n",target,count);
    }
    assert(old.pixel_writes==now.pixel_writes&&old.cache_writes==now.cache_writes);
    printf("ORDERED source stores: pixels=%u cache=%u; IRQ deferrals=%u/%u\n",now.pixel_writes,now.cache_writes,old.deferrals,now.deferrals);
    if (irq)assert(old.irqs>100&&now.irqs>100);
    printf("CPU=%u IRQ=%u base=%04X calls/source=%u cycles=%llu->%llu faster/equal/slower=%u/%u/%u maxdelta=%ld; large ptr3 borrows=%u; IRQs=%u/%u; exact pixels/cache/ordered-stores/BSS/AXYP/stack/C-stack/code/main/aux PASS\n",cmos,irq,base,now.calls,old.cycles,now.cycles,fast,equal,slow,largest,now.large_borrows,old.irqs,now.irqs);
}
