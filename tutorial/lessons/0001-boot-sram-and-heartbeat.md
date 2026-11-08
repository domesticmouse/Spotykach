---
title: "BOOT_SRAM Memory Layout, C++17 Application Lifecycle & Bootloader Rescue"
page_title: "Lesson 0001: BOOT_SRAM & Bootloader Rescue — Spotykach Firmware Course"
nav_id: "lesson-0001"
badge: "Lesson 0001 • C++17 & STM32H750 Bring-Up"
subtitle: "Understand how Spotykach boots from QSPI flash into AXI SRAM via alt_sram.lds, learn the C++17 idioms that structure main.cpp and app.cpp, and build a dual-verified firmware binary with a brick-proof D2 bootloader rescue controller."
card:
  title: "**BOOT_SRAM Memory Layout, C++17 Application Lifecycle & Bootloader Rescue**"
  summary: "Boot the STM32H750 from QSPI into AXI SRAM (`alt_sram.lds`), satisfy the `bleeptools/libDaisy` USB descriptor contract, and build a host-tested and ARM-compiled `D2` bootloader rescue controller."
---

## 1. Why Spotykach Cannot Boot Like a Normal Microcontroller {#why-boot-sram}

When you first look at the specs for the **Electro-Smith Daisy Seed** (`STM32H750IBK6`) sitting at the heart of the Spotykach PCB, it sounds massive: a 480 MHz ARM Cortex-M7 alongside 64 MB of external SDRAM{{sidenote:Despite its 480 MHz clock speed and 64 MB of external SDRAM, the STM32H750 "Value Line" chip has only **128 KB** of internal flash at `0x08000000`.}}. Then you check the internal flash size: **128 KB**.

Wait, 128 KB? Turns out, STMicroelectronics designed the STM32H750 "Value Line" with just enough internal flash to hold a bootloader. Once we compile `libDaisy`, `DaisySP`, FatFS SD card support, and the Spotykach dual-deck DSP engine, our firmware binary weighs in around **180–220 KB** — way too chunky to fit inside the chip's 128 KB internal flash.

So, how does Spotykach actually boot? It uses `APP_TYPE = BOOT_SRAM` with a custom linker script (`alt_sram.lds`). See the [Hardware Architecture Cheat Sheet](../reference/hardware-architecture.md) and [Glossary](../reference/glossary.md) for the full address table:

1. **Internal Flash (`0x08000000`, 128 KB)** permanently holds the **Daisy Bootloader** (`bootloader-spotykach-v2.bin`). When you run `make program-dfu`, you never overwrite internal flash.
2. **External QSPI NOR Flash (`0x90040000`, 8 MB)** stores your compiled firmware binary (`spotykach.bin`) across power cycles.
3. **Internal AXI SRAM (`SRAM_EXEC` at `0x24000000`, 256 KB)** is where your code actually runs. At power-on, the Daisy Bootloader copies your firmware from QSPI flash into `SRAM_EXEC` and jumps to your program's `Reset_Handler`.
4. **DTCMRAM (`0x20000000`, 128 KB)** holds the CPU stack (`_estack = 0x20020000`) and initialised `.data` variables for zero-wait-state 480 MHz access.

```mermaid caption="Figure 1.1: Spotykach BOOT_SRAM startup sequence and D2 boot button rescue loop"
flowchart LR
    subgraph PowerOn["1. Power-On / Reset"]
        BL["Internal Flash (0x08000000)\nbootloader-spotykach-v2.bin"] -->|Copies binary| QSPI["QSPI Flash (0x90040000)\nspotykach_l01.bin"]
        QSPI -->|Loads into RAM| SRAM["SRAM_EXEC (0x24000000)\n.isr_vector + .text + .rodata"]
    end
    subgraph Firmware["2. C++17 Firmware Execution"]
        SRAM --> MAIN["main() in main.cpp\napp.Init() -> app.Loop()"]
        MAIN --> D2{"D2 Boot Button\n(BootController)"}
        D2 -- "Held >= 3000 ms" --> DFU["System::ResetToBootloader()\nWhite breathing LEDs (USB DFU)"]
        D2 -- "Released (< 3000 ms)" --> RST["HAL_NVIC_SystemReset()\nClean reboot"]
        D2 -- "Idle" --> HB["Toggle Seed Heartbeat LED\nEvery 250 ms"]
    end
```

:::callout
**Recommended Primary Sources**: Before modifying startup or linker behavior, consult the [`libDaisy` Developer Guide](../reference/hardware-architecture.md) (`BOOT_SRAM` and memory domains) and the [`spotykach-submodules` Guide](../reference/verification-guide.md) (why `bleeptools/libDaisy` requires external USB descriptor strings in `main.cpp`).
:::

