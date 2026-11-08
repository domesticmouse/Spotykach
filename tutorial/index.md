---
title: "Spotykach Firmware Engineering"
page_title: "Spotykach Firmware Engineering Course"
nav_id: "index"
badge: "Mission: Custom Spotykach Firmware from Scratch"
subtitle: "An interactive, dual-verified C++17 embedded audio course teaching you how to build custom firmware for the Synthux Academy Spotykach hardware from the ground up."
---

## Course Mission {#course-mission}

Spotykach is a dual-deck hardware audio looper, granular/slice/tape processor, and performance instrument built on the Electro-Smith Daisy Seed (`STM32H750IBK6` ARM Cortex-M7 @ 480 MHz){{sidenote:All pinouts, linker scripts (`alt_sram.lds`), and real-time audio invariants in this course are drawn directly from the production Spotykach repository.}}. In this course, you will build a custom Spotykach firmware from scratch — starting with zero assumed background in C++17, STM32H7 embedded peripherals, or real-time audio DSP.

Every lesson pairs a self-contained tutorial with a runnable companion project in `tutorial/apps/<NNNN-slug>/` that passes **two automated verification gates**:
1. **Host C++17 Unit Tests (`make test`)**: Compiles and tests the lesson's C++17 state machines and DSP modules on your computer in under a second (`-std=c++17 -Wall -Wextra -Werror -pedantic`).
2. **ARM Cortex-M7 Firmware Binary (`make`)**: Cross-compiles and links a real `BOOT_SRAM` firmware image (`.elf` + `.bin`) against `alt_sram.lds`, `libDaisy`, and `DaisySP`, ready to flash via `make program-dfu`.

---

## Published Lessons {#published-lessons}

{{widget:lesson-cards}}

---

## Printable Reference Sheets {#reference-sheets}

{{widget:reference-cards}}
