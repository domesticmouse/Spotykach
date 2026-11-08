# Mission: Building Custom Spotykach Firmware from Scratch

## Why
Build a complete, custom bare-metal C++17 firmware for the Synthux Academy Spotykach hardware from the ground up, using the official Spotykach repository as the authoritative source of truth. Starting from zero assumed C++17, STM32H7 embedded hardware, or real-time DSP background, you will progressively bring up every hardware peripheral and real-time audio subsystem until you can author, verify, and flash production-grade dual-deck looper and DSP firmware onto physical Spotykach hardware.

## Success looks like
- Compile and flash (`make program-dfu`) a standalone Spotykach firmware binary (`APP_TYPE = BOOT_SRAM` with `alt_sram.lds`) that enumerates over the rear USB-C port as `"Synthux"` / `"Spotykach"` and handles the `D2` boot button reset and 3-second DFU bootloader hold.
- Bring up and verify all Spotykach control surface peripherals from scratch: `CD74HC165` dual 8-bit shift registers (`D27`/`D26`/`D7`), `MPR121` 12-pad capacitive touch controller over `I2C1` (`D11`/`D12`), 83 `WS2812` RGB LEDs driven by `TIM3` PWM + `DMA2_Stream5` (`D17`), and the 9-channel oversampled ADC with dual 8-channel analog multiplexers (`A9`/`A10`, `D8`–`D10`) plus 7 bipolar CV inputs.
- Architect and verify a lock-free 48 kHz / 96-sample stereo audio callback (`AudioCallback`), a 12-bit dual-channel DMA DAC modulation output (`DACCallback`), and a 500 Hz periodic timer ISR (`TIM5`), strictly separating real-time ISR execution from main-loop hardware I/O.
- Implement the 64 MB external SDRAM (`DSY_SDRAM_BSS`) dual-deck audio engine (`Deck`, `Generator`, 3-voice slice/granular/tape playback, `Grit` overdrive/bitcrusher/DJ filter, and `Flux` stereo delay) alongside `QSPI` flash calibration and `FatFS` SD card 6x6 WAV slot storage.
- Back every lesson's companion firmware in `tutorial/apps/<NNNN-slug>/` with dual verification: an ARM Cortex-M7 firmware build (`spotykach_lNN.elf` / `.bin`) and a deterministic host C++17 unit test suite (`make test`) that passes with zero warnings (`-Wall -Wextra -Werror`).

## Constraints
- **Beginner-friendly C++17, embedded, and DSP explanations**: Every C++17 idiom (`constexpr`, `enum class`, `std::clamp`, deleted copy/move constructors via `NOCOPY`, references vs. pointers), STM32H7 memory region (`SRAM_EXEC`, `DTCMRAM`, `DMA_BUFFER_MEM_SECTION`, `DSY_SDRAM_BSS`), and DSP formula is unpacked block-by-block from first principles.
- **Dual verification in every lesson**: Every companion app under `tutorial/apps/<NNNN-slug>/` compiles both for the STM32H750 target (`arm-none-eabi-g++`) and for the host test runner (`c++ -std=c++17 -Wall -Wextra -Werror`) so progress is 100% verifiable with or without a Spotykach unit plugged in.
- **Source-of-truth fidelity**: Pinouts, memory layouts, register configurations, and submodule contracts (`bleeptools/libDaisy` at `origin/sk` and `electro-smith/DaisySP`) match the production Spotykach codebase.

## Out of scope
- Designing custom PCBs or modifying the physical Spotykach schematic.
- Modifying the upstream STM32 HAL or FreeRTOS (Spotykach runs bare-metal foreground/ISR execution without an RTOS).
- Building desktop DAW plugins (VST/AU) unrelated to the Spotykach hardware platform.
