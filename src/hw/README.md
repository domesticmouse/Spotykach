# Hardware Abstraction & Drivers (`src/hw`)

## Overview
The `src/hw` package provides the board support package (BSP), external SDRAM buffer pool, SDMMC/FatFS card driver, and low-level peripheral drivers for the Spotykach firmware running on the Electro-Smith Daisy Seed (STM32H7). It encapsulates initialization and runtime servicing of multiplexed analog potentiometers/faders, bipolar CV inputs, inverting transistor gate/clock GPIOs, dual-channel 12-bit DAC modulation outputs, UART/USB MIDI transports, daisy-chained CD74HC165 parallel-in/serial-out shift registers for mechanical switches, MPR121 I2C capacitive touch pads, WS2812 addressable RGB LEDs driven via hardware timer PWM and DMA, and bare-metal newlib syscall stubs.

## Interface
- **`spotykach::Hardware`** (`[hardware.h:Hardware]`, `[hardware.cpp:Hardware::Init]`):
  - **Constants & Buffers**:
    - `kDacBufSize` (`[hardware.h:kDacBufSize]`): `48` samples per channel per DMA callback block.
    - `dac_buf` (`[hardware.h:dac_buf]`): `uint16_t DMA_BUFFER_MEM_SECTION dac_buf[2][kDacBufSize]` DMA buffer for dual-channel DAC output.
    - `Hardware::kNumLedsPerRing` (`32`), `Hardware::kNumLeds` (`LED_LAST` = `83`), `Hardware::kNumAnalogControls` (`CTRL_LAST` = `15`), `Hardware::kNumCVInputs` (`CV_LAST` = `7`).
  - **Enumerations**:
    - `Hardware::LedId` (`[hardware.h:Hardware::LedId]`): Chain order indices for all 83 WS2812 LEDs (`LED_SPOTY_PAD`, `LED_ALT_A`, `LED_PLAY_A`, `LED_REV_A`, `LED_RING_A`..`LED_RING_A_LAST`, `LED_GRIT_A`, `LED_FLUX_A`, `LED_GATE_IN_A`, `LED_CYCLE_A`, `LED_MODE_CENTER`, `LED_MODE_LEFT`, `LED_CLOCK_IN`, `LED_MODE_RIGHT`, `LED_CYCLE_B`, `LED_GATE_IN_B`, `LED_FLUX_B`, `LED_GRIT_B`, `LED_RING_B`..`LED_RING_B_LAST`, `LED_REV_B`, `LED_PLAY_B`, `LED_FADER_B`, `LED_FADER_A`, `LED_ALT_B`, `LED_LAST`).
    - `Hardware::AnalogControlId` (`[hardware.h:Hardware::AnalogControlId]`): Multiplexed knob and slider channels (`CTRL_SOS_A`, `CTRL_MODFREQ_A`, `CTRL_MOD_AMT_A`, `CTRL_SIZE_A`, `CTRL_PITCH_A`, `CTRL_POS_A`, `CTRL_ENV_A`, `CTRL_SOS_B`, `CTRL_MODFREQ_B`, `CTRL_MOD_AMT_B`, `CTRL_SIZE_B`, `CTRL_PITCH_B`, `CTRL_POS_B`, `CTRL_ENV_B`, `CTRL_CROSSFADE`, `CTRL_LAST`).
    - `Hardware::Pad` (`[hardware.h:Hardware::Pad]`): MPR121 electrode indices (`PlayA = 0`, `RevA = 1`, `GritA = 2`, `FluxA = 3`, `SeqA = 4`, `SeqB = 5`, `FluxB = 6`, `GritB = 7`, `RevB = 8`, `PlayB = 9`, `Spot = 10`, `Alt = 11`).
    - `Hardware::CvInputId` (`[hardware.h:Hardware::CvInputId]`): Bipolar CV input channels (`CV_SIZE_POS_A`, `CV_MIX_A`, `CV_V_OCT_A`, `CV_CROSSFADE`, `CV_SIZE_POS_B`, `CV_MIX_B`, `CV_V_OCT_B`, `CV_LAST`).
  - **Lifecycle, Accessors & Peripheral Handles**:
    - `Init(float sr, size_t blocksize)`, `StartAdcs()`, `ProcessAnalogControls()`, `ProcessDigitalControls()`, `ProcessPads()`, `StartUsbMidi()`, `StopUsbMidi()`, `StartDAC(...)`, `SetOnTouch(...)`, `SetOnRelease(...)`, `GetAnalogControlValue(...)`, `GetPotValue(...)`, `GetControlVoltageValue(...)`, `GetClockInputState()`, `GetGateInputAState()`, `GetGateInputBState()`, `SetGateOutA(bool)`, `SetGateOutB(bool)`, `GetBootButtonHeldTime()`, `GetShiftRegState(uint8_t)`, `GetMpr121TouchStates()`.
    - Public handles: `seed` (`daisy::DaisySeed`), `leds` (`infrasonic::Ws2812`), `midi_uart` (`daisy::MidiUartHandler`), `midi_usb` (`daisy::MidiUsbHandler`).
