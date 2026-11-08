# Web Packages (`web`)

## Overview
Contains the standalone browser-based **Spotykach Manager** web application (`index.html`, `icon.svg`) and JavaScript/TypeScript packages for communicating with Spotykach hardware from Chromium-based browsers over Web MIDI and Web Serial.

## Subdirectories & Boundaries
- `spotykach-transfer`: [`./spotykach-transfer/README.md`](./spotykach-transfer/README.md) - Host side of the Spotykach USB sample transfer protocol (`@synthuxacademy/spotykach-transfer`), providing Web MIDI SysEx mode switching, Web Serial slot/config/file operations, and 48 kHz stereo 32-bit float WAV preparation.
