# Memory & Storage (`src/memory`)

## Overview
Manages persistent calibration settings in Daisy QSPI flash, SD card sample slot paths and asynchronous load/save/preload state machines for Decks A and B, and RIFF/WAVE header, metadata (`LIST/INFO/INAM`), and cue-point parsing and generation.

## Interface
- `[settings.h:spotykach::Settings]`: QSPI persistent calibration wrapper (`kDataVersion`, `Settings::Data`, `init`, `is_user_defined`, `data`, `read`, `write`).
- `[slots.h:spotykach::kStorageTapeCount]`, `[slots.h:spotykach::kStorageSlotCount]`, `[slots.h:spotykach::kStorageConfigPath]`, `[slots.h:spotykach::kStorageConfigTempPath]`, `[slots.h:spotykach::kStorageFileTempPath]`: Card layout constants (`6` tapes × `6` slots, `/SK/config.txt`, `/SK/config.tmp`, `/SK/file.tmp`).
- `[slots.h:spotykach::storage_root_dir]`, `[slots.h:spotykach::storage_tape_name]`, `[slots.h:spotykach::storage_slot_name]`, `[slots.h:spotykach::storage_slot_path]`, `[slots.h:spotykach::storage_root_path]`, `[slots.h:spotykach::storage_tape_path]`: Path builders for `/SK` and `/SK/<tape>/<slot><ext>`.
- `[storage.h:spotykach::kMemory]`, `[storage.h:spotykach::DeckStorage]`: Per-deck slot selection, preload, load, and save state machine (`Slot`, `State`, `init`, `is_idle`, `is_selecting`, `is_processing`, `is_released`, `is_preloading`, `state`, `deck_ref`, `progress`, `set_on_save_audio`, `next_tape`, `previous_tape`, `selected_tape_idx`, `slot_at`, `can_load`, `selected_slot_idx`, `select_slot_at`, `reset_recent_slot`).
- `[storage.h:spotykach::Storage]`: Top-level SD card coordinator across both decks and USB transfer mode (`PreloadStep`, `TransferCheck`, `init`, `card_state`, `read_settigs`, `activate`, `deactivate`, `load`, `save`, `cancel`, `process`, `of`, `begin_transfer`, `end_transfer`, `card`).
- `[wav.h:WavHeader]`, `[wav.h:WavInfo]`, `[wav.h:wav_header]`, `[wav.h:find_cue_points]`, `[wav.h:wav_info]`, `[wav.h:wav_cue_count]`: RIFF/WAVE header construction, chunk inspection, and cue-point extraction.

## Invariants
- `[slots.h:kStorageTapeCount]` & `[slots.h:kStorageSlotCount]`: Fixed 6 tapes (`B`, `G`, `P`, `R`, `T`, `Y`) and 6 slots (`1`–`6`) per tape shared by both decks under `/SK/<tape>/<slot>.wav`; `storage_slot_path` requires at least 16 bytes in `out_path`, and `storage_root_path`/`storage_tape_path` require at least 8 bytes.
- `[storage.h:Storage::begin_transfer]`: Blocking call that must run from the main loop only; returns `TransferCheck::busy` if `_preload_step != PreloadStep::done`, `_opening_deck != Deck::None`, or either deck is processing (`loading`/`saving`).
- `[storage.h:Storage::load]` & `[storage.h:Storage::save]`: Require `of(ref).is_selecting()` and `card_state() == Card::State::idle` before starting card I/O.
- `[storage.cpp:DeckStorage::_read_preload_source]`: Expects 4 ASCII digits (`1`–`6`, or `0` to skip) in `SK/MEM` (`[tape A, slot A, tape B, slot B]`, `kMemSize = 4`).
- `[wav.cpp:wav_header]` & `[wav.cpp:read_cue_points]`: Saved WAV headers (`wav_header(size)`) use IEEE 754 float (`AudioFormat = 3`), 2 channels, 48,000 Hz, and 32-bit samples; parsed cue points are filtered below `cue_limit`, capped at `spotykach::kMaxFileCuePoints`, and sorted in ascending order.

## Side Effects
- `[settings.h:Settings::init]` & `[settings.h:Settings::write]`: Initializes and writes V/Oct and CV offset calibration (`slug = "cal"`, `storage_version = 1`) to Daisy QSPI flash via `daisy::PersistentStorage`.
- `[storage.h:Storage]` & `[storage.cpp:DeckStorage]`: Mounts and unmounts the SD card (`Card`), reads `/SK/config.txt` into `Config::dynamic()`, reads and updates `SK/MEM`, and streams deck audio buffers and cue points to/from `/SK/<tape>/<slot>.wav` using `SDRAMBuffer::pool().card_buffer()`.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
