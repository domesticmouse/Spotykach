#include <cassert>
#include <cstdio>
#include "boot_controller.h"

using spotykach::BootAction;
using spotykach::BootController;

static void TestIdleAndHoldBelowThreshold() {
    BootController ctrl;
    assert(ctrl.Update(false, 0) == BootAction::None);
    assert(ctrl.Update(true, 100) == BootAction::None);
    assert(ctrl.Update(true, 1500) == BootAction::None);
    assert(ctrl.Update(true, 2999) == BootAction::None);
}

static void TestShortPressReleaseTriggersSystemResetOnce() {
    BootController ctrl;
    assert(ctrl.Update(false, 0) == BootAction::None);
    assert(ctrl.Update(true, 450) == BootAction::None);
    assert(ctrl.Update(false, 0) == BootAction::SystemReset);
    assert(ctrl.Update(false, 0) == BootAction::None);
}

static void TestThreeSecondHoldEntersDfuBootloaderImmediately() {
    BootController ctrl;
    assert(ctrl.Update(true, 1000) == BootAction::None);
    assert(ctrl.Update(true, 2999) == BootAction::None);
    assert(ctrl.Update(true, 3000) == BootAction::EnterDfuBootloader);
    assert(ctrl.Update(true, 3500) == BootAction::EnterDfuBootloader);
}

static void TestHeartbeatCadence() {
    assert(BootController::StepHeartbeat(0, 250) == true);
    assert(BootController::StepHeartbeat(249, 250) == true);
    assert(BootController::StepHeartbeat(250, 250) == false);
    assert(BootController::StepHeartbeat(499, 250) == false);
    assert(BootController::StepHeartbeat(500, 250) == true);
    assert(BootController::StepHeartbeat(100, 0) == false);
}

int main() {
    TestIdleAndHoldBelowThreshold();
    TestShortPressReleaseTriggersSystemResetOnce();
    TestThreeSecondHoldEntersDfuBootloaderImmediately();
    TestHeartbeatCadence();
    std::printf("[PASS] 0001-boot-sram-and-heartbeat: 4/4 test suites passed\n");
    return 0;
}
