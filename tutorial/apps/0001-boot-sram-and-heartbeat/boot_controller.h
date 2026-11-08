#pragma once

#include <cstdint>
#include "nocopy.h"

namespace spotykach {

enum class BootAction : uint8_t {
    None = 0,
    SystemReset,
    EnterDfuBootloader,
};

class BootController {
  public:
    static constexpr uint32_t kDfuHoldThresholdMs = 3000;

    BootController() = default;
    ~BootController() = default;

    BootAction Update(bool is_pressed, uint32_t held_ms) {
        if (is_pressed && held_ms >= kDfuHoldThresholdMs) {
            was_pressed_ = is_pressed;
            return BootAction::EnterDfuBootloader;
        }

        if (!is_pressed && was_pressed_) {
            was_pressed_ = false;
            return BootAction::SystemReset;
        }

        was_pressed_ = is_pressed;
        return BootAction::None;
    }

    bool was_pressed() const { return was_pressed_; }

    static constexpr bool StepHeartbeat(uint32_t elapsed_ms, uint32_t half_period_ms) {
        if (half_period_ms == 0) {
            return false;
        }
        return ((elapsed_ms / half_period_ms) % 2U) == 0U;
    }

  private:
    NOCOPY(BootController)
    bool was_pressed_ = false;
};

} // namespace spotykach