---

## 2. Preventing Self-Bricking: The `D2` Boot Button Contract {#d2-rescue-contract}

Here is a fun trap when writing your own `BOOT_SRAM` firmware from scratch: once the bootloader jumps into your `main()` in RAM, your code owns the CPU. If you forget to wire up a way back to the bootloader, the next time you try to flash an update over the rear USB-C port, nothing will answer. You then have to unscrew the enclosure to reach the tiny hardware buttons on the Daisy Seed itself.

So, how do we make sure we never brick our board? In the production Spotykach firmware (`app.cpp` lines 160–163 and `src/hw/hardware.cpp` lines 218–224), the rear **Reset / Boot** button (wired to Daisy Seed pin `seed::D2`) implements a two-tier safety mechanism:
- **Hold for ≥ 3000 ms**: While the button is still held down, `AppImpl::Loop()` detects `GetBootButtonHeldTime() >= 3000` and immediately invokes `System::ResetToBootloader(System::BootloaderMode::DAISY_INFINITE_TIMEOUT)`. The bottom pad LEDs begin breathing white so you know your finger can release the button and `make program-dfu` is ready.
- **Short tap and release (< 3000 ms)**: When you release the button (`!boot_btn_.Pressed() && was_pressed`), `Hardware::ProcessDigitalControls()` calls `HAL_NVIC_SystemReset()`, performing a clean software reboot.

Try dragging the hold-duration slider and toggling the `D2` button state in the interactive simulator below to see how this state machine behaves:

{{widget:spotykach-boot-sim}}

---

## 3. Building the Firmware Step-by-Step {#block-by-block}

Let's build our first complete, flashable Spotykach firmware (`tutorial/apps/0001-boot-sram-and-heartbeat/`) block by block, unpacking every C++17 feature along the way.

### Block 1: Preventing Accidental Hardware Copies (`nocopy.h`) {#block-1-nocopy}

In C++, if you write `class Application { ... };`, the compiler automatically generates a **copy constructor** and a **copy assignment operator**. For a class that owns physical microcontroller hardware (like audio DMA streams or GPIO pins), copying the object by mistake would create two objects fighting over the same hardware registers.

Spotykach prevents this at compile time with a one-line macro in `nocopy.h`:

```cpp caption="nocopy.h — Deleting copy and move operations in C++17"
#pragma once

#define NOCOPY(T)                  \
    T(const T& other) = delete;    \
    T(T&& other) = delete;         \
    T& operator=(const T& other) = delete; \
    T& operator=(T&& other) = delete;
```

- **`#pragma once`**: Tells the C++ preprocessor to include this header file at most once per compilation unit (`.cpp` file), preventing duplicate-definition errors.
- **`const T& other` (Copy) and `T&& other` (Move)**: In C++17, `&` denotes an lvalue reference (copying an existing named object) and `&&` denotes an rvalue reference (moving a temporary object).
- **`= delete;`**: Instructs the compiler to reject any code that tries to copy or move an instance of `T` with a clear compile-time error.

### Block 2: Hardware-Independent `BootController` (`boot_controller.h`) {#block-2-boot-controller}

To verify our logic on our computer (`make test`) *and* run the exact same code on the STM32H750 (`make`), we isolate the `D2` button state machine and heartbeat timer into a pure C++17 header `boot_controller.h` that depends only on `<cstdint>`:

```cpp caption="boot_controller.h — Pure C++17 boot rescue state machine and heartbeat calculator"
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
```

- **`#include <cstdint>` (`uint8_t`, `uint32_t`)**: Bare-metal code avoids ambiguous `int` sizes; `uint8_t` is guaranteed to be an unsigned 8-bit integer (1 byte) and `uint32_t` is an unsigned 32-bit integer (4 bytes, matching 32-bit ARM Cortex-M7 registers).
- **`namespace spotykach { ... }`**: Groups all Spotykach types under the `spotykach::` prefix so names never collide with `daisy::` or `daisysp::`.
- **`enum class BootAction : uint8_t`**: A C++17 strongly typed enumeration backed by a single byte (`uint8_t`). Unlike C `enum`, you must write `BootAction::EnterDfuBootloader`, preventing accidental integer mix-ups.
- **`static constexpr uint32_t kDfuHoldThresholdMs = 3000;`**: `constexpr` evaluates the constant at compile time with zero RAM cost.
- **Falling-edge detection (`!is_pressed && was_pressed_`)**: By storing the previous tick's button state in private member `was_pressed_`, `Update()` detects the exact moment a short press is released (`true` → `false`) and returns `BootAction::SystemReset` once.

