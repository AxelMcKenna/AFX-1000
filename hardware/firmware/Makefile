TARGET = rmx_standalone
PROFILE ?= onboard
ifeq ($(PROFILE),external)
TARGET = rmx_standalone_external
override BUILD_DIR = build-external
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
DSP_UNITS = Engine Primitives Sampler Isolator SceneEffects ReleaseEffects SampleBank
CPP_SOURCES = main.cpp Memory.cpp $(addprefix ../../src/core/,$(addsuffix .cpp,$(DSP_UNITS))) $(CPP_SOURCES_EXTRA)
C_INCLUDES = -I../../include
include $(LIBDAISY_DIR)/core/Makefile

# Weak startup handlers must not clobber FP state. Keep this flag local to C
# startup; the C++ DSP continues to use the Cortex-M7 floating-point unit.
$(BUILD_DIR)/startup_stm32h750xx.o: CFLAGS += -mgeneral-regs-only
