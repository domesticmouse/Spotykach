# UI Subsystem (`src/ui`)

## Overview
The `src/ui` package implements the user interface and control surface layer for Spotykach. It bridges physical hardware I/O (`src/hw`) and MIDI events with the audio DSP engine (`src/core`) and persistent storage (`src/memory`). Its responsibilities include multiplexed potentiometer soft-takeover tracking, shift-register switch decoding, MPR121 capacitive pad handling, CV/gate input conditioning (including 1V/Oct and zero-offset calibration), UART/USB MIDI processing, and 32-LED ring and status LED rendering.

## Interface
- `[core.ui.h:CoreUI]` — Primary UI coordinator class:
  - `CoreUI(Hardware&, Core&, Settings&, Storage&)`
  - `void init()` — Starts ADCs, initializes timers/pot monitor, and registers hardware, clock, and MIDI callbacks.
  - `void process()` — Main-loop UI update: scans digital controls, pots, pads, switches, and gate outputs; applies `MValue` updates to `Core`; updates LED state buffers.
  - `void tick()` — Audio-rate clock input and MIDI polling tick (`Driver::tick`).
  - `void process_gate_in()` — Timer-driven gate input edge detector and latency-compensated deck trigger.
  - `void read_cv()` — Audio-block CV reader applying `Calibrator` offsets and `SpeedMap` V/Oct conversion.
  - `void set_lfo(const float a, const float b)` — Updates modulator LED brightness levels from DAC callback.
  - `void render_leds()` — Flushes buffered LED and `LEDRing` states to `Hardware::leds`.
  - `void calibrate(const bool recalibrate)` — Initializes or runs `Calibrator`.
  - `CoreMIDI& midi()` — Accessor for the `CoreMIDI` handler.
  - `void set_transfer(const bool is_active)`, `void set_transfer_progress(const bool is_busy, const float progress)`, `bool process_transfer()` — USB file transfer UI mode controls.
- `[core.ui.h:kSpeedSteps]` — `static constexpr std::array<float, 7>` of quantized speed/pitch steps (`0.125f` to `1.0f`).
- `[core.midi.h:CoreMIDI]` — UART and USB MIDI controller (`CoreMIDI(Hardware&, Core&)`, `process()`, `send_clock()`, `set_on_note_on(...)`, `set_on_play(...)`, `set_on_record(...)`, `set_on_cc(...)`, `take_transfer_request()`, `reply_transfer(const uint8_t)`, `is_transfer_reply_pending()`).
- `[calibrator.h:Calibrator]` — CV offset and 1V/Oct calibration state machine (`Phase`, `Step`, `State`, `init(const bool)`, `next()`, `previous()`, `collect()`, `apply_and_exit()`, `correct(Hardware::CvInputId, const float)`, `correctVOctA(const float)`, `correctVOctB(const float)`, `step()`, `phase()`, `state_a()`, `state_b()`, `is_done()`).
- `[voct.h:infrasonic::CalibratedVOct]` — Bipolar 1V/Oct calibration processor preserving 0V neutral (`ReferenceReadings`, `Init(const ReferenceReadings&)`, `Process(float)`).
- `[led.ring.h:LEDRing]` — 32-LED circular display buffer with smoothstep interpolation (`set_hex_color`, `set_brightness`, `fill_brightness`, `set_segment`, `set_point_hex_color`, `set_point`, `add_point`, `is_updated`, `set_updated`, `apply`, `clear`).
- `[mvalue.h:MValue]` — Soft-takeover (catch-up) value wrapper for multiplexed potentiometers (`kDefaultTreshold = 0.02f`, `id()`, `process(...)`, `is_tracking()`, `in_value()`, `apply()`, `set_apply()`, `value()`, `set(...)`).
- `[color.h:Color]` — `infrasonic::Color` RGB/HSV color representation (`FromHSV`, `Red`/`Green`/`Blue`, `Red8`/`Green8`/`Blue8`, `Hex`, `Inverted`, `Normalized`, arithmetic operators).
- `[hold.h:Hold]` — `Hold<uint32_t duration_ms>` hold-duration detector (`init()`, `begin()`, `process()`, `inidcate()`, `is_holding()`, `passed()`, `end()`).
- `[speed.map.h:SpeedMap]` — `SpeedMap<int32_t half_range>` semitone-to-playback-speed lookup table with linear interpolation (`init()`, `range()`, `bipolar_pitch2speed(float)`, `norm2speed(float)`).
- `[time.iterval.h:TimeInterval]` — `TimeInterval<size_t seconds>` one-shot elapsed time checker (`start()`, `is_passed()`).

