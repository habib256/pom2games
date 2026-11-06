/* GPL-3.0. AYS active-volume control flow, compared on both SDK CPU models.
 * Each case runs a complete tick with arbitrary retained on/off flag bits,
 * instrument bytes, volume offsets, effects, caches and chip/mute selections.
 * The reference retains the former defensive LDA/BPL at @vmute. Every arrival
 * there must already have bit 7 set; volume and mixer outputs also have an
 * independent oracle. All state, flags, stacks and permitted stores are checked.
 * No IRQ is pending here; real IRQ bus ordering is covered by test_mb_irq.py.
 */
#include "probe.hpp"
#include <array>
#include <cassert>
#include <cstdio>
#include <vector>
#include <bitset>
using namespace pom2;
struct Result {std::vector<unsigned char> b;std::array<unsigned char,5> z;unsigned a,x,y,p,sp,peak,cycles;};
struct VM {
 Core core;std::map<std::string,unsigned>L;unsigned voices,fast;std::array<unsigned char,0xc000> original,aux;std::bitset<65536>allowed;unsigned visits=0,envelope=0,low=0,high=0,normal=0,started=0,retained=0;
 unsigned at(const char*n){if(std::string(n)=="ays_ib")return L.at(".ays_zp")+3;return L.at(std::string(".")+n);}unsigned rd(unsigned p){return core.read(p);}void wr(unsigned p,unsigned v){core.write(p,(unsigned char)v);}void put(const char*n,unsigned v){wr(at(n),v);}
 VM(const char*b,const char*l,bool c02,unsigned v,unsigned f):core(CoreConfig{c02?CpuModel::CMOS65C02:CpuModel::NMOS6502,VideoTiming::NTSC,true}),voices(v),fast(f){
  original.fill(0xa5);aux.fill(0x69);assert(core.writeRam(RamBank::Main,0,original.data(),original.size()));assert(core.writeRam(RamBank::Aux,0,aux.data(),aux.size()));probe::labels(L,l);std::ifstream file(b,std::ios::binary);std::vector<unsigned char>bytes((std::istreambuf_iterator<char>(file)),{});assert(core.writeRam(RamBank::Main,0x6000,bytes.data(),bytes.size()));
  for(unsigned a=at("guard_before");a<=at("guard_after");++a)allowed.set(a);for(unsigned a=at("ays_zp");a<at("ays_zp")+5;++a)allowed.set(a);for(unsigned a=0x1fc;a<0x200;++a)allowed.set(a);assert(core.readRam(RamBank::Main,0,original.data(),original.size()));
 }
 Result call(unsigned id,unsigned von,unsigned ib,int off,unsigned fx,unsigned par,unsigned count,unsigned note,unsigned nv,unsigned flags){
  for(unsigned a=at("guard_before");a<=at("guard_after");++a)wr(a,(id*13+(a-at("guard_before"))*37)&255);
  for(unsigned i=0;i<5;++i)wr(at("ays_zp")+i,0x19+i*27);
  put("ays_play",0);put("ays_nv",nv);put("ays_mutem",(id&1)?63:0);
  const unsigned active=(id>>1)%nv;
  static const unsigned periods[]={3901,3682,3475,3280,3096,2922,2758,2603,2457,2319,2189,2066};unsigned oct=note/12,p=periods[note%12];if(oct)p=(p+(1u<<(oct-1)))>>oct;
  for(unsigned x=0;x<voices;++x){
   wr(at("ays_von")+x,x==active?von:0);wr(at("ays_vvoff")+x,x==active?unsigned(off)&255:0);wr(at("ays_vfx")+x,fx);wr(at("ays_vpar")+x,par);wr(at("ays_vcnt")+x,count);wr(at("ays_vnote")+x,note);wr(at("ays_vsll")+x,id&255);wr(at("ays_vslh")+x,(id>>8)&255);wr(at("ays_vibl")+x,0);wr(at("ays_vibh")+x,0x20);wr(at("ays_vipos")+x,4);
   if(!fast){wr(at("ays_vpn")+x,(id&2)?note:255);wr(at("ays_vpbl")+x,p&255);wr(at("ays_vpbh")+x,p>>8);}
  }
  wr(0x2000,6);wr(0x2001,4);wr(0x2002,(id&4)?255:9);wr(0x2003,0xab);wr(0x2004,ib);wr(0x2005,par);
  auto s=core.cpuState();s.accumulator=id&255;s.x=(id>>8)&255;s.y=(id*17)&255;s.status=0x20|flags;s.stackPointer=0xfd;s.programCounter=at("ays_tick");s.halted=false;core.setCpuState(s);wr(0x1fe,0xff);wr(0x1ff,3);const auto start=s.cycles;unsigned steps=0,minimum=0xfd;
  while(core.cpuState().programCounter!=0x400&&++steps<10000){
   s=core.cpuState();if(s.programCounter==at("@vmute")){assert(rd(at("ays_von")+s.x)&128);++visits;unsigned b=rd(at("ays_ib"));int o=(signed char)rd(at("ays_vvoff")+s.x),sum=int(b&15)+o;if(b&64)++envelope;else if(sum<0)++low;else if(sum>=16)++high;else ++normal;if(von&64)++started;else ++retained;}
   int target=probe::storeTarget(core);assert(target<0||allowed[target]);core.step();minimum=std::min(minimum,unsigned(core.cpuState().stackPointer));
  }
  s=core.cpuState();assert(steps<10000&&s.stackPointer==255);assert((s.status&12)==(flags&12));assert(rd(at("guard_before"))==((id*13)&255));assert(rd(at("guard_after"))==((id*13+(at("guard_after")-at("guard_before"))*37)&255));
  // The selected voice is the only possible active voice. Derive volume
  // and tone/noise gates independently of the assembly's lookup table.
  for(unsigned x=0;x<nv;++x){
   const bool on=x==active&&(von&128);
   const int sum=int(ib&15)+(signed char)rd(at("ays_vvoff")+x);
   unsigned volume=on?((ib&64)?16u:unsigned(std::max(0,std::min(15,sum)))):0;
   if(rd(at("ays_mutem"))&(1u<<x))volume=0;
   const unsigned mixer=on?((ib&16)?0:1)|((ib&32)?0:8):9;
   assert(rd(at("ays_regs")+(x/3)*16+8+x%3)==volume);
   assert(rd(at("ays_vmix")+x)==mixer);
  }
  Result r;r.a=s.accumulator;r.x=s.x;r.y=s.y;r.p=s.status;r.sp=s.stackPointer;r.peak=255-minimum;assert(r.peak<=4);r.cycles=s.cycles-start+6;for(unsigned a=at("guard_before");a<=at("guard_after");++a)r.b.push_back(rd(a));for(unsigned i=0;i<5;++i)r.z[i]=rd(at("ays_zp")+i);return r;
 }
 void guard(){std::array<unsigned char,0xc000>b;assert(core.readRam(RamBank::Main,0,b.data(),b.size()));for(unsigned a=0;a<b.size();++a)if(!allowed[a]&&(a<0x2000||a>0x2005))assert(b[a]==original[a]);assert(core.readRam(RamBank::Aux,0,b.data(),b.size()));assert(b==aux);for(auto a:{0xc013,0xc014,0xc016})assert(!(rd(a)&128));}
};
int main(int argc,char**argv){assert(argc==8);unsigned c02=std::stoi(argv[5]),v=std::stoi(argv[6]),fast=std::stoi(argv[7]);VM a(argv[1],argv[2],c02,v,fast),b(argv[3],argv[4],c02,v,fast);unsigned cases=0,slower=0,faster=0,equal=0;int lo=9999,hi=-9999;
 auto check=[&](unsigned von,unsigned ib,int off,unsigned fx,unsigned par,unsigned count,unsigned note){unsigned id=cases++,nv=v==6&&(id&8)?3:v,flags=((id&16)?4:0)|((id&32)?0xc1:0);auto x=a.call(id,von,ib,off,fx,par,count,note,nv,flags),y=b.call(id,von,ib,off,fx,par,count,note,nv,flags);assert(x.b==y.b&&x.z==y.z&&x.a==y.a&&x.x==y.x&&x.y==y.y&&x.p==y.p&&x.sp==y.sp&&x.peak==y.peak);int d=int(y.cycles)-int(x.cycles);lo=std::min(lo,d);hi=std::max(hi,d);if(d>0)++slower;else if(d<0)++faster;else ++equal;};
 for(unsigned von=0;von<256;++von)for(unsigned ib=0;ib<256;++ib)check(von,ib,int((von+ib)%31)-15,(von^ib)&7,(ib*17+von)&255,(von*37+ib)&255,(von+ib)%96);
 for(unsigned off=0;off<31;++off)for(unsigned ib=0;ib<256;++ib)for(unsigned von:{0u,128u,192u})check(von,ib,int(off)-15,0,0,0,(off+ib)%96);
 for(unsigned fx=0;fx<8;++fx)for(unsigned par=0;par<256;++par)for(unsigned count:{0u,1u,254u,255u})check((count&1)?128:192,(par*37)&255,int(par%31)-15,fx,par,count,(par+fx)%96);
 a.guard();b.guard();assert(a.visits==b.visits&&b.envelope&&b.low&&b.high&&b.normal&&b.started&&b.retained);std::printf("%s %uvoice fast%u: %u paired full ticks; %u @vmute arrivals all bit7 on, envelope/low/high/normal=%u/%u/%u/%u, new/retained=%u/%u; exact volume/mixer oracle, BSS/ZP/A/X/Y/P/I/D/stack peaks and store/main/aux/code/bank guards PASS; deltas %d..%d faster/equal/slower %u/%u/%u\n",c02?"65C02":"NMOS",v,fast,cases,b.visits,b.envelope,b.low,b.high,b.normal,b.started,b.retained,lo,hi,faster,equal,slower);
}
