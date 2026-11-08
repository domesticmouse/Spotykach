# USB Transfer Firmware (`src/transfer`)

## Overview
Implements the firmware side of the Spotykach USB sample transfer protocol (`1.2`). Coordinates switching the rear external USB port from USB MIDI to USB CDC upon receiving the SysEx trigger, frames commands and responses with IEEE 802.3 CRC-32 checksums, and executes slot listing, atomic WAV uploads, sector-aligned downloads, deletion, `SK/config.txt` updates, and small text file reads/writes on the SD card.

## Interface
- `[protocol.h:spotykach::transfer::kProtoMajor]`, `[protocol.h:spotykach::transfer::kProtoMinor]`, `[protocol.h:spotykach::transfer::kSysExManufacturer]`, `[protocol.h:spotykach::transfer::kSysExSignature]`, `[protocol.h:spotykach::transfer::kSysExEnter]`, `[protocol.h:spotykach::transfer::kSysExReply]`: Protocol version (`1.2`) and MIDI SysEx handshake constants.
- `[protocol.h:spotykach::transfer::EnterStatus]`, `[protocol.h:spotykach::transfer::Command]`, `[protocol.h:spotykach::transfer::Status]`, `[protocol.h:spotykach::transfer::FrameError]`: Protocol command opcodes, status codes, and frame rejection reasons.
- `[protocol.h:spotykach::transfer::kMagic]`, `[protocol.h:spotykach::transfer::kHeaderSize]`, `[protocol.h:spotykach::transfer::kMaxChunk]`, `[protocol.h:spotykach::transfer::kMaxPayload]`, `[protocol.h:spotykach::transfer::kMaxFrame]`, `[protocol.h:spotykach::transfer::kResponseFlag]`, `[protocol.h:spotykach::transfer::kFrameErrorType]`, `[protocol.h:spotykach::transfer::kMaxNameLength]`, `[protocol.h:spotykach::transfer::kFileNameSize]`, `[protocol.h:spotykach::transfer::kMaxFileSize]`, `[protocol.h:spotykach::transfer::kSlotOccupied]`, `[protocol.h:spotykach::transfer::kSlotLoadable]`, `[protocol.h:spotykach::transfer::kSlotParsed]`: Frame sizing and slot flag constants.
- `[protocol.h:spotykach::transfer::crc32_update]`, `[protocol.h:spotykach::transfer::crc32]`, `[protocol.h:spotykach::transfer::get_u16]`, `[protocol.h:spotykach::transfer::get_u32]`, `[protocol.h:spotykach::transfer::put_u16]`, `[protocol.h:spotykach::transfer::put_u32]`: CRC-32 and little-endian serialization helpers.
- `[link.h:spotykach::transfer::Link]`: USB CDC packet framing and CRC verification (`Frame`, `Poll`, `start`, `stop`, `poll`, `payload`, `send`, `send_status`, `last_rx_ms`, `last_error`).
- `[service.h:spotykach::transfer::Service]`: Transfer session state machine and SD card command dispatcher (`init`, `begin`, `end`, `process`, `should_exit`, `is_busy`, `progress`).
- `[usb.transfer.h:spotykach::USBTransfer]`: Mode switch coordinator between `Hardware`, `Core`, `CoreUI`, `Storage`, and `transfer::Service` (`init`, `is_active`, `check_request`, `process`).

## Invariants
- `[link.h:Link::poll]` & `[link.cpp:Link::payload]`: Uses 12-byte little-endian `SK` frame headers (`kHeaderSize = 12`, `kMaxPayload = 32784`); a polled `Frame` remains valid until the next `send()`, and `payload()` waits up to `kTxTimeoutMs` (`200` ms) for USB CDC TX idle before writing to `_tx_buf`. After a frame error, incoming bytes are dropped until `kQuietMs` (`100` ms) of line silence; partial frames expire after `kStaleFrameMs` (`2000` ms).
- `[service.cpp:Service::process]`: Requires the SD card to be mounted and in `Card::State::transfer`; sets `should_exit()` after `kConnectTimeoutMs` (`60000` ms) prior to the first valid frame or `kIdleTimeoutMs` (`10000` ms) of inactivity once connected.
- `[service.cpp:Service::_upload_data]` & `[service.cpp:Service::_download_read]`: Non-final `upload_data` chunks and all `download_read` offsets must be multiples of `Card::kSectorSize` (`512` bytes) so FatFS DMA accesses stay word-aligned; `upload_commit` requires matching total size, CRC-32, and a loadable WAV header (`audio_format == 3`, `channels == 2`, `sample_rate == 48000`, `bits_per_sample == 32`, `block_align == 8`, `data_size > 0`).
- `[service.cpp:file_path]`: `file_read` and `file_write` only permit paths matching `NAME.EXT` or `SK/NAME.EXT` (`< 32` bytes, ASCII letters, digits, `_`, `-`, `.`, and `.txt`/`.md`/`.json` extensions) up to `kMaxFileSize` (`32736` bytes), preventing access to sample slots, `SK/MEM`, or temp files.
- `[usb.transfer.cpp:USBTransfer::_enter]`: Rejects transfer entry with `EnterStatus::busy` if either deck is recording or `Storage::begin_transfer()` reports busy, and `EnterStatus::no_card` if the SD card cannot be mounted.

## Side Effects
- `[usb.transfer.cpp:USBTransfer::_enter]` & `[usb.transfer.cpp:USBTransfer::_exit]`: Stops both decks, sends the MIDI SysEx reply, silences audio processing via `_is_active`, switches the external USB port between USB MIDI (`StopUsbMidi`/`StartUsbMidi`) and USB CDC (`usbd_mode = USBD_MODE_CDC` on `UsbHandle::FS_EXTERNAL`), and updates `CoreUI` transfer LEDs/progress.
- `[link.cpp:_rx_buf]` & `[link.cpp:_tx_buf]`: Allocates 32-byte aligned receive and transmit frame buffers in `DSY_SDRAM_BSS` and attaches `rx_callback` to the external USB CDC interrupt (`__disable_irq`/`__enable_irq`).
- `[service.cpp:Service]`: Creates, writes, renames, and deletes `/SK/<tape>/<slot>.wav`, `/SK/<tape>/<slot>.tmp`, `/SK/config.txt`, `/SK/config.tmp`, `/SK/file.tmp`, and root/`SK/` text files on the SD card via `Card`.

## Verification
- Run: `make -j8 && ./tests/transfer/run.sh`
