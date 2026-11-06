#include "probe.hpp"
#include <array>
#include <bitset>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <vector>
using namespace pom2;
static const char* names[] = {"mul_x","mul_x","mul_y","mul_p0","mul_p1","mul_p2","mul_t","mul_s1l","mul_s1l","mul_s1h","mul_s1h","mul_s2l","mul_s2l","mul_s2h","mul_s2h","mul_acc0","mul_acc1","mul_acc2"};
struct Snapshot { std::array<unsigned char,18> m; unsigned a,x,y,p,cycles,peak; };
struct VM {
 Core core; std::map<std::string,unsigned> labels;
 std::array<unsigned,18> at;
 std::array<std::uint32_t,65536> masks{};
 std::array<std::bitset<65536>,8> allowed;
 std::bitset<65536> math;
 std::array<unsigned char,0xc000> original,auxiliary;
 unsigned address(const char* n) {return labels.at(std::string(".")+n);}
 unsigned read(unsigned a){return core.read((std::uint16_t)a);}
 void write(unsigned a,unsigned v){core.write((std::uint16_t)a,(unsigned char)v);}
 VM(const char* binary,const char* symbols,bool cmos):core(CoreConfig{cmos?CpuModel::CMOS65C02:CpuModel::NMOS6502,VideoTiming::NTSC,true}) {
  original.fill(0xa5);auxiliary.fill(0x69);
  assert(core.writeRam(RamBank::Main,0,original.data(),original.size()));assert(core.writeRam(RamBank::Aux,0,auxiliary.data(),auxiliary.size()));
  probe::labels(labels,symbols);std::ifstream f(binary,std::ios::binary);assert(f);std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(f)),{});assert(core.writeRam(RamBank::Main,0x6000,bytes.data(),bytes.size()));
  for(unsigned i=0;i<18;++i){at[i]=address(names[i])+((i==1||i==8||i==10||i==12||i==14)?1:0);math.set(at[i]);masks[at[i]]|=1u<<i;}
  for(unsigned mode=0;mode<8;++mode){
   auto add=[&](unsigned i){allowed[mode].set(at[i]);};
   if(mode<=3){add(3);add(4);if(mode!=0)add(5);for(auto i:{7u,9u,11u,13u})add(i);if(mode==3){add(0);add(1);add(2);}}
   if(mode==4)for(auto i:{7u,9u,11u,13u})add(i);
   if(mode==5){add(3);add(4);}
   if(mode==6){add(0);add(1);add(2);}
   if(mode==7){for(auto i:{3u,4u,6u,8u,10u,12u,14u})add(i);for(unsigned a=0x800;a<0x1000;++a)allowed[mode].set(a);}
  }
  for(unsigned a=0;a<65536;++a)if(math[a])write(a,(a*37+19)&255);
 }
 std::array<unsigned char,18> memory(){std::array<unsigned char,18>s;for(unsigned i=0;i<18;++i)s[i]=read(at[i]);return s;}
 void put(std::array<unsigned char,18>&s,unsigned i,unsigned v){auto mask=masks[at[i]];while(mask){unsigned bit=__builtin_ctz(mask);s[bit]=(unsigned char)v;mask&=mask-1;}}
 Snapshot raw(const char* fn,unsigned value,unsigned coefficient,unsigned mode,unsigned flags){
  auto s=core.cpuState();s.accumulator=(0xc3^value^coefficient)&255;s.x=(0x5a^(value>>8))&255;s.y=(value*37+coefficient*11)&255;
  if(mode==3){s.accumulator=value&255;s.x=value>>8;s.y=coefficient;}if(mode==6)s.accumulator=coefficient;
  s.status=0x20|flags;s.stackPointer=0xfd;s.programCounter=address(fn);s.halted=false;core.setCpuState(s);write(0x1fe,0xff);write(0x1ff,3);const auto start=s.cycles;unsigned steps=0,minimum=0xfd;
  while(core.cpuState().programCounter!=0x400 && ++steps<20000){int target=probe::storeTarget(core);assert(target<0||allowed[mode][target]);core.step();minimum=std::min(minimum,unsigned(core.cpuState().stackPointer));}
  s=core.cpuState();assert(steps<20000&&s.stackPointer==255);assert((s.status&12)==(flags&12));unsigned peak=255-minimum;assert(peak<=4);
  return {memory(),s.accumulator,s.x,s.y,s.status,unsigned(s.cycles-start+6),peak};
 }
 Snapshot initialize(unsigned flags){
  auto expected=memory();put(expected,3,0);put(expected,4,255);put(expected,6,0);put(expected,8,8);put(expected,10,10);put(expected,12,12);put(expected,14,14);
  auto r=raw("mul_init",0,0,7,flags);assert(r.m==expected);assert(r.a==14&&r.x==0&&r.y==255&&(r.p&0xcf)==(flags&4));assert(r.peak==2);
  for(unsigned n=0;n<512;++n){unsigned a=n*n/4,b=(n>255?n-255:255-n);b=b*b/4;assert(read(0x800+n)==(a&255)&&read(0xa00+n)==(a>>8)&&read(0xc00+n)==(b&255)&&read(0xe00+n)==(b>>8));}
  return r;
 }
 void baseline(){assert(core.readRam(RamBank::Main,0,original.data(),original.size()));}
 Snapshot trial(const char* fn,unsigned value,unsigned coefficient,unsigned mode,unsigned flags,bool numeric=true){
  if(mode<=2||mode==5||mode==6){write(at[0],value&255);write(at[1],value>>8);}if(mode<=2||mode==4)write(at[2],coefficient);
  auto expected=memory();if(mode==5){assert(expected[2]==coefficient&&expected[7]==coefficient&&expected[9]==coefficient&&expected[11]==(coefficient^255)&&expected[13]==(coefficient^255));flags|=1;}
  const auto r=raw(fn,value,coefficient,mode,flags);
  if(mode==5)assert(r.p&1);
  if(mode==4 || (mode<=3 && !(mode==3&&(coefficient==0||coefficient==64||coefficient==192)))){put(expected,7,coefficient);put(expected,9,coefficient);put(expected,11,coefficient^255);put(expected,13,coefficient^255);}
  if(mode==3&&coefficient!=0&&coefficient!=64&&coefficient!=192){put(expected,0,value&255);put(expected,1,value>>8);put(expected,2,coefficient);}
  if(mode<=3||mode==5){long long p=(mode==2||mode==3)?(long long)(std::int16_t)value*(std::int8_t)coefficient:(long long)(mode==0||mode==5?value&255:value)*coefficient;
   unsigned bits=(unsigned)p&0xffffff;for(unsigned i=0;i<(mode==0||mode==5?2u:3u);++i)put(expected,3+i,numeric?bits>>(8*i):r.m[3+i]);}
  if(mode==6){unsigned q=coefficient?value/coefficient:65535,rem=coefficient?value%coefficient:value&255;put(expected,0,q&255);put(expected,1,q>>8);put(expected,2,coefficient);assert(r.a==rem);assert(r.y==((value*37+coefficient*11)&255));}
  assert(r.m==expected);return r;
 }
 void guards(){std::array<unsigned char,0xc000>s;assert(core.readRam(RamBank::Main,0,s.data(),s.size()));for(unsigned a=0;a<s.size();++a)if(!math[a]&&(a<0x1fc||a>0x1ff))assert(s[a]==original[a]);assert(core.readRam(RamBank::Aux,0,s.data(),s.size()));assert(s==auxiliary);for(auto a:{0xc013,0xc014,0xc016})assert(!(read(a)&128));}
};
static void same(const Snapshot&a,const Snapshot&b){assert(a.m==b.m&&a.a==b.a&&a.x==b.x&&a.y==b.y&&a.p==b.p&&a.peak==b.peak);}
int main(int argc,char**argv){
 assert(argc==8);bool cmos=std::stoi(argv[5]);unsigned kind=std::stoi(argv[6]);bool exhaustive=std::stoi(argv[7]);VM before(argv[1],argv[2],cmos),after(argv[3],argv[4],cmos);
 same(before.initialize(4),after.initialize(4));before.baseline();after.baseline();unsigned long long cases=0;unsigned faster=0,equal=0,slower=0;long lo=9999,hi=-9999;
 auto pair=[&](const char*fn,unsigned x,unsigned y,unsigned mode,unsigned flags,bool numeric=true){auto a=before.trial(fn,x,y,mode,flags,numeric),b=after.trial(fn,x,y,mode,flags,numeric);same(a,b);long d=(long)b.cycles-a.cycles;lo=std::min(lo,d);hi=std::max(hi,d);if(d<0)++faster;else if(d>0)++slower;else ++equal;++cases;};
 const std::array<unsigned,9> factors={0,1,64,127,128,129,192,254,255};
 auto flags=[](unsigned x,unsigned y){return ((x^y)&1?4u:0u)|((x+y)&2?0xc1u:0u);};
 if(kind==0){for(unsigned y=0;y<256;++y)for(unsigned x=0;x<256;++x)pair("entry",x|(((x*37+y)&255)<<8),y,0,flags(x,y));}
 else if(exhaustive){for(auto y:factors)for(unsigned x=0;x<65536;++x)pair("entry",x,y,kind==1?1:2,flags(x,y));}
 for(unsigned y=0;y<256;++y)for(auto high:{0u,1u,127u,128u,255u})for(unsigned x=0;x<256;x+=exhaustive?1:17)pair("entry",x|(high<<8),y,kind==0?0:kind==1?1:2,flags(x,y));
 if(kind>=2){for(auto y:factors)for(unsigned x=0;x<65536;x+=exhaustive?1:257)pair("mul_dir",x,y,3,flags(x,y));}
 // Caller prepares the pointer lows once, then reuses them without writing Y.
 for(unsigned y=0;y<256;++y){pair("set_y",0,y,4,flags(y,0));for(unsigned x=0;x<256;++x)pair("cached",x|(y<<8),y,5,flags(x,y)|1);}
 // Division changes Y's operand; subsequent normal/cached preparation must work.
 for(unsigned y=0;y<256;++y)for(auto x:{0u,1u,255u,256u,257u,32767u,32768u,65535u}){pair("div16by8",x,y,6,flags(x,y));pair("set_y",0,y,4,4);pair("cached",x,y,5,5);}
 for(auto y:{0u,64u,255u}){pair("set_y",0,y,4,4);same(before.initialize(0),after.initialize(0));pair("cached",0xa55a,y,5,1);}
 // D=1 is outside the arithmetic contract; still preserve its old behavior.
 for(unsigned y=0;y<256;++y)for(auto x:{0u,1u,255u,32767u,32768u,65535u})pair("entry",x,y,kind==0?0:kind==1?1:2,8|flags(x,y),false);
 before.guards();after.guards();std::printf("%s kind%u: %llu calls (%u faster/%u equal/%u slower), deltas%ld..%ld; products/cache/init/reinit/divisor transitions,A/X/Y/P,I/D,stack,all math/main/aux/code/tables/banks/stores PASS\n",cmos?"65C02":"NMOS",kind,cases,faster,equal,slower,lo,hi);
}
