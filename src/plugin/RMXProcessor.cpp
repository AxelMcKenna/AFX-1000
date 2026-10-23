#include "RMXProcessor.h"

RMXProcessor::RMXProcessor()
    : AudioProcessor(BusesProperties()
                         .withInput("Stereo input", juce::AudioChannelSet::stereo(), true)
                         .withOutput("Stereo output", juce::AudioChannelSet::stereo(), true)) {
    for (size_t i = 0; i < rmx::parameterCount; ++i) {
        auto* parameter = new EngineParameter(engine.params, static_cast<rmx::Param>(i));
        hostParameters[i] = parameter;
        addParameter(parameter);
        lastNotified[i] = parameter->getValue();
    }
    publish(rmx::makeFactoryBank());
    startTimerHz(30);
}

RMXProcessor::~RMXProcessor() {
    stopTimer();
}

double RMXProcessor::getTailLengthSeconds() const {
    const double delay = 60 / std::max(40.f, engine.params.get(rmx::Param::Tempo)) *
                         rmx::beatDivisions[static_cast<size_t>(engine.params.get(rmx::Param::SceneTime))];
    const double feedback = std::clamp(static_cast<double>(engine.params.get(rmx::Param::Feedback)) *
                                           (.7 + engine.params.get(rmx::Param::SceneResonance) * .6),
                                       .01, .96);
    // Imported 30-second samples can play four times slower at -24 semitones.
    return std::max(120., delay * std::log(.0001) / std::log(feedback) + 2);
}

void RMXProcessor::prepareToPlay(double rate, int block) {
    midiControls.reset();
    sampleClock = 0;
    engine.setBank(&published.load()->bank);
    engine.prepare(rate, static_cast<uint32_t>(block));
}

void RMXProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
    juce::ScopedNoDenormals noDenormals;
    if (buffer.getNumChannels() < 2) {
        buffer.clear();
        return;
    }
    const auto* assets = published.load(std::memory_order_acquire);
    engine.setBank(&assets->bank);
    std::array<rmx::Event, 256> events{};
    size_t count = 0;
    for (const auto metadata : midi) {
        const auto* bytes = metadata.data;
        const int size = metadata.numBytes;
        if (size < 1)
            continue;
        const uint8_t a = size >= 2 ? bytes[1] : 0, b = size >= 3 ? bytes[2] : 0;
        if ((bytes[0] < 0xf0) && size < 3)
            continue;
        const auto offset = static_cast<uint32_t>(std::max(0, metadata.samplePosition));
        midiControls.process(bytes[0], a, b, (sampleClock + offset) / getSampleRate(), engine.params,
                             [&](rmx::Event event) {
                                 event.offset = offset;
                                 if (count < events.size())
                                     events[count++] = event;
                                 else
                                     engine.meters.droppedEvents.fetch_add(1, std::memory_order_relaxed);
                             });
    }
    midi.clear();
    auto transport = midiControls.transport(sampleClock / getSampleRate());
    if (auto* head = getPlayHead())
        if (auto position = head->getPosition()) {
            if (auto tempo = position->getBpm()) {
                transport.bpm = *tempo;
                transport.synced = true;
            }
            if (auto ppq = position->getPpqPosition())
                transport.beat = std::max(0., *ppq);
            transport.playing = position->getIsPlaying();
        }

    engine.process(buffer.getReadPointer(0), buffer.getReadPointer(1), buffer.getWritePointer(0),
                   buffer.getWritePointer(1), static_cast<uint32_t>(buffer.getNumSamples()), transport,
                   {events.data(), count});
    acknowledged.store(assets->generation, std::memory_order_release);
    sampleClock += static_cast<uint64_t>(buffer.getNumSamples());
}

void RMXProcessor::getStateInformation(juce::MemoryBlock& destination) {
    const juce::ScopedLock guard(assetLock);
    state.capture(engine.params);
    const auto data = state.serialize();
    destination.replaceAll(data.data(), data.size());
}

void RMXProcessor::setStateInformation(const void* data, int bytes) {
    if (bytes <= 0)
        return;
    try {
        restore(rmx::State::parse({static_cast<const char*>(data), static_cast<size_t>(bytes)}));
    } catch (const std::exception& e) {
        const juce::ScopedLock lock(assetLock);
        assetMessage = e.what();
    }
}

void RMXProcessor::change(rmx::Param p, float value) {
    auto* parameter = hostParameters[static_cast<size_t>(p)];
    parameter->beginChangeGesture();
    parameter->setValueNotifyingHost(parameter->convertTo0to1(rmx::sanitize(p, value)));
    parameter->endChangeGesture();
}

void RMXProcessor::importSample(int slot, const juce::File& file) {
    auto sample = rmx::readWav(file.getFullPathName().toStdString());
    const juce::ScopedLock lock(assetLock);
    auto next = published.load()->bank;
    next.slots[static_cast<size_t>(slot)] = std::move(sample);
    state.samplePaths[static_cast<size_t>(slot)] = file.getFullPathName().toStdString();
    publish(std::move(next));
    assetMessage = "Sample installed";
}

void RMXProcessor::save(const juce::File& file) {
    const juce::ScopedLock lock(assetLock);
    state.capture(engine.params);
    state.save(file.getFullPathName().toStdString());
}

void RMXProcessor::load(const juce::File& file) {
    restore(rmx::State::load(file.getFullPathName().toStdString()));
}

void RMXProcessor::publish(rmx::SampleBank bank) {
    auto next = std::make_unique<Assets>(Assets{std::move(bank), ++generation});
    const auto* ptr = next.get();
    owned.push_back(std::move(next));
    published.store(ptr, std::memory_order_release);
    const auto safe = acknowledged.load(std::memory_order_acquire);
    std::erase_if(owned, [&](const auto& asset) { return asset->generation < safe; });
    for (size_t i = 0; i < 128; ++i)
        midiControls.cc[i].store(state.cc[i]);
}

void RMXProcessor::restore(rmx::State next) {
    auto bank = rmx::makeFactoryBank();
    juce::String missing;
    for (size_t i = 0; i < 16; ++i)
        if (!next.samplePaths[i].empty()) {
            try {
                bank.slots[i] = rmx::readWav(next.samplePaths[i]);
            } catch (...) {
                missing += " " + juce::String(static_cast<int>(i + 1));
            }
        }
    const juce::ScopedLock lock(assetLock);
    state = std::move(next);
    publish(std::move(bank));
    for (size_t i = 0; i < rmx::parameterCount; ++i)
        change(static_cast<rmx::Param>(i), state.values[i]);
    assetMessage =
        missing.isEmpty() ? "Preset restored" : "Missing samples; factory sounds in slots" + missing;
}

void RMXProcessor::notifyParameterChanges() {
    for (size_t i = 0; i < rmx::parameterCount; ++i) {
        const float latest = hostParameters[i]->getValue();
        if (latest != lastNotified[i]) {
            lastNotified[i] = latest;
            hostParameters[i]->sendValueChangedMessageToListeners(latest);
        }
    }
}

void RMXProcessor::timerCallback() {
    notifyParameterChanges();
}
