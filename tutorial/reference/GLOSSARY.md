---
title: "Glossary of Spotykach Firmware Terms"
page_title: "Glossary — Spotykach Firmware Course"
nav_id: "glossary"
nav_label: "Glossary"
badge: "Mission: Custom Spotykach Firmware"
subtitle: "Canonical definitions used across all lessons and reference sheets. Designed for quick screen lookup and clean printing."
card:
  title: "**Glossary of Spotykach Firmware Terms**"
  summary: "Canonical definitions for STM32H750 memory domains, Daisy Seed peripherals, C++17 embedded idioms, and Spotykach real-time audio invariants."
---

## 1. Bootloader & STM32H750 Memory Architecture

**`BOOT_SRAM`**:
The Daisy Bootloader execution mode (`APP_TYPE = BOOT_SRAM`) in which the application binary is stored in external QSPI NOR Flash (`0x90040000`) and copied into internal AXI SRAM (`0x24000000`) by the bootloader before jumping to `Reset_Handler`.
_Avoid_: "Flash boot" (`BOOT_NONE` targets the 128 KB internal flash at `0x08000000`, which is too small for the Spotykach firmware and houses the Daisy Bootloader itself).

**`SRAM_EXEC`**:
The 256 KB partition of STM32H750 AXI SRAM starting at `0x24000000` (defined in `alt_sram.lds`) that holds the Spotykach interrupt vector table (`.isr_vector`), executable machine code (`.text`), and read-only constants (`.rodata`).
_Avoid_: "Code flash" (in `BOOT_SRAM` mode, instructions execute from AXI SRAM, not internal flash).

**`DTCMRAM`**:
The 128 KB Data Tightly Coupled Memory at `0x20000000` connected directly to the ARM Cortex-M7 core with zero wait states at 480 MHz, used in `alt_sram.lds` for the CPU stack (`_estack = 0x20020000`), initialised `.data`, and `.dtcmram_bss`. Because the system DMA controllers (`DMA1`/`DMA2`) cannot access `DTCMRAM`, peripheral DMA buffers must never be placed here.
_Avoid_: "Fast DMA RAM" (`DTCMRAM` is CPU-only; DMA buffers belong in `RAM_D2` via `DMA_BUFFER_MEM_SECTION`).

**`DMA_BUFFER_MEM_SECTION`**:
The `libDaisy` attribute macro (`__attribute__((section(".sram1_bss")))`) that places an array in the non-cached 32 KB `RAM_D2` (`SRAM1`) region at `0x30000000` so peripheral DMA transfers (`ADC`, `DAC`, `TIM3` WS2812 PWM) stay coherent without CPU D-cache stale reads.
_Avoid_: "Normal global array for DMA" (standard `.bss` lives in cached AXI SRAM, causing DMA cache incoherency).

**`DSY_SDRAM_BSS`**:
The `libDaisy` attribute macro (`__attribute__((section(".sdram_bss")))`) that places uninitialised global arrays in the 64 MB external SDRAM chip at `0xC0000000`, used by Spotykach for its dual-deck 60-second stereo audio loop buffers and `Flux` delay lines. Objects in `DSY_SDRAM_BSS` must not rely on dynamic C++ constructors because external SDRAM is initialised inside `Hardware::Init()` after `main()` starts.
_Avoid_: "Heap allocation" (`malloc`/`new` are never used for audio buffers in Spotykach).

## 2. C++17 Embedded Idioms

**`NOCOPY(T)`**:
The macro in `src/nocopy.h` that explicitly deletes the copy constructor, move constructor, copy-assignment operator, and move-assignment operator (`= delete`) of a hardware-owning class `T`, guaranteeing at compile time that singleton hardware coordinators (`Application`, `AppImpl`, `Core`) can never be accidentally duplicated.
_Avoid_: "Private empty copy constructor" (pre-C++11 style that delays errors to link time or allows member copies).

**`constexpr`**:
A C++ specifier declaring that a constant (`static constexpr size_t kBlockSize = 96;`) or pure function (`constexpr bool is_in_unit_range(float in)`) can be evaluated at compile time, placing zero runtime or RAM overhead on the microcontroller.
_Avoid_: `#define` macros for typed numerical constants.

**`enum class`**:
A strongly typed, scoped C++11/17 enumeration (such as `enum class Pad : uint8_t` or `enum class BootAction : uint8_t`) whose enumerators do not leak into the surrounding namespace and do not implicitly convert to integers without an explicit `static_cast`.
_Avoid_: Unscoped C `enum` when implicit integer conversion is undesirable.

## 3. Execution Contexts & Real-Time Audio

**Foreground Loop (`AppImpl::Loop`)**:
The non-real-time `while (true)` loop running in `main()` at lowest priority, responsible for blocking or variable-latency operations: `D2` boot button monitoring, `CD74HC165` shift register scanning, `I2C1` `MPR121` pad polling, `FatFS` SD card slot streaming, and USB CDC sample transfers.
_Avoid_: "Audio thread" or "UI interrupt".

**Audio Callback (`AudioCallback`)**:
The hard-real-time interrupt service routine (ISR) triggered by the `SAI1` DMA controller every 96 stereo frames at 48 kHz (every 2.0 ms), which must compute 96 stereo float samples in `[-1.0f, +1.0f]` without ever blocking or performing I2C/SD/USB I/O.
_Avoid_: "Main loop audio processing".
