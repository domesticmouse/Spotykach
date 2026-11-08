TARGET = spotykach_l01

CPP_STANDARD = -std=c++17

REPO_ROOT = ../../..
LIBDAISY_DIR = $(REPO_ROOT)/lib/libDaisy
DAISYSP_DIR = $(REPO_ROOT)/lib/DaisySP

APP_TYPE = BOOT_SRAM
LDSCRIPT = $(REPO_ROOT)/alt_sram.lds
BOOT_BIN = $(REPO_ROOT)/bootloader-spotykach-v2.bin

C_INCLUDES = -I.
LDFLAGS += -Wl,--no-warn-rwx-segments

CPP_SOURCES = \
	main.cpp \
	app.cpp

SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
include $(SYSTEM_FILES_DIR)/Makefile

HOST_CXX ?= c++
HOST_CXXFLAGS = -std=c++17 -Wall -Wextra -Werror -pedantic -I.

.PHONY: test
test:
	@mkdir -p $(BUILD_DIR)
	$(HOST_CXX) $(HOST_CXXFLAGS) tests/test_boot.cpp -o $(BUILD_DIR)/test_boot
	./$(BUILD_DIR)/test_boot
