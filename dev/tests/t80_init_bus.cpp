// Execute the actual init entry against the SDK's traceable 65C02 bus.
#include <pom2/core.hpp>
#include <array>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <vector>
struct Access { unsigned address; bool write; };
struct Scenario { unsigned x,y,mode,sw,px,py,on,save; bool store,page,text,mixed,hires,an3; };
static unsigned flip(unsigned v) {
 return v<32?v+192:v<64?v+128:v<96?171:v<128?v+128:v<192?v-128:v<224?v-192:v-128;
}
int main(int argc,char **argv) {
 assert(argc==12);
 std::ifstream file(argv[1],std::ios::binary);
 std::vector<unsigned char> image((std::istreambuf_iterator<char>(file)),{});
 const auto number=[&](unsigned i){return std::stoul(argv[i],nullptr,16);};
 const unsigned load=number(2),entry=number(3),x=number(4),y=number(5),mode=number(6);
 const unsigned sw=number(7),px=number(8),py=number(9),on=number(10);
 const std::array<Scenario,3> scenarios={{{0,0,255,39,0,0,0,109,false,false,true,false,false,false},
    {17,23,2,25,37,11,1,47,true,false,false,true,true,true},
    {79,0,1,19,0,23,1,225,true,true,true,true,false,false}}};
 std::array<bool,1024> visible{};
 for(unsigned row=0;row<24;++row)for(unsigned col=0;col<40;++col)visible[(row%8)*128+(row/8)*40+col]=true;
 for(unsigned flags=0;flags<16;++flags)for(unsigned scenario=0;scenario<scenarios.size();++scenario) {
  pom2::CoreConfig config;config.machine=pom2::Machine::AppleIIeEnhanced;
  pom2::Core core(config);assert(core.loadRom(argv[11]));
  std::array<unsigned char,0xC000> main,aux;main.fill(0xA5);aux.fill(0xA5);
  main[0x56]=0xFE;main[0x57]=0xBF; // software stack pointer, guarded $B800-$BFFF
  assert(core.writeRam(pom2::RamBank::Main,0,main.data(),main.size()));
  assert(core.writeRam(pom2::RamBank::Aux,0,aux.data(),aux.size()));
  assert(core.writeRam(pom2::RamBank::Main,load,image.data(),image.size()));
  const auto put=[&](unsigned address,unsigned value){const auto b=static_cast<unsigned char>(value);assert(core.writeRam(pom2::RamBank::Main,address,&b,1));};
  const Scenario spec=scenarios[scenario];
  for(unsigned repeat=0;repeat<2;++repeat) {
   core.clearWatchedAddresses();core.setBusWatch({});
   core.write(spec.store?0xC001:0xC000,0);core.write(0xC002,0);core.write(0xC004,0);core.write(0xC008,0);
   core.write(repeat?0xC00D:0xC00C,0);core.write(repeat?0xC00F:0xC00E,0);
   core.read(spec.text?0xC051:0xC050);core.read(spec.mixed?0xC053:0xC052);
   core.read((spec.page^bool(repeat))?0xC055:0xC054);core.read(spec.hires?0xC057:0xC056);core.read(spec.an3?0xC05F:0xC05E);
   put(x,spec.x);put(y,spec.y);put(mode,spec.mode);put(sw,spec.sw);
   if(on){put(px,spec.px);put(py,spec.py);put(on,spec.on);put(on+1,spec.save);}
   if(on&&spec.on){
    const unsigned address=0x400+(spec.py%8)*128+(spec.py/8)*40+spec.px/2;
    const auto bank=(spec.px&1)?pom2::RamBank::Main:pom2::RamBank::Aux;
    const unsigned char value=flip(spec.save);assert(core.writeRam(bank,address,&value,1));
   }
   const unsigned char dirty=0x41;assert(core.writeRam(pom2::RamBank::Main,0x7F7,&dirty,1));
   const unsigned char back[]={0xFF,0x4F};assert(core.writeRam(pom2::RamBank::Main,0x1FE,back,2));
   assert(core.readRam(pom2::RamBank::Main,0,main.data(),main.size()));assert(core.readRam(pom2::RamBank::Aux,0,aux.data(),aux.size()));
   auto expected_main=main,expected_aux=aux;
   for(unsigned i=0;i<1024;++i)if(visible[i])expected_main[0x400+i]=expected_aux[0x400+i]=0xA0;
   expected_main[mode]=0;if(on)expected_main[on]=0;
   pom2::CpuState state;state.programCounter=entry;state.stackPointer=0xFD;state.accumulator=flags*17;state.x=0x5A;state.y=0xA5;
   state.status=0x20|(flags&1)|((flags&2)?4:0)|((flags&4)?64:0)|((flags&8)?8:0);core.setCpuState(state);
   std::vector<Access> io;std::array<unsigned,2048> stores{};
   core.setBusWatch([&](std::uint16_t address,std::uint8_t value,bool write,std::uint64_t cycle){
    (void)cycle;assert(write||address>=0xC000);
    if(address>=0xC000){io.push_back({address,write});if(write)assert(value==flags*17);}
    else if(address>=0x100&&address<0x200){} // hardware return frames only
    else if(address>=0x400&&address<0x800){unsigned i=address-0x400+(core.displayState().page2?1024:0);assert(value==0xA0&&visible[i%1024]);++stores[i];}
    else {assert((address==mode||(on&&address==on))&&value==0);}
   });
   assert(core.watchAddresses(0,0xBFFF,false,true));assert(core.watchAddresses(0xC000,0xC0FF,true,true));
   const auto begin=core.cpuState().cycles;unsigned minimum=0xFD,steps=0;
   while(core.cpuState().programCounter!=0x5000&&steps++<20000){core.step();minimum=std::min<unsigned>(minimum,core.cpuState().stackPointer);assert(minimum>=0xF0);}
   state=core.cpuState();assert(state.programCounter==0x5000&&state.stackPointer==0xFF);
   assert((state.status&12)==(((flags&2)?4:0)|((flags&8)?8:0)));
   const unsigned ports[]={0xC001,0xC00D,0xC00F,0xC051,0xC052,0xC054,0xC055,0xC054};
   assert(io.size()==8);for(unsigned i=0;i<8;++i)assert(io[i].address==ports[i]&&io[i].write==(i<3));
   const auto display=core.displayState();assert(display.eightyStore&&display.eightyColumn&&display.altCharSet&&display.text&&!display.mixed&&!display.page2&&display.hiRes==spec.hires&&display.an3==spec.an3);
   for(unsigned i=0;i<2048;++i)assert(stores[i]==unsigned(visible[i%1024]));
   assert(core.readRam(pom2::RamBank::Main,0,main.data(),main.size()));assert(core.readRam(pom2::RamBank::Aux,0,aux.data(),aux.size()));
   for(unsigned i=0;i<main.size();++i){if(i<0x100||i>=0x200)assert(main[i]==expected_main[i]);assert(aux[i]==expected_aux[i]);}
   std::printf("%u %u %u %llu %u 0\n",flags,scenario,repeat,static_cast<unsigned long long>(state.cycles-begin),255-minimum);
  }
 }
}