### Block 3: Connecting `BootController` to `libDaisy` (`app.h` & `app.cpp`) {#block-3-app}

Following Spotykach's Pimpl-like separation (`app.h` exposes only `Application::Init()` and `Application::Loop()`, while `app.cpp` hides the hardware handles inside `AppImpl`), let's wire `DaisySeed`, `Switch`, and `BootController` together:

```cpp caption="app.h — Public Application interface matching root app.h"
#pragma once

#include "nocopy.h"

namespace spotykach {

class Application {
  public:
    Application() = default;
    ~Application() = default;

    void Init();
    void Loop();

  private:
    NOCOPY(Application)
};

} // namespace spotykach
```

Now look at how `AppImpl` in `app.cpp` initialises the STM32H750 clock tree and polls `seed::D2`:

```cpp caption="app.cpp — Initialising DaisySeed @ 480 MHz and polling D2 in the foreground loop"
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
```

- **`seed_.Init(true)`**: Passing `true` enables STM32H750 **Boost Mode** (480 MHz CPU clock instead of 400 MHz), configures the Memory Protection Unit (MPU) for non-cached `RAM_D2` DMA, and initialises external 64 MB SDRAM.
- **`boot_btn_.Init(seed::D2, 0, Switch::TYPE_MOMENTARY, Switch::POLARITY_INVERTED, GPIO::Pull::NOPULL)`**: Matches `src/hw/hardware.cpp` line 50 verbatim. The rear button pulls `seed::D2` to ground (`0V`) when pressed, so `Switch::POLARITY_INVERTED` maps `0V` → `Pressed() == true`, while an external pull-up resistor on the Spotykach PCB handles the idle `3.3V` state (`GPIO::Pull::NOPULL`).

### Block 4: Firmware Entrypoint & `bleeptools/libDaisy` USB Strings (`main.cpp`) {#block-4-main}

Finally, look at `main.cpp` (identical to the repository root `main.cpp`):

```cpp caption="main.cpp — Bare-metal entrypoint and external USB descriptor strings"
#include <daisy.h>
#include "app.h"

const char* USBD_MANUFACTURER_STRING = "Synthux";
const char* USBD_PRODUCT_STRING_HS   = "Spotykach";

static spotykach::Application app;

extern "C" int main(void) {
    app.Init();
    app.Loop();
}
```

- **The reason `USBD_MANUFACTURER_STRING` and `USBD_PRODUCT_STRING_HS` live in `main.cpp` is interesting**: Spotykach's `lib/libDaisy` submodule points to the `bleeptools/libDaisy` (`origin/sk`) fork, which replaced the hardcoded `"Electrosmith"` macros in `src/usbd/usbd_desc.c` with `extern const char*` declarations{{sidenote:If you omit these two `const char*` definitions in any Spotykach firmware target, the ARM linker (`arm-none-eabi-ld`) will fail with `undefined reference to USBD_MANUFACTURER_STRING` whenever USB is linked!}}.
- **`extern "C" int main(void)`**: Disables C++ symbol name-mangling on `main` so the C startup assembly routine (`Reset_Handler` in `startup_stm32h750xx.c`) can jump directly to `main`.

### Complete Companion Project Listing {#complete-listing}

Here is the complete `tests/test_boot.cpp` host verification suite and `Makefile` that tie our companion project together in `tutorial/apps/0001-boot-sram-and-heartbeat/`:

```cpp caption="tests/test_boot.cpp — Complete host C++17 unit test suite"
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
```

```makefile caption="Makefile — Dual-verification Makefile (ARM Cortex-M7 BOOT_SRAM + Host C++17 Tests)"
TARGET = spotykach_l01

CPP_STANDARD = -std=c++17

REPO_ROOT = ../../..
LIBDAISY_DIR = $(REPO_ROOT)/lib/libDaisy
DAISYSP_DIR = $(REPO_ROOT)/lib/DaisySP

APP_TYPE = BOOT_SRAM
LDSCRIPT = $(REPO_ROOT)/alt_sram.lds
BOOT_BIN = $(REPO_ROOT)/bootloader-spotykach-v2.bin

C_INCLUDES = -I.
LDFLAGS += -Wl,--no-warn-rwx-segments

CPP_SOURCES = \
	main.cpp \
	app.cpp

SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
include $(SYSTEM_FILES_DIR)/Makefile

HOST_CXX ?= c++
HOST_CXXFLAGS = -std=c++17 -Wall -Wextra -Werror -pedantic -I.

.PHONY: test
test:
	@mkdir -p $(BUILD_DIR)
	$(HOST_CXX) $(HOST_CXXFLAGS) tests/test_boot.cpp -o $(BUILD_DIR)/test_boot
	./$(BUILD_DIR)/test_boot
```

