#include "probe.hpp"
#include <vector>
#include <iterator>
#include <cstdio>
#include <algorithm>
int main(int argc,char**argv){
 probe::require(argc==4,"binary labels rom");std::map<std::string,unsigned>L;probe::labels(L,argv[2]);
 std::ifstream f(argv[1],std::ios::binary);std::vector<uint8_t>image((std::istreambuf_iterator<char>(f)),{});
 pom2::CoreConfig cfg;cfg.machine=pom2::Machine::AppleIIeEnhanced;pom2::Core c(cfg);probe::require(c.loadRom(argv[3]),"ROM");probe::require(c.attachMockingboard(4),"card");
 probe::require(c.writeRam(pom2::RamBank::Main,0x6000,image.data(),image.size()),"image");
 auto put=[&](const char*name,unsigned v){uint8_t b=v;probe::require(c.writeRam(pom2::RamBank::Main,L.at(std::string(".")+name),&b,1),"state");};
 uint64_t minimum=9999,maximum=0;unsigned count=0;
 for(unsigned word=0;word<65536;++word){
  unsigned active=word&1,irq=(word>>1)&1;
  c.write(0xC40E,0x7F);c.write(0xC40B,0x20);c.write(0xC404,0xFF);c.write(0xC405,0xFF);
  put("mb_slot",4);put("mb_timer_active",active);put("mb_old_acr",0x25);put("mb_old_ier",0x93);
  const uint8_t back[]={0xFF,0x4F};probe::require(c.writeRam(pom2::RamBank::Main,0x1FE,back,2),"return frame");
  auto s=c.cpuState();s.programCounter=L.at(".mb_timer_start");s.stackPointer=0xFD;s.accumulator=word;s.x=word>>8;s.y=0x5A;s.status=0x20|(irq?4:0)|((word&4)?1:0)|((word&8)?0x40:0);unsigned original_p=s.status;c.setCpuState(s);auto begin=s.cycles;unsigned steps=0,lowest=0xFD;
  while(c.cpuState().programCounter!=0x5000&&steps++<100){c.step();lowest=std::min<unsigned>(lowest,c.cpuState().stackPointer);}
  s=c.cpuState();probe::require(steps<100&&s.stackPointer==0xFF&&lowest==0xFA,"return/stack");
  probe::require(s.accumulator==1&&s.x==(word>>8)&&s.y==5&&(s.status&0xCF)==(original_p&0xCF),"A/X/Y/P");
  probe::require(c.read(0xC406)==(word&255)&&c.read(0xC407)==(word>>8),"exact 16-bit timer latch");
  probe::require(c.read(0xC40B)==(active?0x65:0x60)&&c.read(0xC40E)==0x80,"ACR/IER");
  probe::require(c.read(L.at(".mb_old_acr"))==(active?0x25:0x20)&&c.read(L.at(".mb_old_ier"))==(active?0x93:0x80),"snapshot");
  auto elapsed=s.cycles-begin;minimum=std::min<uint64_t>(minimum,elapsed);maximum=std::max<uint64_t>(maximum,elapsed);++count;
 }
 std::printf("%u native65C02 reloads, real VIA latch/ACR/IER, registers/I/D/stack/snapshot PASS; cycles %llu..%llu\n",count,(unsigned long long)minimum,(unsigned long long)maximum);
}
