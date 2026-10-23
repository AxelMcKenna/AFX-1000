#include "TestSupport.h"
#include "rmx/dsp/Isolator.h"
#include "rmx/dsp/SceneEffects.h"

int main() {
    return runTests([] {
        rmx::ParameterStore parameters;
        auto values = parameters.snapshot();
        auto set = [&](rmx::Param parameter, float value) { values[static_cast<size_t>(parameter)] = value; };
        rmx::dsp::Context context{values, values, 48000, 120, 0, 0, .0026f};
        set(rmx::Param::IsolateMode, 2);
        for (auto parameter : {rmx::Param::Low, rmx::Param::Mid, rmx::Param::High})
            set(parameter, 1);
        rmx::dsp::Isolator isolator;
        isolator.prepare(context.sr);
        isolator.configure(250, 4000, context.sr);
        // A band roll engaged on silence must keep that frozen window, even
        // when this bus has never previously received a nonzero sample.
        for (; context.frame < 1000; ++context.frame)
            isolator.process({}, 0, context);
        for (; context.frame < 3000; ++context.frame) {
            const auto out = isolator.process({.2f, -.1f}, 0, context);
            require(out.l == 0 && out.r == 0, "Silent band roll restarted on the first input signal");
        }

        // Crossovers cached at one rate must be invalidated by prepare().
        values = parameters.snapshot();
        set(rmx::Param::Low, -.5f);
        context.sr = 96000;
        isolator.prepare(context.sr);
        isolator.configure(250, 4000, context.sr);
        rmx::dsp::Isolator fresh;
        fresh.prepare(context.sr);
        fresh.configure(250, 4000, context.sr);
        for (unsigned i = 0; i < 2048; ++i) {
            rmx::Stereo input{std::sin(i * .13f) * .2f, .1f};
            const auto actual = isolator.process(input, 0, context);
            const auto expected = fresh.process(input, 0, context);
            require(actual.l == expected.l && actual.r == expected.r,
                    "Crossover cache survived a sample-rate change");
        }

        rmx::dsp::SceneEffects scene;
        context.sr = 48000;
        scene.prepare(context.sr);
        set(rmx::Param::SceneOn, 1);
        set(rmx::Param::SceneDepth, 1);
        set(rmx::Param::SceneType, 4);
        set(rmx::Param::ReverbDecay, .3f);
        set(rmx::Param::SceneResonance, .1f);
        double tailEnergy = 0;
        for (unsigned i = 0; i < 48000; ++i) {
            const auto output = scene.process(i == 0 ? rmx::Stereo{.5f, .25f} : rmx::Stereo{}, 1, context);
            if (i > 100)
                tailEnergy += output.l * output.l + output.r * output.r;
        }
        require(tailEnergy > 1.e-5, "Reverb slept before its audible tail finished");
        // Let the reverb decay while another scene is selected, then wake it.
        set(rmx::Param::SceneType, 1);
        for (unsigned i = 0; i < 48000 * 10; ++i)
            scene.process({}, 1, context);
        set(rmx::Param::SceneType, 4);
        rmx::dsp::SceneEffects freshScene;
        freshScene.prepare(context.sr);
        for (unsigned i = 0; i < 12000; ++i) {
            const rmx::Stereo input = i == 0 ? rmx::Stereo{.5f, .25f} : rmx::Stereo{};
            const auto actual = scene.process(input, 1, context);
            const auto expected = freshScene.process(input, 1, context);
            require(std::abs(actual.l - expected.l) < 1.e-10f && std::abs(actual.r - expected.r) < 1.e-10f,
                    "Reverb woke with stale history after draining its tail");
        }
    });
}
