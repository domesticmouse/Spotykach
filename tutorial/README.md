# Spotykach Firmware Engineering Course (`./tutorial/`)

An interactive, stateful code-teaching workspace for learning how to build custom C++17 firmware for the **Synthux Academy Spotykach** hardware from scratch, using this repository as the authoritative source of truth.

## Quick Start

1. **Pre-build the `libDaisy` and `DaisySP` static libraries (once at the repo root):**
   ```bash
   make -j8 libs
   ```
2. **Compile and validate the course HTML site:**
   ```bash
   tutorial/.venv/bin/python tutorial/build.py --check
   ```
3. **Open the course in your browser:**
   - Course Landing Page: [`tutorial/index.html`](./index.html)
   - Lesson 0001: [`tutorial/lessons/0001-boot-sram-and-heartbeat.html`](./lessons/0001-boot-sram-and-heartbeat.html)

## Published Lessons

- **[Lesson 0001 — `BOOT_SRAM` Memory Layout, C++17 Application Lifecycle & Bootloader Rescue](./lessons/0001-boot-sram-and-heartbeat.md)** (`tutorial/apps/0001-boot-sram-and-heartbeat/`)

## Reference Sheets

- **[Glossary of Spotykach Firmware Terms](./reference/GLOSSARY.md)** (`tutorial/reference/glossary.html`)
- **[Spotykach Hardware & STM32H750 Architecture Cheat Sheet](./reference/hardware-architecture.md)** (`tutorial/reference/hardware-architecture.html`)
- **[Dual Verification & Flashing Guide](./reference/verification-guide.md)** (`tutorial/reference/verification-guide.html`)

## Course Workspace Files

- [`MISSION.md`](./MISSION.md) — Concrete course goal, success criteria, and scope boundaries.
- [`RESOURCES.md`](./RESOURCES.md) — Curated primary sources and workspace skills (`libdaisy-guide`, `daisysp-guide`, `spotykach-submodules`).
- [`NOTES.md`](./NOTES.md) — Learner profile, dual-verification contract, and 10-lesson curriculum roadmap.
- [`learning-records/`](./learning-records/) — Decision-grade records tracking baseline knowledge and mastered skills.
