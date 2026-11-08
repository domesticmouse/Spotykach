---
title: "Spotykach Firmware Engineering"
page_title: "Spotykach Firmware Engineering Course"
nav_id: "index"
badge: "Mission: Custom Spotykach Firmware from Scratch"
subtitle: "An interactive, dual-verified C++17 embedded audio course teaching you how to build custom firmware for the Synthux Academy Spotykach hardware from the ground up."
---

## Course Mission {#course-mission}

The joy of hacking on a hardware synth like the Synthux Academy Spotykach is turning a physical knob and hearing real-time audio warp under your fingers. The pain is staring at a bare-metal C++17 codebase, custom STM32H7 linker scripts, and DMA interrupts when your background is high-level application code.

So, in this course we are going to build a custom firmware for this little noise maker from the ground up — starting with zero assumed background in C++17, STM32H7 embedded peripherals, or real-time audio DSP{{sidenote:All pinouts, linker scripts (`alt_sram.lds`), and real-time audio invariants in this course are drawn directly from the production Spotykach repository on the Electro-Smith Daisy Seed (`STM32H750IBK6` ARM Cortex-M7 @ 480 MHz).}}.

Turns out, waiting to flash a hardware board over USB just to discover an off-by-one bug in a state machine is a great way to lose your sanity. To keep our codebase evergreen and fast to iterate on, every lesson pairs a self-contained tutorial with a runnable companion project in `tutorial/apps/<NNNN-slug>/` that passes **two automated verification gates**:
1. **Host C++17 Unit Tests (`make test`)**: Compiles and tests the lesson's C++17 state machines and DSP modules on your computer in under a second (`-std=c++17 -Wall -Wextra -Werror -pedantic`).
2. **ARM Cortex-M7 Firmware Binary (`make`)**: Cross-compiles and links a real `BOOT_SRAM` firmware image (`.elf` + `.bin`) against `alt_sram.lds`, `libDaisy`, and `DaisySP`, ready to flash via `make program-dfu`.

---

## Published Lessons {#published-lessons}

{{widget:lesson-cards}}

---

## Printable Reference Sheets {#reference-sheets}

{{widget:reference-cards}}