---

## 4. Interactive Practice & Dual Verification {#practice-and-verification}

:::exercise id="ex-0001" title="Interactive Lab: Complete the BootController & D2 Initialisation" badge="Skill Practice • C++17 & libDaisy"
Fill in the four missing tokens below from memory to complete the compile-time DFU threshold, the 3-second hold check, the falling-edge release check, and the active-low `seed::D2` switch polarity:

```cpp
class BootController {
  public:
    static {{blank:constexpr|Use the C++17 keyword that evaluates this constant at compile time.|constexpr|11}} uint32_t kDfuHoldThresholdMs = 3000;

    BootAction Update(bool is_pressed, uint32_t held_ms) {
        if (is_pressed && held_ms >= {{blank:kDfuHoldThresholdMs||3000|Compare held_ms against the 3000 ms compile-time threshold constant.|kDfuHoldThresholdMs|21}}) {
            was_pressed_ = is_pressed;
            return BootAction::EnterDfuBootloader;
        }
        if ({{blank:!is_pressed|Check that the button is no longer pressed on this tick.|!is_pressed|13}} && was_pressed_) {
            was_pressed_ = false;
            return BootAction::SystemReset;
        }
        was_pressed_ = is_pressed;
        return BootAction::None;
    }
  private:
    bool was_pressed_ = false;
};

// Inside AppImpl::Init():
boot_btn_.Init(seed::D2, 0, Switch::TYPE_MOMENTARY, Switch::{{blank:POLARITY_INVERTED|D2 is active-low (0V when pressed), so use inverted switch polarity.|POLARITY_INVERTED|19}}, GPIO::Pull::NOPULL);
```

:::prompts
hint: "Remember: `constexpr` evaluates constants at compile time, `kDfuHoldThresholdMs` is 3000 ms, a falling edge occurs when `!is_pressed && was_pressed_`, and active-low switches use `Switch::POLARITY_INVERTED`."
success: "Spot on! Your `BootController` and active-low `seed::D2` configuration match the production Spotykach firmware."
:::
:::

:::verify id="verify-0001" title="Verification Lab: Run Host Unit Tests & Compile the ARM BOOT_SRAM Binary" badge="Dual Verification • Host C++17 + ARM Cortex-M7"
Run both verification gates inside `tutorial/apps/0001-boot-sram-and-heartbeat/` and confirm your output matches the verified transcript below:

```bash caption="Run host C++17 unit tests and ARM Cortex-M7 firmware build"
make -C tutorial/apps/0001-boot-sram-and-heartbeat test
make -C tutorial/apps/0001-boot-sram-and-heartbeat
```

```text caption="Verified terminal output (Host C++17 test runner + STM32H750 memory table)"
[PASS] 0001-boot-sram-and-heartbeat: 4/4 test suites passed
...
Memory region         Used Size  Region Size  %age Used
           FLASH:           0 B       128 KB      0.00%
         DTCMRAM:         888 B       128 KB      0.68%
       SRAM_EXEC:       69272 B       256 KB     26.43%
            SRAM:       11744 B       256 KB      4.48%
          RAM_D2:         16 KB        32 KB     50.00%
```

- [ ] `make -C tutorial/apps/0001-boot-sram-and-heartbeat test` compiles with `-Wall -Wextra -Werror -pedantic` and prints `[PASS] 0001-boot-sram-and-heartbeat: 4/4 test suites passed`.
- [ ] `make -C tutorial/apps/0001-boot-sram-and-heartbeat` links `build/spotykach_l01.elf` and `build/spotykach_l01.bin` with `0 B` in `FLASH` and ~26.4% in `SRAM_EXEC`.
- [ ] *(Optional hardware check)* With Spotykach in DFU mode on the rear USB-C port, `make -C tutorial/apps/0001-boot-sram-and-heartbeat program-dfu` flashes the unit, blinks the Daisy Seed heartbeat LED at 2 Hz, and re-enters white-breathing DFU mode when the rear `D2` button is held for 3 seconds.
:::

