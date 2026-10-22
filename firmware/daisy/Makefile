# Requires libDaisy and Arm GNU Toolchain (GCC 12+ with C++20/PMR).
# Pinned versions and checksums are in dependencies.lock.json.
-include ../../.tools/firmware-env.mk
TARGET = rmx_seed
LIBDAISY_DIR ?= ../../.tools/libDaisy-8.1.0
SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
APP_TYPE = BOOT_QSPI
CPP_SOURCES = main.cpp CardStorage.cpp ../../src/core/CardSamples.cpp ../../src/core/CardSettings.cpp ../../src/core/Engine.cpp ../../src/core/Isolator.cpp ../../src/core/Scene.cpp
USE_FATFS = 1
C_INCLUDES = -I../../include -I../../hardware/generated
CPP_STANDARD = -std=gnu++20
OPT = -O3
include $(SYSTEM_FILES_DIR)/Makefile
# The bounded SDRAM resource reports exhaustion via bad_alloc at startup.
# Keep this recursively expanded: CFLAGS contains $@ for each object's .d file.
# Eager expansion loses header dependencies and can mix incompatible class sizes.
# GCC's final option wins over the SDK's earlier -fno-* defaults.
CPPFLAGS += -fexceptions -frtti -funwind-tables
