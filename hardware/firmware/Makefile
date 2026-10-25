TARGET = rmx_standalone
PROFILE ?= onboard
ifeq ($(PROFILE),external)
TARGET = rmx_standalone_external
override BUILD_DIR := $(if $(BUILD_DIR),$(BUILD_DIR),build-external)
C_DEFS += -DRMX_EXTERNAL_CONVERTER=1
CPP_SOURCES_EXTRA = ExternalAudio.cpp
else ifneq ($(PROFILE),onboard)
$(error PROFILE must be onboard or external)
endif
LIBDAISY_DIR ?= ../../build-hardware/libDaisy
SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
APP_TYPE = BOOT_SRAM
CPP_STANDARD = -std=gnu++20
OPT = -O3
DSP_UNITS = Engine Primitives Sampler Isolator SceneEffects ReleaseEffects SampleBank BootStorage
CPP_SOURCES = main.cpp Memory.cpp BootCard.cpp $(addprefix ../runtime/src/core/,$(addsuffix .cpp,$(DSP_UNITS))) $(CPP_SOURCES_EXTRA)
C_INCLUDES = -I../runtime/include
# The SDK archive includes FatFs core, but not its configured code-page helpers.
C_SOURCES += $(LIBDAISY_DIR)/Middlewares/Third_Party/FatFs/src/option/ccsbcs.c
include $(LIBDAISY_DIR)/core/Makefile

# Weak startup handlers must not clobber FP state. Keep this flag local to C
# startup; the C++ DSP continues to use the Cortex-M7 floating-point unit.
$(BUILD_DIR)/startup_stm32h750xx.o: CFLAGS += -mgeneral-regs-only

# SDMMC1 file/sector buffers must remain in AXI SRAM, never DTCM.
LDFLAGS += -TStorageMemory.ld
$(BUILD_DIR)/$(TARGET).elf: StorageMemory.ld