- **`spotykach::SDRAMBuffer`** (`[buffer.sdram.h:SDRAMBuffer]`, `[buffer.sdram.cpp:SDRAMBuffer::pool]`):
  - Constants: `kSampleRate` (`48000`), `kDecksCount` (`2`), `kBuffersPerDeckCount` (`1`), `kChannelsCount` (`2`), `kSourceMaxSeconds` (`42`).
  - Singleton pool (`SDRAMBuffer::pool()`) providing `DSY_SDRAM_BSS` buffers: `sourceBuffer()`, `sourceBufferSize()`, `delayBuffer()`, `detectorBuffer()`, `track_buffer_a()`, `track_buffer_b()`, `slices_a()`, `slices_b()`, `card_buffer()`.
- **`spotykach::Card`** (`[card.h:Card]`, `[card.cpp:Card]`):
  - Constants & types: `kChunk` (`32768`), `kSectorSize` (`512`), `Card::State` (`unmounted`, `mounting`, `idle`, `read_file`, `write_file`, `write_audio`, `read_audio`, `transfer`, `failed`), `Card::AudioData`.
  - Card & audio streaming methods: `init(uint8_t*)`, `recognize()`, `mount()`, `unmount()`, `state()`, `progress()`, `file_exists(const char*)`, `init_read_audio(AudioData)`, `read_audio()`, `size_audio()`, `init_write_audio(AudioData)`, `write_audio()`, `write_file(...)`, `read_file(...)`, `notify_finish_processing()`, `cancel()`.
  - USB transfer mode methods (`State::transfer`): `begin_transfer()`, `end_transfer()`, `buffer()`, `stat(...)`, `open_read(...)`, `open_write(...)`, `read(...)`, `write(...)`, `seek(...)`, `read_at(...)`, `tell()`, `close()`, `remove(...)`, `rename(...)`, `make_dir(...)`, `space_kib(...)`.
- **`infrasonic::ShiftRegister165`** (`[sr_165.h:ShiftRegister165]`, `[sr_165.h:kMaxSr165DaisyChain]`):
  - `ShiftRegister165::Config` (`data`, `clk`, `load`), `Init(const Config&, size_t)`, `Update()`, `Read(size_t)`.
- **`infrasonic::Ws2812`** (`[ws2812.h:Ws2812]`, `[ws2812.cpp:Ws2812::Init]`):
  - `Ws2812::kMaxNumLEDs` (`128`), `Ws2812::Config`, `Init(const Config&)`, `SetGamma(float)`, `SetBrightnessLimit(float)`, `Set(...)`, `Fill(...)`, `Clear()`, `Show()`.
  - Interrupt callbacks: `[ws2812.cpp:DMA2_Stream5_IRQHandler]`, `[ws2812.cpp:HAL_TIM_PWM_PulseFinishedCallback]`, `[ws2812.cpp:DMAMUX1_OVR_IRQHandler]`.
- **Newlib Syscall Stubs** (`[syscalls.cpp:_close]`, `[syscalls.cpp:_fstat]`, `[syscalls.cpp:_isatty]`, `[syscalls.cpp:_lseek]`, `[syscalls.cpp:_read]`, `[syscalls.cpp:_write]`, `[syscalls.cpp:_kill]`, `[syscalls.cpp:_getpid]`):
  - Strong `extern "C"` definitions silencing `-lnosys` linker warnings on bare metal.

