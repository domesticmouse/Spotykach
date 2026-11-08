# Spotykach Firmware Resources

## Knowledge

- [Spotykach Firmware Source of Truth (`README.md` & `src/`)](../README.md)
  Authoritative blueprint and production C++17 source tree (`main.cpp`, `app.cpp`, `src/hw/`, `src/ui/`, `src/core/`, `src/memory/`, `src/transfer/`) for the Synthux Academy Spotykach dual-deck hardware looper. Use for: exact pin mappings, memory linker scripts (`alt_sram.lds`), peripheral configurations, and real-time audio/UI invariants.
- [Workspace Skill: `libDaisy` Developer Guide (`.agents/skills/libdaisy-guide/SKILL.md`)](../.agents/skills/libdaisy-guide/SKILL.md)
  Comprehensive architectural reference for the Electro-Smith Daisy Seed (STM32H750IBK6 @ 480 MHz), memory sections (`DTCM`, `AXI SRAM`, `SRAM1` DMA buffers, `SDRAM`, `QSPI`), `BOOT_SRAM` bootloader workflow, and peripheral drivers (`AudioHandle`, `AdcHandle`, `DacHandle`, `GPIO`, `Switch`, `I2CHandle`, `TimerHandle`). Use for: verifying STM32H7 memory placement, DMA cache coherency rules, and `libDaisy` API semantics.
- [Workspace Skill: `DaisySP` Developer Guide & DSP Runbook (`.agents/skills/daisysp-guide/SKILL.md`)](../.agents/skills/daisysp-guide/SKILL.md)
  Operational runbook for real-time audio DSP in C++ on Cortex-M7, covering normalized float audio ranges (`[-1.0f, +1.0f]`), sample-rate lifecycle (`Init(sr)` -> `Process()`), filter/effect modules (`Svf`, `Overdrive`, `DelayLine`), and fast math helpers (`daisysp::fmap`, `pow10f`, `SoftClip`). Use for: designing real-time audio callbacks, smoothing parameters, and avoiding FPU/stack hazards.
- [Workspace Skill: Spotykach Submodules Guide (`.agents/skills/spotykach-submodules/SKILL.md`)](../.agents/skills/spotykach-submodules/SKILL.md)
  Lineage and patch reference for `lib/libDaisy` (`bleeptools/libDaisy` branch `origin/sk`, layered on `Infrasonic/libDaisy` `infs-mods` and `electro-smith/libDaisy` `v8.0.0`) and `lib/DaisySP`. Use for: understanding why `main.cpp` defines `USBD_MANUFACTURER_STRING` and `USBD_PRODUCT_STRING_HS`, how `TimerHandle::GetHALHandle()` powers the WS2812 DMA driver, and how `Mpr121` touch filtering is tuned for Spotykach pads.
- [cppreference.com — C++17 Standard Reference](https://en.cppreference.com/w/cpp/17)
  Authoritative reference for C++17 language features (`constexpr`, `enum class`, fixed-width integers in `<cstdint>`, `std::clamp`, deleted special member functions, and templates). Use for: verifying C++17 syntax, type guarantees, and zero-overhead abstractions used in bare-metal firmware.
- [STM32H750IB Reference Manual (RM0433) & Datasheet](https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
  Official STMicroelectronics hardware reference for the Cortex-M7 MCU inside the Daisy Seed, including memory bus matrices (AXI, AHB, APB1/APB2 timer clock doubling), SAI audio, DMA2, TIM3/TIM5, and FMC SDRAM. Use for: low-level timer clock divider calculations and DMA stream mapping.

## Wisdom (Communities)

- [Synthux Academy Discord & Community](https://synthux.academy/store/spotykach)
  Official community of instrument designers and firmware hackers building on Spotykach and Simple Touch hardware. Use for: sharing custom firmware modes, hardware calibration tips, and musical workflow feedback.
- [Electro-Smith Daisy Forum](https://forum.electro-smith.com/)
  Official moderated forum for `libDaisy`, `DaisySP`, and STM32H7 embedded audio development. Use for: troubleshooting `BOOT_SRAM` linker questions, SAI audio latency, and DMA peripheral edge cases.
