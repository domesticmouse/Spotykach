# Spotykach
The official firmware for the [Spotykach](https://synthux.academy/store/spotykach).

## Setup

Clone the repo recursively or run `git submodule update --init --recursive`
to update submodules (libDaisy + DaisySP)

Note that the ws2812 driver requires a slight modification to libDaisy,
as such the libDaisy submodule commit ref points at a specific branch within
the bleeptools fork (which is based on Infrasonic Audio fork), containing a few other modifications as well, namely
within the MIDI and mpr121 classes.

## Compiling the Firmware

First you must build the libraries. For convenience there is a target in the `Makefile` for this, so you
simply need to run the following command from a terminal (in the root directory of this repository):

`make -j8 libs`

_Note: The `-j8` flag runs make with 8 parallel jobs, feel free to change the number. It works best
if you use the number of cores (including hyperthread cores) on your machine._

Then, build the actual firmware code:

`make -j8`

If successful the compiled binaries will end up in the `build/` directory along with many other
intermediate build files:

```
spotykach.bin
spotykach.elf
```

The `.elf` file is mainly used for debugging. The `.bin` file is the one that the DFU
utilities will flash onto the Seed.

## Flashing the Firmware

The bootloader version used in this project enables USB DFU firmware updating from the _external_
USB port - i.e. the USB-C port on the rear of the main PCB, NOT the one on the Seed. Application
firmware can only be flashed using the USB-C port.

1. Compile the firmware using the steps above
2. Connect the USB-C connector on the main PCB to the computer (ensure the cable is not power-only)
3. Hold the `Reset` button on the back of the unit for ~3 seconds. The leds under bottom pads going to "breathe" in white.
4. Run the command `make program-dfu` from a terminal

Once finished, the device will automatically boot the new firmware.
This can "brick" (temporarily) the device and require reinstallation of either the
bootloader, the firmware binary, or both.

---

# Spotykach Blueprint

## System Overview
Spotykach is a dual-deck hardware audio looper, granular/slice/tape processor, and performance instrument built on the Electro-Smith Daisy Seed (STM32H7, `APP_TYPE = BOOT_SRAM` using `alt_sram.lds` and `bootloader-spotykach-v2.bin`). The system comprises bare-metal C++17 firmware (`src/`) running a 48 kHz / 96-sample audio engine backed by 64 MB of external SDRAM, QSPI flash calibration storage, and FatFS SD card sample slots, alongside a browser-based Web MIDI / Web Serial sample transfer and configuration client (`web/`).

## Local Interface & Invariants
- **Entrypoint & USB Descriptors (`main.cpp`)**:
  - `[main.cpp:main]`: Instantiates static `spotykach::Application app`, calls `app.Init()`, and enters `app.Loop()`.
  - `[main.cpp:USBD_MANUFACTURER_STRING]` (`"Synthux"`) & `[main.cpp:USBD_PRODUCT_STRING_HS]` (`"Spotykach"`): External USB string descriptors consumed by the `bleeptools/libDaisy` (`origin/sk`) USB device stack.
- **Application Lifecycle & Real-Time Callbacks (`app.h`, `app.cpp`, `meter.h`)**:
  - `[app.h:spotykach::Application]` & `[app.cpp:spotykach::AppImpl]`: Top-level coordinator owning `Core`, `CoreUI`, `Hardware`, `Settings`, `Storage`, and `USBTransfer`.
  - `[app.cpp:AudioCallback]` / `[app.cpp:spotykach::AppImpl::ProcessAudio]`: 48 kHz (`block_size = 96`) SAI audio callback. Outputs zeroed buffers while `USBTransfer::is_active()` is true; otherwise runs `Hardware::ProcessAnalogControls()`, `CoreUI::tick()`, `CoreUI::read_cv()`, and `Core::process()`.
  - `[app.cpp:DACCallback]`: 12-bit dual-channel DMA DAC callback driving Deck A and Deck B modulation outputs (`Core::mod(Deck::A/B).process`) and updating LFO LED brightness (`CoreUI::set_lfo`).
  - `[app.cpp:StartT5Callback]` & `[app.cpp:T5Callback]`: Configures `TIM_5` periodic interrupt (`call_freq_hz = 250`, period `System::GetPClk2Freq() / call_freq_hz`, resulting in a 500 Hz ISR on STM32H7 APB timer clocks) to poll gate inputs (`CoreUI::process_gate_in()`), prepare audio engine state (`Core::prepare()`), and flush WS2812 LED frames (`CoreUI::render_leds()`) every 4th tick (~125 Hz).
  - `[app.cpp:spotykach::AppImpl::Loop]`: Main foreground loop. Reboots into the Daisy bootloader (`System::ResetToBootloader(System::BootloaderMode::DAISY_INFINITE_TIMEOUT)`) when the boot button is held for `>= 3000` ms; services `USBTransfer::process()` exclusively when active, or runs `CoreUI::process()`, `Storage::process()`, and `USBTransfer::check_request()` (when `DEBUG` is not defined).
  - `[meter.h:Meter]`: Singleton wrapper (`Meter::cpu().load`) around `daisy::CpuLoadMeter`, active when `METER` is defined.

## Subdirectories & System Boundaries
- `src`: [`./src/README.md`](./src/README.md) - Firmware source root containing shared DSP/logging headers (`common.h`, `expose.h`, `nocopy.h`) and the five firmware subsystems:
  - `src/core`: [`./src/core/README.md`](./src/core/README.md) - Dual-deck real-time DSP audio engine, 3-voice granular/slice/tape generator, 48 PPQN clock synchronization driver, 128-step sequencer, and LFO/follower modulation subsystem.
  - `src/core/fx`: [`./src/core/fx/README.md`](./src/core/fx/README.md) - Per-deck stereo audio effects chain (`Grit` insert overdrive/bitcrusher/DJ filter and `Flux` stereo tape echo delay).
  - `src/hw`: [`./src/hw/README.md`](./src/hw/README.md) - Daisy Seed board support package, external SDRAM buffer pool (`SDRAMBuffer`), SDMMC/FatFS card driver (`Card`), CD74HC165 shift registers, MPR121 touch pads, and WS2812 PWM+DMA LED driver.
  - `src/memory`: [`./src/memory/README.md`](./src/memory/README.md) - QSPI flash calibration storage (`Settings`), SD card 6x6 tape/slot management (`Storage`, `DeckStorage`), and RIFF/WAVE header and cue-point parser/writer.
  - `src/transfer`: [`./src/transfer/README.md`](./src/transfer/README.md) - Firmware side of the Spotykach USB transfer protocol (`1.2`), handling USB MIDI-to-CDC mode switching, CRC-32 packet framing (`Link`), and SD card file/slot operations (`Service`, `USBTransfer`).
  - `src/ui`: [`./src/ui/README.md`](./src/ui/README.md) - Control surface coordinator (`CoreUI`), multiplexed pot soft-takeover (`MValue`), 32-LED ring renderer (`LEDRing`), CV/V-Oct calibrator (`Calibrator`), and UART/USB MIDI handler (`CoreMIDI`).
- `web`: [`./web/README.md`](./web/README.md) - Browser-side packages for communicating with Spotykach hardware over Web MIDI and Web Serial:
  - `web/spotykach-transfer`: [`./web/spotykach-transfer/README.md`](./web/spotykach-transfer/README.md) - Host side of the Spotykach USB sample transfer protocol (`@synthuxacademy/spotykach-transfer`), providing Web MIDI SysEx mode switching, Web Serial slot/config/file operations, and 48 kHz stereo 32-bit float WAV preparation.

## Global Invariants
- **Execution Context Separation**: Blocking hardware I/O (SDMMC/FatFS in `Card`/`Storage`, I2C MPR121 polling in `Hardware::ProcessPads`, GPIO shift register scanning in `Hardware::ProcessDigitalControls`, and USB CDC transfer servicing in `USBTransfer::process`) must only execute on the main loop (`AppImpl::Loop`). The 48 kHz SAI `AudioCallback` must remain strictly non-blocking, communicating with foreground/ISR threads via `IrqQueue` (`Deck::_commands`).
- **USB Transfer Exclusivity**: Entering USB transfer mode (`USBTransfer::_enter`) requires neither deck to be recording and `Storage::begin_transfer()` to succeed from the main loop (`Card::State::idle`). While `USBTransfer::is_active()` is true, `AudioCallback` outputs silence, `T5Callback` skips gate/deck preparation, the external USB port switches from USB MIDI to USB CDC, and pad inputs are ignored except `PlayA`/`PlayB` (which exit transfer mode).
- **Audio & Storage Format Contract**: Both firmware (`src/memory/wav.cpp`, `src/hw/card.cpp`, `src/transfer/service.cpp`) and host (`web/spotykach-transfer/index.js`) enforce 48,000 Hz, 2-channel stereo, 32-bit IEEE 754 float (`AudioFormat = 3`) WAV files across 6 tapes (`B`, `G`, `P`, `R`, `T`, `Y`) × 6 slots (`1`–`6`) under `/SK/<tape>/<slot>.wav`, with SD reads aligned to 512-byte sectors (`Card::kSectorSize`) and non-finite (`Inf`/`NaN`) float samples scrubbed to `0.0f` on load.
- **Custom Submodule Requirements**: Compiling the firmware requires the `bleeptools/libDaisy` (`origin/sk`) submodule fork, which exposes `TimerHandle::GetHALHandle()` and `hal_map.h` helpers for `src/hw/ws2812.cpp`, `extern` USB descriptor strings for `main.cpp`, and tuned `Mpr121` filter registers for `src/hw/hardware.cpp`.

## Global Side Effects
- **Hardware Peripherals & External Memory**: Initializes and drives STM32H7 SAI audio, dual-channel 12-bit DMA DAC, 9-channel oversampled ADC (with two 8-channel muxes), `TIM3` PWM + `DMA2_Stream5` (83 WS2812 LEDs), `TIM5` periodic interrupt, `I2C1` (MPR121 touch controller), `USART1` MIDI, external USB FS (dynamically switching between USB MIDI and USB CDC), 64 MB external SDRAM (`DSY_SDRAM_BSS`), QSPI flash (`daisy::PersistentStorage`), and 1-bit SDMMC FatFS SD card storage.
- **Bootloader & System Reset**: Releasing the boot button (`D2`) triggers `HAL_NVIC_SystemReset()`; holding the boot button for `>= 3000` ms invokes `System::ResetToBootloader(System::BootloaderMode::DAISY_INFINITE_TIMEOUT)`.

## System Verification
- Run: `make -j8 libs && make -j8 && ./tests/transfer/run.sh`