## Invariants
- **Audio-Callback vs. Main-Loop Execution**: `Hardware::ProcessAnalogControls` (`[hardware.cpp:Hardware::ProcessAnalogControls]`) is non-blocking and must be invoked at the audio block rate (`sr / blocksize`) inside the audio callback so the `0.02s` smoothing filters remain accurate. `Hardware::ProcessDigitalControls` (`[hardware.cpp:Hardware::ProcessDigitalControls]`) and `Hardware::ProcessPads` (`[hardware.cpp:Hardware::ProcessPads]`) perform blocking GPIO delays and I2C transactions and must never be called from the audio callback.
- **SDRAM Pool Allocation Counts**: `[buffer.sdram.cpp:SDRAMBuffer::sourceBuffer]` asserts `_providedSourceBufCount < kSrcBufsCount` (`3`), `[buffer.sdram.cpp:SDRAMBuffer::detectorBuffer]` asserts `_providedDetectorBufCount < kDetectorBufsCount` (`4`), and `[buffer.sdram.cpp:SDRAMBuffer::delayBuffer]` asserts `_providedDelayBufCount < kDelayBufsCount` (`4`).
- **SDMMC DMA Sector Alignment & NaN Scrubbing**: `[card.cpp:Card::_read_from]` aligns SD reads down to a `kSectorSize` (`512`-byte) boundary into the 32-byte-aligned `_buffer` and skips the leading offset so FatFS SDMMC DMA never receives an unaligned destination address. `[card.cpp:Card::_scrub_audio]` bitwise-checks loaded 32-bit floats (`(bits & 0x7F800000u) == 0x7F800000u`, safe under `-ffast-math`) and zeroes any `Inf`/`NaN` samples before DSP playback.
- **Card State Exclusivity**: `Card::init_read_audio`, `Card::init_write_audio`, `Card::read_file`, `Card::write_file`, and `Card::begin_transfer` require `_state == State::idle`; raw transfer operations (`stat`, `open_read`, `open_write`, `remove`, `rename`, `make_dir`, `space_kib`) require `_state == State::transfer`.
- **Inverting Transistor Gate/Clock Inputs**: `GetClockInputState`, `GetGateInputAState`, and `GetGateInputBState` (`[hardware.cpp:Hardware::GetClockInputState]`, `[hardware.cpp:Hardware::GetGateInputAState]`, `[hardware.cpp:Hardware::GetGateInputBState]`) invert raw GPIO reads (`!pin.Read()`) to account for the hardware's inverting transistor input buffers.
- **Potentiometer Inset Scaling**: `GetAnalogControlValue` (`[hardware.cpp:Hardware::GetAnalogControlValue]`) maps raw ADC readings from `[0.08, 0.92]` to `[0.0, 1.0]` and clamps to `[0.0, 1.0]`.
- **Single-Instance WS2812 Driver & Custom `libDaisy` Dependency**: `infrasonic::Ws2812` (`[ws2812.h:Ws2812]`, `[ws2812.cpp:impl]`) uses a single static `Ws2812::Impl` instance and a shared `DMA_BUFFER_MEM_SECTION pwm_out_buf` supporting at most `128` LEDs on `TIM_3` (`CH1`–`CH4`) or `TIM_4` (`CH1`–`CH3`) via `DMA2_Stream5`. It requires the custom `lib/libDaisy` fork exposing `TimerHandle::GetHALHandle()`, `GetHALPort()`, `GetHALPin()`, and `GPIOClockEnable()` (`[ws2812.cpp:Ws2812::Impl::initPwmDma]`).

## Side Effects
- **STM32H7 Peripheral & Pin Initialization**: `Hardware::Init` (`[hardware.cpp:Hardware::Init]`) initializes `DaisySeed` (with boost enabled), configures GPIO pins (`D0`–`D3`, `D7`–`D14`, `D17`, `D26`–`D27`, `D31`–`D32`, `A0`–`A1`, `A3`–`A6`, `A9`–`A11`), `TIM3` Channel 4 PWM + `DMA2_Stream5`, `I2C1` at 400 kHz, 9 ADC channels (two 8-channel CD4051 muxes + 7 CV channels with 32x oversampling), `USART1` MIDI RX/TX, external USB FS MIDI RX (when `DEBUG` is not defined), and 48 kHz 12-bit dual-channel DMA DAC.
- **External SDRAM Zero-Initialization**: `[buffer.sdram.cpp:SDRAMBuffer::SDRAMBuffer]` zeroes all three 42-second stereo `Buffer::Frame` source buffers (`_srcBuf1`, `_srcBuf2`, `_srcBuf3`) in external `DSY_SDRAM_BSS` memory on first access.
- **SDMMC & FatFS Filesystem I/O**: `[card.cpp:Card]` initializes `SdmmcHandler` (1-bit bus, `MEDIUM_SLOW` speed) and `FatFSInterface`, mounts/unmounts the SD card, and reads/writes/renames/deletes files on the FAT filesystem.
- **Boot Button Release System Reset**: In `Hardware::ProcessDigitalControls` (`[hardware.cpp:Hardware::ProcessDigitalControls]`), releasing the boot button (`boot_btn_` on `seed::D2`) after it was pressed immediately invokes `HAL_NVIC_SystemReset()`.
- **USB Transport Mode Switching**: `Hardware::StartUsbMidi` and `Hardware::StopUsbMidi` (`[hardware.cpp:Hardware::StartUsbMidi]`, `[hardware.cpp:Hardware::StopUsbMidi]`) initialize or tear down the external USB FS stack (`UsbHandle::FS_EXTERNAL`) so `USBTransfer` can switch the rear USB port between USB MIDI and USB CDC.
- **DMA & Interrupt State Mutation**: `Ws2812::Impl::initPwmDma` (`[ws2812.cpp:Ws2812::Impl::initPwmDma]`) enables `DMA2_Stream5_IRQn` and executes `asm("bkpt 255")` on `HAL_DMA_Init` failure. `Ws2812::Impl::Show` (`[ws2812.cpp:Ws2812::Impl::Show]`) writes `pwm_out_buf` in `DMA_BUFFER_MEM_SECTION`, advances `dither_`, and starts interrupt-driven DMA via `HAL_DMA_Start_IT`.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
