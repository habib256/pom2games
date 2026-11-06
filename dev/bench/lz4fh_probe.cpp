// GPL-3.0. Independent LZ4FH streams and forward-overlap output model.
// Covers every match length, source/output page crossings, both destination
// pages, literal boundaries, full 8K output, code/RAM/stack guards and AXYP.
// Optional four asset paths replace synthetic inputs with two packed/raw pairs.
#include "probe.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <iterator>
#include <vector>
using namespace pom2;
using Bytes=std::vector<unsigned char>;
struct Input { Bytes packed{0x66}, output; unsigned matches=0; };
static void literal(Input& v, unsigned count, bool end=false) {
    assert(count>0 && count<=255);
    v.packed.push_back((std::min(count,15u)<<4)|15);
    if(count>=15) v.packed.push_back(count-15);
    for(unsigned i=0;i<count;++i) {
        unsigned b=(v.output.size()*37+count*11+(i>>3))&255;
        v.packed.push_back(b);v.output.push_back(b);
    }
    v.packed.push_back(end?254:253);
}
static void match(Input& v,unsigned count,unsigned offset) {
    assert(count>=4 && count<=255 && offset<v.output.size());
    v.packed.push_back(std::min(count-4,15u));
    if(count>=19) v.packed.push_back(count-19);
    v.packed.push_back(offset&255);v.packed.push_back(offset>>8);
    for(unsigned i=0;i<count;++i) v.output.push_back(v.output[offset+i]);
    ++v.matches;
}
struct Result { unsigned a,x,y,p; unsigned long long cycles; };
struct Instance {
    Core core;std::map<std::string,unsigned> labels;Bytes image;
    unsigned base, calls=0;unsigned long long cycles=0;
    unsigned at(const char* n){return labels.at(std::string(".")+n);}
    Instance(const char* binary,const char* symbols,bool cmos,unsigned where):
        core(CoreConfig{cmos?CpuModel::CMOS65C02:CpuModel::NMOS6502,VideoTiming::NTSC,true}),base(where) {
        probe::labels(labels,symbols);std::ifstream f(binary,std::ios::binary);
        image.assign(std::istreambuf_iterator<char>(f),{});assert(!image.empty());
    }
    Result run(const Input& in,unsigned destination,unsigned phase,unsigned serial) {
        std::array<unsigned char,0xc000> before,after,wanted;
        for(unsigned i=0;i<before.size();++i) before[i]=(i*13+(i>>8)*31+serial*7)&255;
        assert(core.writeRam(RamBank::Main,0,before.data(),before.size()));
        assert(core.writeRam(RamBank::Main,base,image.data(),image.size()));
        unsigned source=0x9000+phase;
        assert(core.writeRam(RamBank::Main,source,in.packed.data(),in.packed.size()));
        core.write(at("lz4fh_src"),source);core.write(at("lz4fh_src")+1,source>>8);
        core.write(at("lz4fh_dst"),destination);core.write(at("lz4fh_dst")+1,destination>>8);
        core.write(0x1fe,0xff);core.write(0x1ff,3);
        assert(core.readRam(RamBank::Main,0,before.data(),before.size()));wanted=before;
        std::copy(in.output.begin(),in.output.end(),wanted.begin()+destination);
        wanted[at("_desthi")+1]=destination>>8;
        auto state=core.cpuState();state.programCounter=at("unpack");state.stackPointer=0xfd;
        state.accumulator=serial&255;state.x=53;state.y=211;state.status=0x20|((serial&1)?4:0);
        state.halted=false;core.setCpuState(state);auto start=state.cycles;
        unsigned steps=0;
        while(core.cpuState().programCounter!=0x400 && ++steps<300000) core.step();
        state=core.cpuState();assert(steps<300000);assert(state.stackPointer==255);
        assert((state.status&12)==((serial&1)?4:0));
        assert(core.readRam(RamBank::Main,0,after.data(),after.size()));
        for(unsigned i=0;i<after.size();++i) {
            bool scratch=i>=at("lz4fh_read")&&i<at("lz4fh_length")+1;
            if(!scratch && i!=0x1fe && i!=0x1ff) assert(after[i]==wanted[i]);
        }
        unsigned write=core.read(at("lz4fh_write"))|(core.read(at("lz4fh_write")+1)<<8);
        assert(write==destination+in.output.size());
        ++calls;cycles+=state.cycles-start;
        return {state.accumulator,state.x,state.y,state.status,state.cycles-start};
    }
};
int main(int argc,char** argv) {
    assert(argc==7 || argc==11);bool cmos=std::stoi(argv[5]);unsigned base=std::stoul(argv[6]);
    Instance old(argv[1],argv[2],cmos,base),now(argv[3],argv[4],cmos,base);
    std::vector<Input> inputs;
    for(unsigned count=4;count<=255;++count) for(unsigned mode=0;mode<6;++mode) {
        Input in;unsigned prefix=mode<3?1+mode*7:255;
        literal(in,prefix);
        if(mode==5) literal(in,17);
        unsigned offset=mode%3==0?0:mode%3==1?in.output.size()-1:in.output.size()-3;
        match(in,count,offset);in.packed.insert(in.packed.end(),{15,254});inputs.push_back(in);
    }
    for(unsigned count:{1u,14u,15u,16u,254u,255u}) {Input in;literal(in,count,true);inputs.push_back(in);}
    Input full;literal(full,32);while(full.output.size()+255<=8192)match(full,255,full.output.size()-1);
    unsigned remain=8192-full.output.size();if(remain)literal(full,remain,true);else full.packed.insert(full.packed.end(),{15,254});inputs.push_back(full);
    if(argc==11) {
        inputs.clear();
        for(unsigned i=7;i<11;i+=2) {
            Input in;std::ifstream packed(argv[i],std::ios::binary),raw(argv[i+1],std::ios::binary);
            in.packed.assign(std::istreambuf_iterator<char>(packed),{});
            in.output.assign(std::istreambuf_iterator<char>(raw),{});
            assert(!in.packed.empty() && in.output.size()==8192);inputs.push_back(in);
        }
    }
    unsigned faster=0,equal=0,slower=0,serial=0;long low=0,high=0;
    for(const auto& in:inputs)for(unsigned page:{0x2000u,0x4000u})for(unsigned phase:{0u,253u,255u}) {
        auto a=old.run(in,page,phase,serial);auto b=now.run(in,page,phase,serial++);
        assert(a.a==b.a&&a.x==b.x&&a.y==b.y&&a.p==b.p);
        long d=long(b.cycles)-long(a.cycles);faster+=d<0;equal+=d==0;slower+=d>0;
        low=std::min(low,d);high=std::max(high,d);
    }
    std::printf("CPU=%u base=%04x calls=%u cycles=%llu->%llu faster=%u equal=%u slower=%u delta=%ld..%ld; output/wholeRAM/code/AXYP/I/D/SP PASS\n",cmos,base,serial,old.cycles,now.cycles,faster,equal,slower,low,high);
}
