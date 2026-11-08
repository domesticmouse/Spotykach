---
title: "Dual Verification & Flashing Guide"
page_title: "Verification Guide — Spotykach Firmware Course"
nav_id: "verification-guide"
nav_label: "Verification Guide"
badge: "Reference • Build, Test & DFU"
subtitle: "How every lesson in this course verifies companion firmware using both the ARM Cortex-M7 cross-compiler and deterministic host C++17 unit tests."
card:
  title: "**Dual Verification & Flashing Guide**"
  summary: "Commands and mental model for verifying every lesson's companion app (`tutorial/apps/<NNNN-slug>/`) via ARM Cortex-M7 `.bin`/`.elf` compilation, memory budget inspection, host C++17 unit tests, and USB DFU flashing."
---

## 1. Why Dual Verification?

If you have to hold a physical button for three seconds and flash over USB every time you want to check an off-by-one boundary condition, you will lose your mind. Or, moreover, you just won't test it.

Turns out, embedded firmware usually fails in two distinct places:
1. **Hardware linkage & memory placement errors** (missing `extern` symbols like `USBD_MANUFACTURER_STRING`, overflowing `DTCMRAM`, or misconfigured linker scripts), which only an ARM Cortex-M7 cross-compiler (`arm-none-eabi-g++`) and linker (`alt_sram.lds`) can catch.
2. **State-machine, math, and DSP logic bugs** (off-by-one hold timers, inverted gate logic, soft-takeover edge cases, or NaN samples), which are fast and painless to catch on your host machine if you keep your logic decoupled from hardware registers.

So, every companion app under `tutorial/apps/<NNNN-slug>/` separates **hardware-independent C++17 logic headers** from **thin `libDaisy` hardware glue**, enabling two complementary verification gates in a single `Makefile`:

Table: Dual verification targets in `tutorial/apps/<NNNN-slug>/Makefile`

| Command | Compiler & Target | What It Verifies |
| :--- | :--- | :--- |
| `make` | `arm-none-eabi-g++ -std=c++17` (`Cortex-M7`, `alt_sram.lds`) | Links against `lib/libDaisy/build/libdaisy.a` and `lib/DaisySP/build/libdaisysp.a`, producing `build/<target>.elf` and flashable `build/<target>.bin` with memory region usage table. |
| `make test` | Host `c++ -std=c++17 -Wall -Wextra -Werror -pedantic` | Compiles and runs `tests/test_*.cpp` on your computer in $< 1\text{ s}$, verifying every state transition, boundary condition, and DSP calculation with deterministic assertions. |
| `make program-dfu` | `dfu-util` (`0483:df11` @ `0x90040000`) | Flashes `build/<target>.bin` into the Spotykach QSPI flash over the rear USB-C port when the Daisy Bootloader is breathing white. |

---

## 2. Pre-Building the Submodule Libraries (One-Time Setup)

Before building your first lesson companion app, compile `libDaisy` and `DaisySP` once at the repository root:

```bash caption="Compile libDaisy and DaisySP static archives at repo root"
make -j8 libs
```

This generates:
- `lib/libDaisy/build/libdaisy.a`
- `lib/DaisySP/build/libdaisysp.a`

All lesson companion apps in `tutorial/apps/<NNNN-slug>/` link directly against these prebuilt archives so each lesson's ARM firmware builds in ~1–2 seconds.

---

## 3. Running Dual Verification in a Lesson Directory

Inside any `tutorial/apps/<NNNN-slug>/` directory, run both gates:

```bash caption="Run host unit tests and ARM Cortex-M7 firmware compilation"
make test && make
```

To inspect section sizes in detail after building:

```bash caption="Inspect ELF section placement with arm-none-eabi-size"
arm-none-eabi-size -A build/*.elf
```

---

## 4. Flashing to Physical Spotykach Hardware via USB DFU

:::callout-warn
**Use the Rear PCB USB-C Port (`FS_EXTERNAL`), Not the Daisy Seed Micro-USB Port!**
Spotykach's custom bootloader (`bootloader-spotykach-v2.bin`) enumerates USB DFU on the **external USB-C connector** on the rear of the Spotykach PCB (`seed::D29`/`D30`). If you plug into the Daisy Seed's internal Micro-USB port while running the Spotykach bootloader, nothing will show up.
:::

1. Connect a data-capable USB-C cable from your computer to the **rear USB-C port** on the Spotykach PCB.
2. Put Spotykach into Daisy Bootloader DFU mode using either method:
   - **If already running Spotykach (or Lesson 0001+) firmware**: Hold the **Boot/Reset button** (`D2`) on the back of the unit for **$\ge 3$ seconds** until the bottom pad LEDs breathe smoothly in white.
   - **From power-off or hardware reset**: Press the hardware Reset button, then immediately hold the Boot button while the LEDs begin breathing white.
3. Flash the compiled `.bin` from your lesson directory:

```bash caption="Flash the BOOT_SRAM binary to QSPI flash via USB DFU"
make program-dfu
```

Turns out, `dfu-util` loves to complain with `Error during download get_status` at the exact millisecond the board resets itself into your new firmware at the end of the transfer — if the progress bar reached `100%`, the flash succeeded! =)