## Invariants
- `[core.ui.cpp:CoreUI::process]` — Returns immediately while `_state == State::launching` until `[core.ui.leds.cpp:CoreUI::_draw_launching]` completes the startup animation and sets `_state = State::init_values`, which overrides initial pot readings with default parameters before transitioning to `State::ready`.
- `[core.ui.cpp:CoreUI::process_gate_in]` — Enforces an 8 ms delay (`TimeInterval<8>`) after a rising gate edge before triggering `Deck::A` or `Deck::B` so V/Oct CV inputs settle, and only triggers when the target deck's `DeckStorage` is `idle`.
- `[core.ui.cpp:CoreUI::_process_gate_out]` — Gate output pulses remain high for 7 ms (`_gate_out_timer[ref].HasPassedMs(7)`) after `voxs().read_reset_is_triggered()`.
- `[core.ui.cpp:CoreUI::_process_switches]` — Shift register readings (`GetShiftRegState(0)` and `GetShiftRegState(1)`) are bitwise-inverted (`~`) due to hardware pull-ups, and the manual tap switch (`sr2.test(6)`) is sampled at most once every 4 ms (250 Hz).
- `[core.ui.pads.cpp:CoreUI::_on_pad_touch]` — When `_is_transfer` is `true`, all capacitive pad touches and releases are ignored except `Hardware::Pad::PlayA` and `Hardware::Pad::PlayB`, which set `_transfer_exit = true`.
- `[mvalue.cpp:MValue::process]` — Potentiometer changes on a newly activated layer do not take effect until the physical pot position comes within `thresh` (`0.02f` default, `0.1f` for Alt-quantized pitch) of the stored `_value`; calling `[mvalue.h:MValue::value]` clears `_apply = false`.
- `[calibrator.cpp:Calibrator::_collect]` — Collects `kMaxAvgCount` (`50`) CV samples with 4 ms delays; rejects 1V/Oct calibration steps deviating from default targets by more than `kDeviationTolerance` (`0.02f`) and rejects zero-offset calibration when the average exceeds `0.03`.
- `[core.midi.cpp:CoreMIDI::process]` — USB MIDI listening, SysEx transfer replies, and USB MIDI transmission are compiled out when `DEBUG` is defined (`#ifndef DEBUG`), and SysEx transfer-enter commands are only honored when received over USB MIDI (`is_usb == true`).
- `[time.iterval.h:TimeInterval::is_passed]` — The template parameter `seconds` is multiplied by `1000` microseconds (`seconds * 1000`), so `TimeInterval<N>` measures `N` milliseconds and disarms (`_scheduled = false`) once elapsed.

## Side Effects
- `[core.ui.cpp:CoreUI::init]` — Starts hardware ADCs (`_hw.StartAdcs()`), initializes `daisy::PotMonitor`, and registers event callbacks on `Hardware`, `Driver`, and `CoreMIDI`.
- `[core.ui.cpp:CoreUI::process]` — Polls digital controls, analog pots, shift registers, and MPR121 pads; mutates `Core` (`Deck`, `Driver`, `Modulator`, `Panner`, `Grit`, `Flux`) state; drives hardware gate outputs (`SetGateOutA`, `SetGateOutB`); and initiates `Storage` slot selection, load, save, and cancel operations.
- `[core.ui.leds.cpp:CoreUI::render_leds]` — Mutates and flushes the hardware WS2812 LED buffer via `_hw.leds.Clear()`, `_hw.leds.Set(...)`, and `_hw.leds.Show()`.
- `[core.midi.cpp:CoreMIDI::process]` — Pops events from `Hardware::midi_uart` and `Hardware::midi_usb`, transmits SysEx transfer replies (`_hw.midi_usb.SendMessage`), enqueues realtime clock messages, and flushes outbound MIDI buffers via `TransmitEnqueuedMessages()`.
- `[calibrator.cpp:Calibrator::_collect]` — Blocks execution via `daisy::System::Delay(4)` while averaging CV readings, mutates `Settings::data()`, and reinitializes `infrasonic::CalibratedVOct` instances (`_voct_a`, `_voct_b`).

## Verification
- Run: `make -j8`
