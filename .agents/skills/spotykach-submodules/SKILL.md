---
name: spotykach-submodules
description: >-
  Reference guide and maintenance workflows for the Spotykach submodules (lib/DaisySP and lib/libDaisy).
  Use this skill whenever inspecting, updating, debugging, or modifying libDaisy or DaisySP in the Spotykach repository,
  or when working on Spotykach hardware drivers (WS2812 LEDs, MPR121 touch pads, MIDI, USB descriptors, QSPI, or timers)
  that depend on custom fork modifications in libDaisy.
---

# Spotykach Submodules Guide (`lib/DaisySP` & `lib/libDaisy`)

Spotykach relies on two Git submodules under `lib/` (configured in `.gitmodules`). Because `lib/libDaisy` points to a multi-layered custom fork with hardware-specific modifications required by the Spotykach firmware, care must be taken when updating submodules or touching hardware-facing drivers.

---

## 1. `lib/DaisySP`

* **Upstream URL:** `https://github.com/electro-smith/DaisySP.git` (Official Electro-Smith repo)
* **Pinned Commit:** `599511b740f8f3a9b8db72a0642aa45b8a23c3a3` (`V1.0.0-25-g599511b`)
* **Divergence from Upstream:**
  * Uses the official repository with **no custom fork or local patches**.
  * Sits 5 commits (1 PR) behind `origin/master` (`2c72eaf`, `V1.0.0-30-g2c72eaf`).
  * Those 5 newer commits in `origin/master` are exclusively from PR #166 (`fix/pitch_shift`), which simplified `PitchShifter`, fixed negative transposition, and allowed negative frequencies in `Phasor`.

---

## 2. `lib/libDaisy`

* **Configured URL:** `https://github.com/bleeptools/libDaisy.git`
* **Pinned Commit:** `dcd20e135f8ed21757711576b398d6a4c6526fba` (Branch: `origin/sk`)
* **Fork Lineage:**
  1. **Official Upstream (`electro-smith/libDaisy`):** Base is tag **`v8.0.0`** (`c6887c69`).
  2. **Infrasonic Audio Fork (`origin/infs-mods` at `da7019c5`):** Maintained by Nick Donaldson (Infrasonic Audio); adds hardware/driver capabilities across 41 files on top of `v8.0.0`.
  3. **Bleeptools Fork (`origin/sk` at `dcd20e13`):** Maintained by Vlad Lytvynenko (`bleeptools`); branches off `infs-mods` with Spotykach-specific changes.

### A. Spotykach-Specific Changes (`origin/infs-mods` → `origin/sk`)

Only two files differ between `origin/infs-mods` and `origin/sk`:

1. **MPR121 Capacitive Touch Filtering (`src/dev/mpr121.h`):**
   * Adjusts baseline noise/filter register initialization for Spotykach's capacitive touch pads:
     * `MPR121_NCLR`: `0x0E` → `0x14`
     * `MPR121_FDLR`: `0x00` → `0x80`
     * `MPR121_FDLF`: `0x00` → `0x80`
2. **External USB String Descriptors (`src/usbd/usbd_desc.c`):**
   * Replaces `#define USBD_MANUFACTURER_STRING "Electrosmith"` and `#define USBD_PRODUCT_STRING_HS "Daisy Seed External"` with `extern const char*` declarations:
     ```c
     extern const char* USBD_MANUFACTURER_STRING;
     extern const char* USBD_PRODUCT_STRING_HS;
     ```
   * Spotykach defines these symbols in `main.cpp` as `"Synthux"` and `"Spotykach"`.
   * **Warning:** Switching `lib/libDaisy` to vanilla `electro-smith/libDaisy` will break USB device identification or cause symbol/macro conflicts with `main.cpp`.

### B. Infrasonic Audio Modifications (`v8.0.0` → `origin/infs-mods`)

Key additions in `infs-mods` over official `libDaisy` `v8.0.0`:

