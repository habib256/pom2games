/* GPL-3.0. HUD8 independent pixel/read/store oracle. Fixed unaligned row and
 * digit tables expose page crossings. All clipped columns/phases/digits/pages,
 * byte-Y wrap, low-pointer borrow, arbitrary source bytes, and framebuffer
 * aliases are checked on both CPUs, with live register-preserving IRQs.
 * Public geometry is validated separately by test_hgr_hud.py --compact.
 */
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <limits>
#include <vector>
using namespace pom2;
using Event = std::pair<unsigned, unsigned>;
struct Case {
    unsigned top,col,phase,base,digit,seed,kind,font,serial;
};
static unsigned off(unsigned y) {
    return ((y&7)<<10)+((y&56)<<4)+(y>>6)*40;
}
static unsigned rowoff(unsigned y) {
    return y<192?off(y):off(y-192)+1;
}
static unsigned data(const Case&c,unsigned i) {
    return c.kind==0?c.seed:((c.seed+i*37)&255)|1;
}
struct Instance {
    Core core;
    std::map<std::string,unsigned>L;
    std::vector<unsigned char>image;
    unsigned calls=0,reads=0,writes=0,irqs=0,deferred=0,alias_changes=0,borrow_rows=0;
    unsigned long long cycles=0;
    unsigned a(const char*n) {
        return L.at(std::string(".")+n);
    }
    unsigned rd(unsigned p) {
        return core.read(p);
    }
    void wr(unsigned p,unsigned v) {
        core.write(p,v);
    }
    Instance(const char*b,const char*l,const char*r,bool cmos):core(CoreConfig{cmos?CpuModel::CMOS65C02:CpuModel::NMOS6502,VideoTiming::NTSC,true}) {
        probe::labels(L,l);
        std::ifstream f(b,std::ios::binary);
        image.assign(std::istreambuf_iterator<char>(f),{});
        assert(!image.empty());
        assert(core.loadRom(r));
        assert(core.attachMockingboard());
    }
    void run(const Case&c,bool irq) {
        std::array<unsigned char,0xc000>before[2],actual[2],expected[2];
        for (unsigned bank=0;bank<2;++bank) {
            for (unsigned p=0;p<0xc000;++p)before[bank][p]=(p*29+(p>>8)*17+bank*83+c.serial*13)&255;
            assert(core.writeRam(bank?RamBank::Aux:RamBank::Main,0,before[bank].data(),before[bank].size()));
        }
        assert(core.writeRam(RamBank::Main,0x6000,image.data(),image.size()));
        unsigned base=c.base?c.base:0x20,index=c.phase*11+c.digit,source=c.font<256?0x8000+index*32+c.font:c.font;
        for (unsigned i=0;i<77;++i) {
            unsigned p=i==index?source:0x8000+i*32+(c.font&255);
            wr(a("hgr_hud8_digitlo")+i,p);
            wr(a("hgr_hud8_digithi")+i,p>>8);
        }
        for (unsigned i=0;i<16;++i)wr(source+i,data(c,i));
        wr(a("_hgr_base"),c.base);
        wr(a("_hgr_g_col"),c.col);
        wr(a("_hgr_g_bit"),c.phase);
        wr(a("_hgr_g_y"),c.top);
        wr(a("_hgr_g_glyph"),0xad);
        wr(a("_hgr_g_glyph")+1,0xde);
        for (unsigned y=0;y<256;++y) {
            wr(a("hgr_fixed_rowlo")+y,rowoff(y));
            wr(a("hgr_fixed_rowhi")+y,rowoff(y)>>8);
        }
        // Save registers, acknowledge VIA T1, then SEC before RTI. No ZP use.
        const unsigned char handler[]={
            0x48,0x8a,0x48,0x98,0x48,0xad,0x13,0xc0,0x0d,0x14,0xc0,0x29,0x80,0xf0,0x03,0xee,0x04,0x10,0xad,0x04,0xc4,0xee,0x02,0x10,0xd0,0x03,0xee,0x03,0x10,0x68,0xa8,0x68,0xaa,0x68,0x38,0x40
        };
        assert(core.writeRam(RamBank::Main,0x900,handler,sizeof(handler)));
        wr(0x1002,0);
        wr(0x1003,0);
        wr(0x1004,0);
        wr(0x1fe,0xff);
        wr(0x1ff,3);
        wr(0xc40e,0x7f);
        wr(0xc404,0);
        if (irq) {
            wr(0xc40b,0x40);
            wr(0xc404,0x63);
            wr(0xc405,0);
            wr(0xc40e,0xc0);
        }
        for (unsigned bank=0;bank<2;++bank) {
            assert(core.readRam(bank?RamBank::Aux:RamBank::Main,0,before[bank].data(),before[bank].size()));
            expected[bank]=before[bank];
        }
        expected[0][a("_hgr_g_glyph")]=source;
        expected[0][a("_hgr_g_glyph")+1]=source>>8;
        // Consume each font byte immediately before its store: aliases can
        // change the second byte of this row or a source on a later row.
        std::vector<Event>wanted_read,wanted_write,got_read,got_write;
        unsigned keep[2]={
            (1u<<c.phase)-1,127u^((1u<<(c.phase+1))-1)
        };
        for (unsigned row=0;row<8;++row) {
            unsigned y=(c.top+row)&255,at=(base<<8)+rowoff(y)+c.col;
            if ((rowoff(y)&255)+c.col<row*2)++borrow_rows;
            for (unsigned byte=0;byte<2;++byte) {
                unsigned pixel=expected[0][at+byte];
                wanted_read.emplace_back(at+byte,pixel);
                unsigned glyph=expected[0][source+row*2+byte];
                wanted_read.emplace_back(source+row*2+byte,glyph);
                if (c.font>=256&&glyph!=data(c,row*2+byte))++alias_changes;
                expected[0][at+byte]=(pixel&keep[byte])|glyph;
                wanted_write.emplace_back(at+byte,expected[0][at+byte]);
            }
        }
        auto st=core.cpuState();
        st.accumulator=c.digit?0x2f+c.digit:0x20;
        st.x=0x5a;
        st.y=0x99;
        st.status=0x20|((c.serial&1)?4:0);
        st.stackPointer=0xfd;
        st.programCounter=a("_hgr_hud8_cell_run");
        st.halted=false;
        core.setCpuState(st);
        auto begin=st.cycles;
        unsigned steps=0,ptr=a("ptr1"),glyph=a("_hgr_g_glyph");
        while (core.cpuState().programCounter!=0x400&&++steps<10000) {
            auto s=core.cpuState();
            unsigned op=rd(s.programCounter),operand=rd(s.programCounter+1),read_at=0,value=0;
            bool consumes=(op==0xb1&&operand==ptr)||(op==0x11&&operand==glyph);
            if (consumes) {
                read_at=(rd(operand)|(rd(operand+1)<<8))+s.y;
                value=rd(read_at);
            }
            auto target=probe::storeTarget(core);
            bool stores=op==0x91&&operand==ptr;
            assert(!(rd(0xc013)&128)&&!(rd(0xc014)&128));
            core.step();
            auto after=core.cpuState();
            // SDK step services an IRQ and executes the first PHA in one call.
            // Verify vector, handler range and the actual saved return frame;
            // an address match alone must never hide a renderer operation.
            if (after.programCounter==0x901&&(s.programCounter<0x900||s.programCounter>=0x900+sizeof(handler))) {
                assert(rd(0x900)==0x48);
                assert((rd(0xfffe)|(rd(0xffff)<<8))==0x900);
                assert(!(s.status&4)&&(after.status&4));
                unsigned sp=s.stackPointer;
                assert(rd(0x100|((sp-3)&255))==s.accumulator);
                assert((rd(0x100|((sp-1)&255))|(rd(0x100|sp)<<8))==s.programCounter);
                assert(after.stackPointer==((sp-4)&255));
                if (consumes||stores)++deferred;
                continue;
            }
            if (consumes)got_read.emplace_back(read_at,value);
            if (stores) {
                assert(bool(s.status&4)==bool(c.serial&1));
                got_write.emplace_back(target,s.accumulator);
            }
        }
        st=core.cpuState();
        assert(steps<10000&&st.stackPointer==255);
        assert((st.status&12)==((c.serial&1)?4:0));
        assert(got_read==wanted_read);
        if (got_write != wanted_write) {
            bool pixels_match = true;
            for (auto event : wanted_write) pixels_match &= rd(event.first) == expected[0][event.first];
            fprintf(stderr, "ORDER REJECT serial=%u live_irqs=%u pixels_match=%u\n", c.serial,
            rd(0x1002) | (rd(0x1003) << 8), unsigned(pixels_match));
        }
        assert(got_write==wanted_write);
        cycles+=st.cycles-begin;
        reads+=got_read.size();
        writes+=got_write.size();
        ++calls;
        wr(0xc40e,0x7f);
        wr(0xc404,0);
        irqs+=rd(0x1002)|(rd(0x1003)<<8);
        assert(rd(0x1004)==0);
        std::array<bool,256>scratch{
        };
        for (unsigned p:{ptr,ptr+1,a("tmp1"),a("tmp2"),a("tmp3"),a("tmp4")})scratch[p]=true;
        for (unsigned bank=0;bank<2;++bank) {
            assert(core.readRam(bank?RamBank::Aux:RamBank::Main,0,actual[bank].data(),actual[bank].size()));
            for (unsigned p=0;p<0xc000;++p) {
                if (!bank&&((p<256&&scratch[p])||(p>=0x1f8&&p<0x200)||(irq&&p>=0x1002&&p<=0x1004)))continue;
                assert(actual[bank][p]==expected[bank][p]);
            }
        }
        for (unsigned p:{0xc013,0xc014,0xc016,0xc018,0xc01c})assert(!(rd(p)&128));
    }
};
int main(int argc,char**argv) {
    assert(argc==8);
    bool cmos=std::stoi(argv[6]),irq=std::stoi(argv[7]);
    Instance old(argv[1],argv[2],argv[5],cmos),now(argv[3],argv[4],argv[5],cmos);
    std::vector<Case>cases;
    unsigned serial=0;
    auto add=[&](unsigned top,unsigned col,unsigned phase,unsigned base,unsigned digit,unsigned seed,unsigned kind,unsigned font) {
        cases.push_back({top,col,phase,base,digit,seed,kind,font,serial++});
    };
    // Every byte-Y, source byte, clipped column, phase, digit, and page.
    for (unsigned top=0;top<256;++top)for (unsigned phase=0;phase<7;++phase)for (unsigned base:{0,0x20,0x40})add(top,(top*7+phase)%39,phase,base,top%11,(top*37+phase*13)&255,1,(top*73+phase*17)&255);
    for (unsigned seed=0;seed<256;++seed)for (unsigned phase=0;phase<7;++phase)for (unsigned base:{0,0x20,0x40})add((seed*17+phase)&255,(seed*13+phase)%39,phase,base,(seed+phase)%11,seed,0,(seed*73+phase*17)&255);
    for (unsigned col=0;col<39;++col)for (unsigned phase=0;phase<7;++phase)for (unsigned base:{0,0x20,0x40})for (unsigned digit=0;digit<11;++digit)add(184,col,phase,base,digit,(col*37+digit*13+phase)&255,1,(col*19+phase)&255);
    // Font ranges overlap both pixel bytes and subsequent scanlines.
    for (unsigned base:{0,0x20,0x40})for (unsigned top:{0,7,63,184,255})for (unsigned col:{0,1,30,38})for (unsigned phase=0;phase<7;++phase)for (int shift:{-2,-1,0,1,2,4})add(top,col,phase,base,(top+phase)%11,(top*37+col*13+phase)&255,1,((base?base:0x20)<<8)+rowoff(top)+col+shift);
    unsigned fast=0,equal=0,slow=0;
    long lo=std::numeric_limits<long>::max(),hi=std::numeric_limits<long>::min();
    for (auto&c:cases) {
        auto b=old.cycles,a=now.cycles;
        old.run(c,irq);
        now.run(c,irq);
        long delta=long(now.cycles-a)-long(old.cycles-b);
        fast+=delta<0;
        equal+=delta==0;
        slow+=delta>0;
        lo=std::min(lo,delta);
        hi=std::max(hi,delta);
    }
    assert(old.reads==now.reads&&old.writes==now.writes&&old.alias_changes==now.alias_changes&&now.alias_changes>100);
    assert(old.borrow_rows==now.borrow_rows&&now.borrow_rows>100);
    if (irq)assert(old.irqs>100&&now.irqs>100);
    printf("%s IRQ=%u %u cells/source; %u ordered pixel/font reads, %u ordered writes; cycles %llu -> %llu; IRQs %u/%u; %u alias-modified font bytes, %u borrow rows; deferrals %u/%u; full guards PASS\n",cmos?"65C02":"NMOS",irq,now.calls,now.reads,now.writes,old.cycles,now.cycles,old.irqs,now.irqs,now.alias_changes,now.borrow_rows,old.deferred,now.deferred);
    printf("Per-cell cycles %u faster/%u equal/%u slower, range %ld..%ld\n",fast,equal,slow,lo,hi);
}
