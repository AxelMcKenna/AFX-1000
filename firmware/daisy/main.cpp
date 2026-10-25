#include "daisy_seed.h"
#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include "rmx/EmbeddedControls.h"
#include "BoardConfig.h"
#include "CardStorage.h"
#include <atomic>
#include <bit>
#include <cstddef>
#include <memory_resource>
#include <new>

using namespace daisy;
static_assert(rmx::board::buttonCount==static_cast<unsigned>(rmx::Button::Count));
namespace {
DaisySeed hardware;
// Do not construct an Engine or SampleBank before SDRAM initialization: their
// PMR vectors capture the current resource when they are constructed.
alignas(std::max_align_t) DSY_SDRAM_BSS std::byte audioMemory[60u*1024*1024];
alignas(rmx::Engine) std::byte engineStorage[sizeof(rmx::Engine)];
alignas(rmx::SampleBank) std::byte bankStorage[sizeof(rmx::SampleBank)];
rmx::Engine* engine{};
std::atomic<uint32_t> audioBlocks{};
rmx::EmbeddedControls controls;
rmx::StartupEnvelope startupEnvelope;
GPIO buttonLoad,buttonClock,buttonData,ledData,ledClock,ledLatch,ledOe,heartbeat,dspReady;
I2CHandle touchBus;
bool touchReady{},audioStarted{};
// AXI globals: FatFS and SDMMC DMA cannot access the DTCM stack.
rmx::board::CardStorage card;
rmx::board::CardState cardState{rmx::board::CardState::Absent};
constexpr uint8_t touchAddress=0x5a;

void output(GPIO& pin,unsigned number,bool high=false) {
    pin.Init(DaisySeed::GetPin(number),GPIO::Mode::OUTPUT); pin.Write(high);
}
void audio(AudioHandle::InputBuffer input,AudioHandle::OutputBuffer output,size_t size) {
    engine->process(input[0],input[1],output[0],output[1],static_cast<uint32_t>(size));
    startupEnvelope.process(output[0],output[1],size);
    audioBlocks.fetch_add(1,std::memory_order_relaxed);
}
bool touchWrite(uint8_t reg,uint8_t value) {
    uint8_t bytes[]{reg,value};
    return touchBus.TransmitBlocking(touchAddress,bytes,2,2)==I2CHandle::Result::OK;
}
bool initTouch() {
    I2CHandle::Config config;
    config.periph=I2CHandle::Config::Peripheral::I2C_1;
    config.speed=I2CHandle::Config::Speed::I2C_400KHZ;
    config.mode=I2CHandle::Config::Mode::I2C_MASTER;
    config.pin_config.scl=DaisySeed::GetPin(rmx::board::i2c_scl);
    config.pin_config.sda=DaisySeed::GetPin(rmx::board::i2c_sda);
    if(touchBus.Init(config)!=I2CHandle::Result::OK) return false;
    if(!touchWrite(0x80,0x63)) return false;
    System::Delay(2);
    if(!touchWrite(0x5e,0)) return false;
    // NXP MPR121: baseline filters, touch/release hysteresis, eight electrodes.
    constexpr uint8_t setup[][2]={{0x2b,1},{0x2c,1},{0x2d,14},{0x2e,0},{0x2f,1},{0x30,5},{0x31,1},{0x32,0},{0x5b,0},{0x5c,0x10},{0x5d,0x20}};
    for(const auto& entry:setup) if(!touchWrite(entry[0],entry[1])) return false;
    for(unsigned i=0;i<8;++i) if(!touchWrite(0x41+2*i,12)||!touchWrite(0x42+2*i,6)) return false;
    return touchWrite(0x5e,0x88);
}
uint32_t readButtons() {
    buttonClock.Write(false); buttonLoad.Write(false);
    System::DelayUs(1); buttonLoad.Write(true);
    uint32_t result=0;
    // QH is read before each shift. Active-low switches have 10k pull-ups.
    for(unsigned i=0;i<32;++i) {
        if(!buttonData.Read()) result|=uint32_t{1}<<i;
        buttonClock.Write(true); buttonClock.Write(false);
    }
    return result;
}
void ledFrame() {
    std::array<bool,96> bits{};
    auto get=[](rmx::Param p){return engine->params.get(p);};
    bits[0]=get(rmx::Param::Quantize)>.5f; bits[1]=get(rmx::Param::AutoTempo)>.5f;
    const int source=static_cast<int>(get(rmx::Param::SceneSource));
    bits[5]=source==0||source==2;bits[6]=source==1||source==2;
    if(get(rmx::Param::IsolateOn)>.5f)bits[7+static_cast<unsigned>(get(rmx::Param::IsolateMode))]=true;
    bits[12]=get(rmx::Param::XSource)>.5f;
    bits[17]=get(rmx::Param::Overdub)>.5f;bits[18]=get(rmx::Param::XHold)>.5f;
    if(get(rmx::Param::SceneOn)>.5f) bits[19+static_cast<unsigned>(get(rmx::Param::SceneType))]=true;
    if(get(rmx::Param::SampleSource)>.5f)bits[29+static_cast<unsigned>(get(rmx::Param::Bank))]=true;
    for(unsigned i=0;i<11;++i) {
        const float threshold=std::pow(10.f,(-30+3*static_cast<float>(i))/20.f);
        bits[33+i]=engine->meters.input.load()>threshold; bits[44+i]=engine->meters.output.load()>threshold;
    }
    const unsigned bpm=static_cast<unsigned>(std::clamp(engine->meters.tempo.load(),0.f,999.f));
    constexpr unsigned digits[]{0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    for(unsigned digit=0;digit<3;++digit) {
        const unsigned number=digit==0?bpm/100:digit==1?(bpm/10)%10:bpm%10;
        for(unsigned segment=0;segment<7;++segment) bits[55+digit*8+segment]=(digits[number]>>segment)&1u;
    }
    ledLatch.Write(false);
    for(int i=95;i>=0;--i) {ledClock.Write(false);ledData.Write(bits[static_cast<size_t>(i)]);ledClock.Write(true);}
    ledClock.Write(false);ledLatch.Write(true);ledOe.Write(false);
}
}
int main() {
    hardware.Init(true);
    // Heartbeat is permission for the external watchdog/relay circuit to enable
    // processed output. Its external pull-down must keep the unit bypassed at boot.
    output(heartbeat,rmx::board::watchdog_heartbeat,false);
    output(dspReady,rmx::board::dsp_ready,false);
    output(ledOe,rmx::board::led_oe,true);
    try {
        rmx::FixedArena arena(audioMemory,sizeof(audioMemory));
        std::pmr::set_default_resource(&arena);
        engine=new(engineStorage) rmx::Engine;
        auto* bank=new(bankStorage) rmx::SampleBank(rmx::makeFactoryBank(48000,false));
        engine->setBank(bank); engine->prepare(48000,64);
        cardState=card.load(*bank,engine->params);
        output(buttonLoad,rmx::board::button_load,true); output(buttonClock,rmx::board::button_clock);
        buttonData.Init(DaisySeed::GetPin(rmx::board::button_data),GPIO::Mode::INPUT,GPIO::Pull::PULLUP);
        output(ledData,rmx::board::led_data);output(ledClock,rmx::board::led_clock);output(ledLatch,rmx::board::led_latch);
        AdcChannelConfig adc[2];
        for(unsigned i=0;i<2;++i) adc[i].InitMux(DaisySeed::GetPin(i?rmx::board::adc_mux_b:rmx::board::adc_mux_a),8,DaisySeed::GetPin(rmx::board::mux_s0),DaisySeed::GetPin(rmx::board::mux_s1),DaisySeed::GetPin(rmx::board::mux_s2),AdcChannelConfig::SPEED_64CYCLES_5);
        hardware.adc.Init(adc,2); hardware.adc.Start();
        touchReady=initTouch();
        hardware.SetAudioSampleRate(SaiHandle::Config::SampleRate::SAI_48KHZ); hardware.SetAudioBlockSize(64); hardware.StartAudio(audio); audioStarted=true;
        auto read=[](rmx::Param p){return engine->params.get(p);};
        auto write=[](rmx::Param p,float v){engine->params.set(p,v);};
        auto send=[](rmx::Event e){engine->enqueue(e);};
        uint32_t previousBlocks=0,lastTick=System::GetNow(),ledTick=lastTick,lastProgress=lastTick; bool heartbeatState=false;
        while(true) {
            const auto now=System::GetNow(); if(now-lastTick<1) continue;lastTick=now;
            controls.buttons(readButtons(),read,write,send);
            for(unsigned i=0;i<std::size(rmx::board::adcParameters);++i) {
                const auto p=rmx::board::adcParameters[i];
                const bool centered=p==rmx::Param::Low||p==rmx::Param::Mid||p==rmx::Param::High||p==rmx::Param::XPitch;
                controls.analog(i,p,card.calibration.apply(i,hardware.adc.GetMuxFloat(i/8,i%8),centered),write);
            }
            uint8_t status[2]{};
            if(touchReady) {
                const bool ok=touchBus.ReadDataAtAddress(touchAddress,0,1,status,2,2)==I2CHandle::Result::OK;
                // A disconnected touch sensor releases a gesture, never latches it.
                controls.touch(ok?status[0]:0,write,send);
            }
            const auto blocks=audioBlocks.load(std::memory_order_relaxed);
            constexpr unsigned startupBlocks=(rmx::StartupEnvelope::fadeFrames+63)/64;
            if(blocks!=previousBlocks) {heartbeatState=!heartbeatState;heartbeat.Write(heartbeatState);previousBlocks=blocks;lastProgress=now;dspReady.Write(blocks>=startupBlocks);}
            if(now-lastProgress>10) dspReady.Write(false);
            if(now-ledTick>=25) {
                ledFrame();ledTick=now;
                const bool cardError=cardState==rmx::board::CardState::ManifestError||cardState==rmx::board::CardState::Partial||cardState==rmx::board::CardState::IoError;
                hardware.SetLed(cardError?(now/250)%2:touchReady);
            }
        }
    } catch(...) {
        heartbeat.Write(false);dspReady.Write(false);ledOe.Write(true);
        if(audioStarted) hardware.StopAudio();
        // No audio start/relay enable after allocation or initialization failure.
        while(true) {hardware.SetLed(true);System::Delay(100);hardware.SetLed(false);System::Delay(100);}
    }
}
