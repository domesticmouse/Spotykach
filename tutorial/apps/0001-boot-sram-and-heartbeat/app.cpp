#include "app.h"
#include "boot_controller.h"
#include "daisy_seed.h"

using namespace daisy;

namespace spotykach {

class AppImpl {
  public:
    AppImpl() = default;
    ~AppImpl() = default;

    void Init() {
        seed_.Init(true);
        boot_btn_.Init(
            seed::D2,
            0,
            Switch::TYPE_MOMENTARY,
            Switch::POLARITY_INVERTED,
            GPIO::Pull::NOPULL);
    }

    void Loop() {
        while (true) {
            boot_btn_.Debounce();

            const BootAction action = boot_ctrl_.Update(
                boot_btn_.Pressed(),
                boot_btn_.TimeHeldMs());

            if (action == BootAction::EnterDfuBootloader) {
                System::ResetToBootloader(
                    System::BootloaderMode::DAISY_INFINITE_TIMEOUT);
            } else if (action == BootAction::SystemReset) {
                HAL_NVIC_SystemReset();
            }

            const bool led_on = BootController::StepHeartbeat(
                System::GetNow(), 250);
            seed_.SetLed(led_on);
            System::Delay(1);
        }
    }

  private:
    NOCOPY(AppImpl)

    DaisySeed      seed_;
    Switch         boot_btn_;
    BootController boot_ctrl_;
};

static AppImpl impl;

void Application::Init() {
    impl.Init();
}

void Application::Loop() {
    impl.Loop();
}

} // namespace spotykach
