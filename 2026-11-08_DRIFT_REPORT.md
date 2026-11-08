## README.md

No drift detected.

## src/README.md

No drift detected.

## src/core/README.md

No drift detected.

## src/core/fx/README.md

No drift detected.

## src/hw/README.md

No drift detected.

## src/memory/README.md

No drift detected.

## src/transfer/README.md

No drift detected.

## src/ui/README.md

No drift detected.

## web/README.md

No drift detected.

## web/spotykach-transfer/README.md

- **Version Table Omission (`web/spotykach-transfer/README.md` § Versioning vs. `src/core/config.h`)**: The `Firmware` column in the `Versioning` table lists `"uploader branch, first release with USB transfer"` for `1.0.1`, without citing the concrete firmware release version constant (`kFirmwareVersion = "1.4.0"` in `src/core/config.h:57`).

## docs/usb-transfer.md

- **Firmware Version Constant Drift (`docs/usb-transfer.md` § 5.3 & § 7.6 vs. `src/core/config.h:57`)**: Section 5.3 (line 160) and Section 7.6 (lines 352–355) state that `kFirmwareVersion` in `src/core/config.h` is `"1.3.1"` (`static constexpr const char* kFirmwareVersion = "1.3.1";`), whereas `src/core/config.h:57` defines `static constexpr const char* kFirmwareVersion = "1.4.0";`.
- **Command Enum Name Drift (`docs/usb-transfer.md` § 5.3 vs. `src/transfer/protocol.h:51` & `web/spotykach-transfer/index.js`)**: Section 5.3 (line 139) and Section 5.5 (line 235) name command `0x30` `DELETE`, whereas the firmware (`Command::remove = 0x30` in `src/transfer/protocol.h:51`) and host library (`CMD.remove: 0x30` in `web/spotykach-transfer/index.js`) name it `remove`.