* **Timer HAL Handle & HAL Pin Map (Critical for `src/hw/ws2812.cpp`):**
  * `src/per/tim.h`: Exposes `TimerHandle::GetHALHandle()`.
  * `src/util/hal_map.h`: Exposes `GetHALPort()`, `GetHALPin()`, and `GPIOClockEnable()`.
  * Spotykach's `infrasonic::Ws2812` driver (`src/hw/ws2812.cpp`) calls `timer.GetHALHandle()`, `GetHALPort()`, `GetHALPin()`, and `GPIOClockEnable()` to configure `TIM3`/`TIM4` PWM with `DMA2_Stream5`.
  * `src/per/tim.cpp`: Fixes the tick denominator in `DelayMs` / `GetMs` and adds proper tick-overflow microsecond timing.
* **StopwatchTimer (`src/util/stopwatch_timer.h`):**
  * Adds `daisy::StopwatchTimer`, used in `app.cpp` (`_log_timer`) when `DEBUG` is enabled.
* **MIDI Overhaul, Tx Queue & USB MIDI Host (`src/hid/midi.h`, `src/hid/midi_util.*`):**
  * Adds a MIDI transmit queue, raw data callback mode, a `ControlChange` Tx factory helper, and USB MIDI Host support.
* **QSPI Block Erase & Storage (`src/per/qspi.*`, `src/util/PersistentStorage.h`):**
  * Adds `EraseBlock()` / `EraseBlocks()` alongside sector erase, removes the hardcoded `-O3` pragma in `qspi.cpp`, and fixes slug length checks in `PersistentStorage`.
* **GPIO Interrupts (`src/per/gpio.*`):**
  * Adds hardware interrupt (`EXTI`) support and callback registration to `daisy::GPIO`.
* **Audio / SAI Precise Sample Rate (`src/hid/audio.*`, `src/per/sai.*`):**
  * Adds methods to calculate and query the exact hardware sample rate from SAI clock dividers.
* **Controls, UI & Utilities:**
  * `src/hid/ctrl.*`: Adds `flip` and `slew_seconds` arguments to `AnalogControl::InitBipolarCv()`.
  * `src/hid/parameter.*`: Adds ability to disable parameters.
  * `src/util/MappedValue.h`: Adds coarse/fine step customization to `MappedFloatValue`.
  * `src/hid/switch3.h`: Allows disabling internal pullups on `Switch3`.
  * `src/hid/rgb_led.*`: Adds sample rate argument to `RgbLed`.
  * `src/ui/ButtonMonitor.h`: Fixes initial button release spew on startup.
  * `src/util/Stack.h`: Fixes `Insert` bug and adds `Peek`, `FirstIndexOf`, and sorted insert methods.
  * `src/util/oled_fonts.h`: Adds 4 new OLED fonts and makes `FontDef` width non-const.
* **Logging & Build System (`src/sys/system.*`, `src/hid/logger_impl.*`, `core/Makefile`):**
  * Adds `System::IsDebuggerAttached()` so semihosting logs only transmit when a debugger is attached.
  * Adds rudimentary UART7 logging.
  * `core/Makefile`: Adds support for `.cc` sources, semihosting flags, and `USR_CFLAGS` / `USR_CXXFLAGS` / `USR_LDFLAGS`.

---

## 3. Maintenance & Verification Commands

When inspecting or updating submodules in this workspace:

1. **Check current submodule status:**
   ```sh
   git submodule status
   ```
2. **Diff `lib/libDaisy` against official `v8.0.0` merge-base (`c6887c69`):**
   ```sh
   git -C lib/libDaisy diff --stat c6887c69..HEAD
   ```
3. **Diff Spotykach branch (`origin/sk`) against Infrasonic base (`origin/infs-mods`):**
   ```sh
   git -C lib/libDaisy diff origin/infs-mods..origin/sk
   ```
4. **Rebuild libraries and firmware after any submodule change:**
   ```sh
   make -j8 libs
   make -j8
   ```
