# Firmware Source (`src`)

## Overview
Root firmware source package for Spotykach. Provides shared DSP math, logging, assertion, debug telemetry, and non-copyable type macros (`common.h`, `expose.h`, `nocopy.h`), and groups the five core firmware subsystems: real-time dual-deck audio engine (`core`), Daisy Seed hardware abstraction and peripheral drivers (`hw`), QSPI flash settings and SD card slot storage (`memory`), USB sample transfer protocol (`transfer`), and physical control surface / LED / MIDI UI (`ui`).

## Interface
- `[common.h:infrasonic::Log]` — Conditional logger type alias (`daisy::Logger<INFS_LOG_TARGET>` when `INFS_LOG` is truthy, otherwise `daisy::Logger<daisy::LOGGER_NONE>`), plus `LOG_TAGGED(TAG, FMT, ...)`, `INFS_MIN`, `INFS_MAX`, and `INFS_CLAMP` macros.
- `[common.h:infrasonic::FailAssertion]` — Debug assertion helper logging formatted messages and triggering `asm("bkpt 255")` when `DEBUG` is enabled.
- `[common.h:infrasonic::is_in_unit_range]`, `[common.h:infrasonic::sgn]`, `[common.h:infrasonic::unitclamp]`, `[common.h:infrasonic::lerp]`, `[common.h:infrasonic::lerp3]`, `[common.h:infrasonic::frac_table_lerp]`, `[common.h:infrasonic::map]`, `[common.h:infrasonic::dbfs2lin]`, `[common.h:infrasonic::dbfs2lin_pwr]`, `[common.h:infrasonic::lin2dbfs]`, `[common.h:infrasonic::map_db]`, `[common.h:infrasonic::map_db_split]`, `[common.h:infrasonic::onepole_coef]` — Shared DSP math, interpolation, decibel conversion, and one-pole filter coefficient helpers.
- `[expose.h:Expose]` — Singleton debug telemetry probe (`Expose::values()`, `print()`, `vox`, `layer`, `p1`–`p5`) and probe macros `IP1`, `IP2`, `FP3`, `FP4`, `FP5`.
- `[nocopy.h:NOCOPY]` — Macro deleting copy and move constructors and assignment operators (`NOCOPY(T)`).
- Subdirectories:
  - [`core`](./core/README.md) — Dual-deck real-time DSP audio engine, 3-voice granular/slice/tape generator, 48 PPQN clock synchronization driver, 128-step sequencer, and LFO/follower modulation subsystem.
  - [`hw`](./hw/README.md) — Daisy Seed board support package, external SDRAM buffer pool (`SDRAMBuffer`), SDMMC/FatFS card driver (`Card`), CD74HC165 shift registers, MPR121 touch pads, and WS2812 PWM+DMA LED driver.
  - [`memory`](./memory/README.md) — QSPI flash calibration storage (`Settings`), SD card 6x6 tape/slot management (`Storage`, `DeckStorage`), and RIFF/WAVE header and cue-point parser/writer.
  - [`transfer`](./transfer/README.md) — Firmware side of the Spotykach USB transfer protocol (`1.2`), handling USB MIDI-to-CDC mode switching, CRC-32 packet framing (`Link`), and SD card file/slot operations (`Service`, `USBTransfer`).
  - [`ui`](./ui/README.md) — Control surface coordinator (`CoreUI`), multiplexed pot soft-takeover (`MValue`), 32-LED ring renderer (`LEDRing`), CV/V-Oct calibrator (`Calibrator`), and UART/USB MIDI handler (`CoreMIDI`).

## Invariants
- `[common.h:infrasonic::onepole_coef]` returns `1.0f` whenever `time_s <= 0.0f` or `sample_rate <= 0.0f`, and clamps positive coefficients to `<= 1.0f`.
- `[expose.h:Expose::print]` only logs probe fields (`p1`–`p5`) that are strictly greater than `kOff` (`-INT32_MAX`), resetting each logged field back to `kOff` immediately after printing.

## Side Effects
- `[common.h:infrasonic::FailAssertion]` writes formatted error output to `infrasonic::Log` and halts execution at a hardware breakpoint (`asm("bkpt 255")`) when `DEBUG` is defined.
- `[expose.h:Expose::print]` transmits formatted debug probe values (`P1`–`P5`) via `infrasonic::Log::PrintLine` and resets `p1`–`p5` to `kOff`.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
