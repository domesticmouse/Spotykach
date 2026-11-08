# Core Audio Engine (`src/core`)

## Overview
Real-time dual-deck audio engine, granular/slice/tape playback generator, clock synchronization driver, pattern sequencer, and modulation subsystem for Spotykach. Coordinates audio routing (`DoubleMono`, `Stereo`, `GenerativeStereo`), SDRAM-backed loop recording/overdubbing, 48 PPQN internal/external clock division, 3-voice per-deck polyphonic/monophonic grain and slice playback, and per-deck LFO/envelope-follower modulation.

## Interface
- `[core.h:spotykach::Core]`, `[core.h:spotykach::Route]`, `[core.h:spotykach::ModType]` — Top-level dual-deck engine (`init(float, float)`, `driver()`, `panner()`, `deck(Deck::Ref)`, `mod(Deck::Ref)`, `source(Deck::Ref)`, `set_source(Deck::Source, Deck::Ref)`, `infer_panner_mode()`, `mix()`, `set_mix(float)`, `mix_mod_in(float)`, `set_route(Route)`, `route()`, `set_click_mix(float)`, `prepare()`, `process(const float* const*, float**, size_t)`).
- `[deck.h:spotykach::Deck]`, `[mode.h:spotykach::Mode]` — Per-deck state machine supporting `Mode::Reel`, `Mode::Slice`, and `Mode::Drift` (`init(Params)`, `prepare()`, `process_commands()`, `process_out(...)`, `process_in(...)`, `toggle_play()`, `play()`, `stop()`, `toggle_recording()`, `disarm()`, `make_grid()`, `clear_sequence()`, `tick(bool, bool)`, `trigger(const Event*)`, `set_reverse(bool)`, `set_tempo(float)`, `tempo_to_fit(float)`, `set_mode(Mode)`, `set_inout_mix(float)`, `set_feedback(float)`, `track()`, `buffer()`, `voxs()`, `fx()`).
- `[driver.h:spotykach::Driver]`, `[driver.h:spotykach::kKeyInterval]`, `[driver.h:spotykach::kKeyIntervals]`, `[synclock.h:bleeptools::SynClock]`, `[divider.h:spotykach::Divider]`, `[tempo.h:spotykach::Tempo]`, `[click.h:spotykach::Click]` — Master clock synchronization (`Source::internal`, `Source::ts4`, `Source::midi`), tap tempo, bar/key interval tracking, swing/triplet clock division, and metronome click synthesis.
- `[generator.h:spotykach::Generator]`, `[vox.h:spotykach::Vox]`, `[vox.h:spotykach::SpeedMode]`, `[window.h:spotykach::Window]`, `[phasor.h:spotykach::Phasor]`, `[skip.write.head.h:spotykach::skip_write_head]`, `[adenv.h:spotykach::ADEnvelope]` — 3-voice (`kVoxCount = 3`) playback generator with 6 overlapping Hann-windowed grains per voice, Q31.32 fixed-point `Phasor` read heads, write-head collision avoidance during overdubbing, and curved AD envelopes.
- `[buffer.h:spotykach::Buffer]`, `[detector.h:spotykach::Detector]`, `[softswitch.h:spotykach::SoftSwitch]`, `[hann.h:bleeptools::Hann]` — Stereo loop buffer with Hann fade-in/out recording, overdub feedback, linear interpolation readback, and 10 ms EMA input threshold gate detector.
- `[track.h:spotykach::Track]`, `[dispatcher.h:spotykach::Dispatcher]`, `[event.h:spotykach::Event]`, `[irq.queue.h:spotykach::IrqQueue]` — 128-step (`kSlicesCount = 8` x `kSliceLength = 16`) parameter-lock event sequencer, voice allocation dispatcher (`Mono`/`Poly`), and IRQ-safe command queue.
- `[modulator.h:spotykach::Modulator]`, `[lfo.h:spotykach::LFO]`, `[lutsinosc.h:spotykach::LUTSinOsc]`, `[random.lfo.h:spotykach::RandomLFO]`, `[follower.h:spotykach::Follower]` — Per-deck modulation source selectable between tempo-syncable multi-waveform `LFO` and mean-square envelope `Follower`.
- `[panner.h:spotykach::Panner]`, `[xfade.h:spotykach::XFade]`, `[smooth.h:spotykach::OnePoleSmoother]` — Generative stereo panner (`off`, `smooth`, `step`), square-law crossfader, and one-pole parameter smoother.
- `[config.h:spotykach::Config]`, `[config.h:spotykach::CC]`, `[config.h:spotykach::kFirmwareVersion]` — Runtime configuration parser (`Config::dynamic().fill(...)`), static DSP constants (`kPPQNIntern = 48`, `kMaxSlicePointCount = 256`), and MIDI CC mappings.
- Subdirectories:
  - [fx](./fx/README.md) — Per-deck `Grit` and `Flux` stereo audio effects processors.

## Invariants
- `[deck.h:spotykach::Deck::process_commands]` must only be called from the audio callback context; cross-context mutations (`set_mode`, `trigger`, `toggle_play`, `play`, `stop`, `clear_sequence`) must be posted through `[irq.queue.h:spotykach::IrqQueue]` (`_commands`), which disables interrupts via `daisy::ScopedIrqBlocker` during push/pop.
- Switching a deck to `Mode::Drift` while voices are actively generating defers the mode transition via `_pending_mode` and calls `_dispatcher.all_off()` first so all voices settle before reconfiguring to `Vox::Mode::Spread` (`[deck.cpp:spotykach::Deck::_validate_mode]`).
- `[phasor.h:spotykach::Phasor]` represents frame positions in signed Q31.32 fixed-point format; `[buffer.cpp:spotykach::Buffer::read_linear]` wraps integer frame indices modulo `_size` and returns silence (`0.f`) when `_size == 0`.
- When overdubbing (`Buffer::is_overdubbing()`), newly activated windows execute `[skip.write.head.h:spotykach::skip_write_head]` to clamp window length or advance the read head past the active write head.
- In external sync mode (`Source::ts4` or `Source::midi`), `[driver.cpp:spotykach::Driver::tick]` stops the clock and resets dividers if no external clock pulse arrives within `1000 ms` (corresponding to the minimum 20 BPM at 4 PPQN).

## Side Effects
- `[core.cpp:spotykach::Core::init]` claims shared SDRAM backing buffers from `SDRAMBuffer::pool()` for both decks' main audio buffers, detector buffers, delay lines, slice cue arrays, and sequencer event tracks.
- `[core.cpp:spotykach::Core::process]` reads and mutates deck buffers, modulators, panner state, and writes soft-limited stereo audio to the hardware SAI output buffer.
- `[driver.cpp:spotykach::Driver::_on_clock_tick]` invokes `_on_clock_out` and `_on_quarter` callbacks to drive hardware clock output pulses and UI beat indicators.
- `[config.cpp:spotykach::Config::fill]` mutates the singleton `Config::dynamic()` state from raw configuration file bytes loaded from storage.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
