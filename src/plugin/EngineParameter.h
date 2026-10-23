#pragma once
#include "rmx/Parameters.h"
#include <juce_audio_processors/juce_audio_processors.h>

// JUCE and the DSP share one atomic value. Audio-generated changes become
// visible immediately; deferred host notifications never write parameter state.
class EngineParameter final : public juce::RangedAudioParameter {
  public:
    EngineParameter(rmx::ParameterStore& store, rmx::Param id)
        : RangedAudioParameter(juce::ParameterID(text(info(id).id), 1), text(info(id).name)), store(store),
          id(id), range(info(id).min, info(id).max, info(id).discrete ? 1.f : 0.f) {}

    float getValue() const override {
        return convertTo0to1(store.get(id));
    }
    void setValue(float normalized) override {
        store.set(id, convertFrom0to1(normalized));
    }
    float getDefaultValue() const override {
        return convertTo0to1(info(id).initial);
    }
    const juce::NormalisableRange<float>& getNormalisableRange() const override {
        return range;
    }
    bool isDiscrete() const override {
        return info(id).discrete;
    }
    bool isBoolean() const override {
        return isDiscrete() && info(id).min == 0 && info(id).max == 1;
    }
    juce::String getText(float normalized, int maximumLength) const override {
        return juce::String(convertFrom0to1(normalized), isDiscrete() ? 0 : 3).substring(0, maximumLength);
    }
    float getValueForText(const juce::String& value) const override {
        return convertTo0to1(value.getFloatValue());
    }

  private:
    rmx::ParameterStore& store;
    rmx::Param id;
    juce::NormalisableRange<float> range;
    static const rmx::ParameterInfo& info(rmx::Param p) {
        return rmx::parameters[static_cast<size_t>(p)];
    }
    static juce::String text(std::string_view value) {
        return juce::String::fromUTF8(value.data(), static_cast<int>(value.size()));
    }
};