:::quiz id="quiz-0001" title="Retrieval Practice: BOOT_SRAM, C++17 Idioms & D2 Rescue" badge="3 Questions • Equal-Length Options"
- question: "How does `APP_TYPE = BOOT_SRAM` with `alt_sram.lds` partition flash memory on Spotykach?"
  wrong_hint: "Check Section 1 and the STM32H750 memory table in the Hardware Architecture Cheat Sheet."
  options:
    - letter: "A"
      text: "Internal flash stores the bootloader while QSPI flash stores the application binary."
      correct: true
      explain: "Correct! The 128 KB internal flash (`0x08000000`) holds `bootloader-spotykach-v2.bin`, which copies the application from QSPI (`0x90040000`) into `SRAM_EXEC` (`0x24000000`) at boot."
    - letter: "B"
      text: "Internal flash stores the application binary while SDRAM stores the bootloader image."
      correct: false
      explain: "Not quite — SDRAM (`0xC0000000`) is volatile RAM, and the application binary exceeds the 128 KB internal flash."
    - letter: "C"
      text: "DTCMRAM stores the persistent application binary across hardware power cycles without QSPI."
      correct: false
      explain: "Incorrect — `DTCMRAM` (`0x20000000`) is volatile CPU data RAM that loses its contents when power is removed."
    - letter: "D"
      text: "RAM_D2 stores the entire executable code section and interrupt vector table directly."
      correct: false
      explain: "Incorrect — `RAM_D2` (`0x30000000`) is the 32 KB non-cached DMA buffer region (`DMA_BUFFER_MEM_SECTION`), whereas code runs from `SRAM_EXEC`."
- question: "What is the purpose of the `NOCOPY(T)` macro in Spotykach hardware classes?"
  wrong_hint: "Look at what `= delete;` does to the copy and move constructors in Block 1."
  options:
    - letter: "A"
      text: "It allocates the hardware object dynamically inside external 64 MB SDRAM."
      correct: false
      explain: "Incorrect — `DSY_SDRAM_BSS` places global arrays in external SDRAM; `NOCOPY(T)` only deletes special member functions."
    - letter: "B"
      text: "It prevents accidental copying or moving of unique hardware coordinator instances."
      correct: true
      explain: "Correct! Deleting the copy and move constructors/operators (`= delete`) guarantees at compile time that singleton hardware owners like `Application` and `AppImpl` are never duplicated."
    - letter: "C"
      text: "It forces the compiler to inline every public member function automatically."
      correct: false
      explain: "Incorrect — `NOCOPY(T)` deletes copy and move operations; it does not change function inlining."
    - letter: "D"
      text: "It registers the class instance with the USB DFU bootloader table."
      correct: false
      explain: "Incorrect — `NOCOPY(T)` is purely a compile-time C++11/17 class constraint."
- question: "How does `BootController::Update()` handle the rear `D2` boot button on Spotykach?"
  wrong_hint: "Compare what happens when `held_ms >= 3000` while pressed versus releasing before 3000 ms."
  options:
    - letter: "A"
      text: "Releasing before three seconds enters DFU while holding longer triggers normal reset."
      correct: false
      explain: "Incorrect — that is backwards! A short tap and release triggers `HAL_NVIC_SystemReset()`, whereas holding for 3 seconds enters DFU."
    - letter: "B"
      text: "Tapping D2 clears QSPI flash while holding D2 erases external SDRAM buffers."
      correct: false
      explain: "Incorrect — `D2` controls system reset (`HAL_NVIC_SystemReset()`) and jumping to the Daisy DFU bootloader (`System::ResetToBootloader()`)."
    - letter: "C"
      text: "Holding D2 for three seconds enters DFU while releasing earlier resets firmware."
      correct: true
      explain: "Correct! Holding `D2` for `>= 3000 ms` immediately returns `BootAction::EnterDfuBootloader` (`System::ResetToBootloader`), while releasing an earlier press returns `BootAction::SystemReset` (`HAL_NVIC_SystemReset`)."
    - letter: "D"
      text: "Pressing D2 immediately halts the CPU clock until external USB power disconnects."
      correct: false
      explain: "Incorrect — the foreground loop continues polling `boot_btn_.TimeHeldMs()` while `D2` is held."
:::

:::teacher-prompt
**Where to next?** Have a look at the compiled page and run the verification lab in `tutorial/apps/0001-boot-sram-and-heartbeat/`. Ask any questions you have about `alt_sram.lds`, C++17 `enum class` / `constexpr` / `NOCOPY`, or the `D2` bootloader rescue flow — or let me know when you're ready for **Lesson 0002: GPIO Gate/Clock I/O (Transistor Inversion) & Dual CD74HC165 Shift Register Scanning**!
:::
