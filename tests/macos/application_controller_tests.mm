#include "TestSupport.h"
#include "src/macos/ApplicationController.h"
#import <Cocoa/Cocoa.h>
#include <vector>

int main() {
    @autoreleasepool {
        return runTests([] {
            const auto folder = std::filesystem::temp_directory_path() /
                                ("rmx-controller-" +
                                 std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
            std::filesystem::create_directories(folder);
            auto controller = std::make_shared<ApplicationController>(folder / "session.rmx");
            std::vector<int> completed;
            bool resultsValid = true;
            auto done = [&](int id, bool expectedSuccess) {
                return [&, id, expectedSuccess](ApplicationController::Result result) {
                    resultsValid = resultsValid && result.ok == expectedSuccess && [NSThread isMainThread];
                    completed.push_back(id);
                };
            };
            controller->restore(done(1, true));
            controller->load(folder / "missing.rmx", done(2, false));
            controller->save(folder / "saved.rmx", done(3, true));
            controller->stop(done(4, true));
            controller->shutdown(done(5, true));
            require(controller->busy(), "Queued session work was not marked busy");
            const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
            while (completed.size() < 5 && std::chrono::steady_clock::now() < deadline) {
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, .01, true);
            }
            require(completed == std::vector<int>({1, 2, 3, 4, 5}) && resultsValid,
                    "Control queue lost ordering, error recovery or main-thread completions");
            require(!controller->busy() && !controller->audio().running(),
                    "Shutdown finished with pending work or active audio");
            require(std::filesystem::exists(folder / "saved.rmx") &&
                        std::filesystem::exists(folder / "session.rmx"),
                    "Shutdown did not finish persistence");
            controller.reset();
            std::filesystem::remove_all(folder);
        });
    }
}
