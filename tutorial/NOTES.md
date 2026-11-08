# Course Working Notes & Curriculum Roadmap

## Learner Profile & Preferences
- **Goal**: Build a complete custom Spotykach firmware from scratch, using this repository as the authoritative source of truth.
- **Starting Point**: Beginner to C++17, embedded hardware, and audio DSP. Every lesson must unpack C++17 syntax and idioms (`namespace`, `class`, `constexpr`, `uint32_t`, `enum class`, deleted copy/move constructors, references, callbacks) alongside STM32H7 hardware architecture and DSP concepts.
- **Verification Strategy**: Dual verification in every lesson (`tutorial/apps/<NNNN-slug>/`):
  1. **ARM Cortex-M7 Firmware Build (`make`)**: Compiles against `../../lib/libDaisy`, `../../lib/DaisySP`, and `../../alt_sram.lds` (`APP_TYPE = BOOT_SRAM`) to produce a real, flashable `.elf` and `.bin` (ready for `make program-dfu` on physical Spotykach hardware).
  2. **Deterministic Host C++17 Unit Test Suite (`make test`)**: Compiles pure C++17 hardware-abstracted logic/DSP controllers on the host (`c++ -std=c++17 -Wall -Wextra -Werror`) and executes automated assertions so every lesson verifies deterministically with or without physical hardware attached.

## Curriculum Roadmap (Progressive Bring-Up from Scratch)

1. **Lesson 0001 — `0001-boot-sram-and-heartbeat`**: *BOOT_SRAM Memory Layout, C++17 Application Lifecycle & Bootloader Rescue*
   - Unpack how Spotykach boots on the Daisy Seed (`STM32H750IBK6`): why the firmware exceeds 128 KB internal flash, how `APP_TYPE = BOOT_SRAM` and `alt_sram.lds` load code from QSPI flash (`0x90040000`) into fast `SRAM_EXEC` (`0x24000000`), and why `main.cpp` defines `USBD_MANUFACTURER_STRING` (`"Synthux"`) and `USBD_PRODUCT_STRING_HS` (`"Spotykach"`) for the `bleeptools/libDaisy` fork.
   - Learn essential C++17 building blocks used in `main.cpp`, `app.h`, and `src/hw/hardware.cpp`: `namespace`, `class`, `constexpr`, fixed-width integers (`uint32_t`), `enum class`, and the `NOCOPY` deleted copy/move idiom.
   - Build and test a hardware-abstracted `BootController` modelling Spotykach's `D2` boot button safety mechanism (tap-and-release triggers `HAL_NVIC_SystemReset()`, holding `>= 3000 ms` triggers `System::ResetToBootloader(DAISY_INFINITE_TIMEOUT)` so you can never brick your board), wired into a real `BOOT_SRAM` firmware binary.
2. **Lesson 0002 — `0002-gpio-gates-and-shift-registers`**: *GPIO Gate/Clock I/O (Transistor Inversion) & Dual CD74HC165 Shift Register Scanning*
   - Bring up Spotykach's digital inputs and outputs: `Clock In` (`D3`), `Gate In A/B` (`D1`/`D0`), `Gate Out A/B` (`D31`/`D32`), and why NPN transistor input buffers invert external signals (`!gpio.Read()`).
   - Implement and test the `ShiftRegister165` driver (`D26` CLK, `D27` DATA, `D7` LOAD) reading 16 switch bits across two daisy-chained 74HC165 chips.
3. **Lesson 0003 — `0003-mpr121-capacitive-touch-pads`**: *I2C1 Capacitive Touch Pads (`MPR121`) & Edge-Triggered Pad Events*
   - Configure `Mpr121I2C` on `I2C1` (`D11` SCL, `D12` SDA @ 400 kHz), understand the `bleeptools/libDaisy` noise/filter tuning (`NCLR`/`FDLR`/`FDLF`), and build the 12-pad bitmask edge detector (`Pad::PlayA`..`Pad::Alt`) with `std::function` callbacks.
4. **Lesson 0004 — `0004-ws2812-leds-and-tim5-isr`**: *WS2812 83-LED Chain (`TIM3` PWM + `DMA2`) & `TIM5` Periodic Interrupt Scheduling*
   - Drive the 83 addressable RGB LEDs (`LedId` topology, two 32-LED rings, `LEDRing` renderer) using `TIM3` PWM + `DMA2_Stream5` in non-cached `DMA_BUFFER_MEM_SECTION` (`SRAM1`), scheduled at ~125 Hz from the `TIM5` periodic interrupt.
5. **Lesson 0005 — `0005-muxed-adcs-cv-and-soft-takeover`**: *Dual 8-Channel Multiplexed ADCs, Bipolar CV Calibration & Soft-Takeover (`MValue`)*
   - Configure the 9-channel oversampled ADC (`OVS_32`) scanning 15 pots/sliders across two 8-channel `CD4051` muxes (`A9`/`A10`, `D8`–`D10`) and 7 bipolar CV jacks, inset scaling (`0.08`..`0.92` -> `0.0`..`1.0`), 1V/3V V/Oct calibration, and `MValue` soft-takeover for secondary Alt parameters.
6. **Lesson 0006 — `0006-realtime-audio-and-dac-modulation`**: *48 kHz SAI Audio Callback, Lock-Free `IrqQueue` & 12-Bit Dual-Channel DMA DAC LFOs*
   - Bring up the 48 kHz / 96-sample `AudioCallback`, the 12-bit DMA DAC modulation outputs (`__USAT` saturation), and the `Modulation` LFO/envelope follower subsystem while enforcing strict Execution Context Separation.
7. **Lesson 0007 — `0007-sdram-buffer-and-dual-deck-looper`**: *64 MB External SDRAM (`DSY_SDRAM_BSS`), Dual-Deck Looper & Crossfader*
   - Allocate 60-second stereo 48 kHz float loop buffers in external SDRAM (`0xC0000000`), implement lock-free `Deck` record/play/dub state transitions, and wire the Deck A/B crossfader.
8. **Lesson 0008 — `0008-granular-slice-tape-generator`**: *3-Voice Granular, Slice & Tape Playback Engine (`Generator`) & Envelope Windowing*
   - Build the 3-voice window-overlapped playback engine supporting One-Shot, Slice, Granular, and Repeat modes, pitch shifting (`V/Oct` + semitone quantisation), and scrubbed playback position.
9. **Lesson 0009 — `0009-grit-and-flux-stereo-fx`**: *Per-Deck Stereo DSP Effects: `Grit` (Overdrive/Bitcrush/DJ Filter) & `Flux` (Stereo Tape Echo)*
   - Implement Spotykach's two per-deck effects chains using `daisysp::Svf`, polynomial soft-clipping, sample-rate/bit-depth decimation, and SDRAM-backed stereo delay lines with feedback filtering.
10. **Lesson 0010 — `0010-clock-sequencer-sd-and-usb-transfer`**: *48 PPQN Clock, 128-Step Sequencer, FatFS SD WAV Slots & USB Transfer Protocol*
    - Complete the custom firmware with the 48 PPQN internal/external/MIDI clock driver, 128-step motion/slice sequencer, QSPI `PersistentStorage`, FatFS `/SK/<tape>/<slot>.wav` 32-bit float WAV loader/writer, and the CRC-32 USB MIDI-to-CDC sample transfer service.
