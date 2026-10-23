#pragma once
#include "BoardProfile.h"
#include "ControlExpanders.h"
#include "WireFormat.h"
#include "daisy_seed.h"
#include <initializer_list>

namespace rmx::embedded {
class BoardIO {
  public:
    bool initialize() {
        using namespace daisy;
        permit.Init(DaisySeed::GetPin(permitPin), GPIO::Mode::OUTPUT);
        permit.Write(false);
        heartbeat.Init(seed::D13, GPIO::Mode::OUTPUT);
        heartbeat.Write(false);
        gainMode.Init(seed::D9, GPIO::Mode::OUTPUT);
        gainMode.Write(false);
        armed.Init(DaisySeed::GetPin(armedPin), GPIO::Mode::INPUT, GPIO::Pull::PULLDOWN);
        blank.Init(seed::D14, GPIO::Mode::OUTPUT);
        blank.Write(true);
        latch.Init(seed::D7, GPIO::Mode::OUTPUT);
        latch.Write(false);
        if constexpr (!externalConverter) {
            bypass.Init(seed::D0, GPIO::Mode::INPUT, GPIO::Pull::PULLUP);
            levelMode.Init(seed::D25, GPIO::Mode::INPUT, GPIO::Pull::PULLUP);
        }
        expanderReset.Init(DaisySeed::GetPin(resetPin), GPIO::Mode::OUTPUT);
        expanderReset.Write(false);
        System::Delay(externalConverter ? 20 : 1);
        expanderReset.Write(true);
        System::Delay(1);
        I2CHandle::Config cfg;
        cfg.periph = I2CHandle::Config::Peripheral::I2C_1;
        cfg.mode = I2CHandle::Config::Mode::I2C_MASTER;
        cfg.speed = I2CHandle::Config::Speed::I2C_400KHZ;
        cfg.pin_config.scl = seed::D11;
        cfg.pin_config.sda = seed::D12;
        if (i2c.Init(cfg) != I2CHandle::Result::OK)
            return false;
        SpiHandle::Config spiCfg;
        spiCfg.periph = SpiHandle::Config::Peripheral::SPI_1;
        spiCfg.mode = SpiHandle::Config::Mode::MASTER;
        spiCfg.direction = SpiHandle::Config::Direction::TWO_LINES_TX_ONLY;
        spiCfg.nss = SpiHandle::Config::NSS::SOFT;
        spiCfg.pin_config.sclk = seed::D8;
        spiCfg.pin_config.mosi = seed::D10;
        spiCfg.pin_config.miso = Pin();
        spiCfg.pin_config.nss = Pin();
        spiCfg.baud_prescaler = SpiHandle::Config::BaudPrescaler::PS_64;
        if (spi.Init(spiCfg) != SpiHandle::Result::OK)
            return false;
        if (!configureControlExpanders(
                [this](uint8_t a, uint8_t r, std::initializer_list<uint8_t> b) { return write(a, r, b); },
                [this](uint8_t a, uint8_t r, uint8_t* b, uint16_t n) { return read(a, r, b, n); },
                externalConverter))
            return false;
        // Trill Craft protocol, based on Bela's published driver (see README).
        if (!trill({255}))
            return false;
        System::Delay(25);
        uint8_t identify[3]{};
        if (i2c.ReceiveBlocking(0x30, identify, 3, 3) != I2CHandle::Result::OK || identify[1] != 3)
            return false;
        if (!trill({1, 3}) || !trill({2, 0, 10}) || !trill({3, 2}) || !trill({6}))
            return false;
        System::Delay(150);
        return true;
    }
    bool buttons(uint32_t& pressed) {
        return readControlButtons(
            [this](uint8_t a, uint8_t r, uint8_t* b, uint16_t n) { return read(a, r, b, n); }, pressed);
    }
    bool releaseAngle(uint16_t& raw) {
        uint8_t data[3];
        if (!read(0x36, 0x0b, data, 3) || (data[0] & 0x38) != 0x20)
            return false;
        raw = static_cast<uint16_t>(((data[1] & 15) << 8) | data[2]);
        return true;
    }
    bool touch(Touch& value) {
        uint8_t bytes[16];
        if (!read(0x30, 4, bytes, 16))
            return false;
        std::array<uint16_t, 8> readings;
        for (size_t i = 0; i < 8; ++i)
            readings[i] = static_cast<uint16_t>((bytes[2 * i] << 8) | bytes[2 * i + 1]);
        value = touchPosition(readings);
        return true;
    }
    bool feedback(const std::array<uint16_t, 96>& values) {
        auto frame = packLedFrame(values);
        if (spi.BlockingTransmit(frame.data(), frame.size(), 3) != daisy::SpiHandle::Result::OK) {
            blank.Write(true);
            return false;
        }
        latch.Write(true);
        latch.Write(false);
        blank.Write(false);
        return true;
    }
    bool pollRearStatus() {
        if constexpr (externalConverter) {
            uint8_t data = 0;
            rearValid_ = read(0x22, 0x12, &data, 1);
            rear_ = rearValid_ ? data : 0; // Failed status is bypass / unqualified.
            return rearValid_;
        }
        return true;
    }
    bool analogQualified() const {
        return !externalConverter || (rearValid_ && (rear_ & 4));
    }
    bool inputQualified() const {
        return !externalConverter || (rearValid_ && (rear_ & 8));
    }
    bool manualBypass() {
        if constexpr (externalConverter)
            return !rearValid_ || !(rear_ & 2);
        return !bypass.Read();
    }
    bool sendReturn() {
        if constexpr (externalConverter)
            return rearValid_ && !(rear_ & 1);
        return !levelMode.Read();
    }
    bool codecRead(uint8_t reg, uint8_t& value) {
        return read(0x18, reg, &value, 1);
    }
    bool codecWrite(uint8_t reg, uint8_t value) {
        return write(0x18, reg, {value});
    }
    void disableConverter() {
        if constexpr (externalConverter) {
            permit.Write(false);
            expanderReset.Write(false);
            rearValid_ = false;
        }
    }
    bool hardwareArmed() {
        return armed.Read();
    }
    void connectionGain(bool sendReturn) {
        gainMode.Write(sendReturn);
    }
    void relayPermit(bool on) {
        permit.Write(on);
    }
    void audioHeartbeat() {
        heartbeat.Toggle();
    }

  private:
    daisy::I2CHandle i2c;
    daisy::SpiHandle spi;
    daisy::GPIO permit, heartbeat, gainMode, armed, blank, latch, bypass, levelMode, expanderReset;
    bool rearValid_ = false;
    uint8_t rear_ = 0;
    bool read(uint8_t addr, uint8_t reg, uint8_t* data, uint16_t count) {
        return i2c.ReadDataAtAddress(addr, reg, 1, data, count, 3) == daisy::I2CHandle::Result::OK;
    }
    bool write(uint8_t addr, uint8_t reg, std::initializer_list<uint8_t> bytes) {
        uint8_t packet[8]{};
        size_t n = 0;
        for (auto v : bytes)
            packet[n++] = v;
        return i2c.WriteDataAtAddress(addr, reg, 1, packet, n, 3) == daisy::I2CHandle::Result::OK;
    }
    bool trill(std::initializer_list<uint8_t> bytes) {
        const bool ok = write(0x30, 0, bytes);
        daisy::System::Delay(15);
        return ok;
    }
};
} // namespace rmx::embedded
