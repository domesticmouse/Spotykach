# Core FX (`src/core/fx`)

## Overview
Per-deck stereo audio effects processing chain for Spotykach. Provides soft-switched `Grit` (insert saturation/degradation/filter unit combining `Drive`, `Reduce`, and `Filter` modes) followed by `Flux` (send/return stereo tape-style echo delay with free and tempo-clocked modes, backed by cascaded biquad filtering and fractional delay lines).

## Interface
- `[fx.h:spotykach::Fx]` — Top-level per-deck FX processor (`init(const Params)`, `process(float& inout0, float& inout1)`, `grit()`, `is_grit_on()`, `set_grit_on(bool)`, `toggle_grit_lock()`, `flux()`, `is_flux_on()`, `set_flux_on(bool)`, `toggle_flux_lock()`, `kEchoDelayBufferLength`).
- `[fx.grit.h:spotykach::Grit]` — Multi-mode insert effect (`Mode::Drive`, `Mode::Reduce`, `Mode::Filter`, `init(float)`, `process(float&, float&)`, `mode()`, `switch_mode()`, `intensity()`, `set_intensity(float)`, `character()`, `set_character(float)`, `mix()`, `set_mix(float, bool)`).
- `[fx.drive.h:spotykach::Drive]` — Overdrive processor with intensity-compensated attenuation and dry/wet crossfade (`init(float)`, `intensity()`, `set_intensity(float)`, `mix()`, `set_mix(float)`, `process(float&, float&)`).
- `[fx.reduce.h:spotykach::Reduce]` — Bitcrusher and sample-rate decimator with dry/wet crossfade (`init(float)`, `set_intensity(float)`, `intensity()`, `set_mix(float)`, `mix()`, `process(float&, float&)`).
- `[filter.h:spotykach::Filter]` — Split DJ-style resonant filter (`< 0.5` 12 dB/oct low-pass, `>= 0.5` 12 dB/oct high-pass) with dry/wet crossfade and soft limiting (`init(float)`, `cutoff()`, `set_cutoff(float)`, `q()`, `set_q(float)`, `mix()`, `set_mix(float)`, `process(float&, float&)`).
- `[fx.flux.h:spotykach::Flux]` — Stereo echo/delay processor supporting `Mode::FreeDelay` and `Mode::ClockedDelay` (`init(float, float**)`, `process(float&, float&, float)`, `time_norm()`, `set_time_norm(float)`, `mix_norm()`, `set_mix_norm(float)`, `fb_norm()`, `set_fb_norm(float)`, `switch_mode()`, `mode()`, `set_tempo_bpm(float)`, `kFeedbackDelayBufferLength`, `kDelayMaxSeconds`, `kEchoDelayBufferLength`).
- `[echo.h:infrasonic::EchoDelay]` — Templated tape-style delay line with one-pole delay-time lag smoothing, 12 dB/oct bandpass feedback filtering (`800 Hz`), and soft clipping (`Init(float, float*)`, `SetLagTime(float)`, `SetDelayTime(float, bool)`, `SetFeedback(float)`, `Feedback()`, `Process(float)`).
- `[biquad.h:infrasonic::BiquadSection]` & `[biquad.h:infrasonic::BiquadCascade]` — Transposed Direct Form II stereo biquad filter primitives and type aliases (`LPF12`, `LPF24`, `HPF12`, `HPF24`, `BPF12`, `BPF24`).
- `[deline.h:DeLine]` — Templated circular delay buffer with fractional linear interpolation (`Init(float*)`, `Reset()`, `SetDelay(float)`, `Write(const T)`, `Read()`).

## Invariants
- `[fx.flux.h:spotykach::Flux::init]` requires `delay_buf` to point to two valid channel buffers each of at least `Flux::kEchoDelayBufferLength` (`240,000` floats, 5 seconds at 48 kHz) allocated in external SDRAM (`[deline.h:DeLine::Init]`).
- `[biquad.h:infrasonic::BiquadSection::Process]` asserts `channel < 2` (`assert(channel < 2)`) and `[biquad.h:infrasonic::BiquadCascade]` enforces `static_assert(NumSections > 0)`.
- `[fx.cpp:spotykach::Fx::set_grit_on]` and `[fx.cpp:spotykach::Fx::set_flux_on]` do not disengage the effect switch while `_grit_lock` or `_flux_lock` is active; transitions are ramped over a 4 ms Hann micro-envelope via `SoftSwitch`.
- `[filter.cpp:spotykach::Filter::set_q]` clamps normalized resonance to `kMaxResonance` (`0.9f`), mapping exponentially between `kFlatQ` (`0.70710678f`) and `kMaxQ` (`10.0f`).

## Side Effects
- Mutates stereo audio samples in-place (`inout0`, `inout1`) during the real-time audio callback (`[fx.cpp:spotykach::Fx::process]`).
- Zeroes and writes to external SDRAM delay line buffers via `[deline.h:DeLine::Reset]` and `[deline.h:DeLine::Write]`.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
