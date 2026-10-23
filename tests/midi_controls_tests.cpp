#include "TestSupport.h"
#include "rmx/ControlActions.h"
#include "rmx/MidiControls.h"
#include <vector>

int main() {
    return runTests([] {
        rmx::MidiControls controls;
        rmx::ParameterStore params;
        std::vector<rmx::Event> events;
        auto send = [&](rmx::Event event) { events.push_back(event); };
        controls.process(0xb0, 17, 0, 0, params, send);
        require(params.get(rmx::Param::Low) == 0, "Pickup changed parameter before reaching its value");
        controls.process(0xb0, 17, 127, 0, params, send);
        require(params.get(rmx::Param::Low) == 1, "Pickup failed when crossing current value");
        controls.cc[17].store(static_cast<int>(rmx::Param::High));
        controls.process(0xb0, 17, 120, 0, params, send);
        require(params.get(rmx::Param::High) == 0, "Remapping retained old pickup state");
        controls.learnTarget.store(static_cast<int>(rmx::Param::Tempo));
        controls.process(0xb0, 30, 51, 0, params, send);
        require(controls.learnedCC.load() == 30 && std::abs(params.get(rmx::Param::Tempo) - 120) < 1,
                "MIDI learn failed");
        controls.process(0x90, 36, 127, 0, params, send);
        controls.process(0xb0, 64, 127, 0, params, send);
        controls.process(0xfc, 0, 0, 0, params, send);
        require(events.size() == 3 && events[0].type == rmx::EventType::Trigger &&
                    events[1].type == rmx::EventType::RollStart && events[2].type == rmx::EventType::RollStop,
                "Shared MIDI event rules differ");
        controls.process(0xfa, 0, 0, 0, params, send);
        for (int tick = 0; tick < 120; ++tick)
            controls.process(0xf8, 0, 0, tick / 48., params, send);
        const auto transport = controls.transport(119 / 48.);
        require(transport.synced && std::abs(transport.bpm - 120) < .001,
                "MIDI clock failed at timestamp zero");
        require(!controls.transport(3.1).synced, "Stale MIDI clock stayed synchronized");
        controls.reset();
        require(!controls.transport(0).synced, "Reset kept old MIDI transport");
        require(rmx::toggleSource(2, rmx::Source::Input) == 1 &&
                    rmx::toggleSource(1, rmx::Source::Input) == 2,
                "Source encoding changed");
    });
}
