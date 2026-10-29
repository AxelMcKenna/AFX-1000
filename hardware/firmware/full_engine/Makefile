TARGET = rmx_full_engine
PROFILE ?= onboard
ifeq ($(PROFILE),external)
TARGET = rmx_full_engine_external
override BUILD_DIR := $(if $(BUILD_DIR),$(BUILD_DIR),build-external)
C_DEFS += -DRMX_EXTERNAL_CONVERTER=1
CPP_SOURCES_EXTRA = ../ExternalAudio.cpp
else ifneq ($(PROFILE),onboard)
$(error PROFILE must be onboard or external)
endif
LIBDAISY_DIR ?= ../../../build-hardware/libDaisy
SYSTEM_FILES_DIR = $(LIBDAISY_DIR)/core
APP_TYPE = BOOT_SRAM
CPP_STANDARD = -std=gnu++20
OPT = -O3
DSP_UNITS = FactoryRelease Engine Scene Isolator CardSamples CardSettings ReverbDown ReverbUp drums/Kick drums/Snare drums/Clap drums/Hat
CPP_SOURCES = main.cpp Memory.cpp BootStorage.cpp KernelTransport.cpp ../BootCard.cpp $(addprefix ../../../src/core/,$(addsuffix .cpp,$(DSP_UNITS))) $(CPP_SOURCES_EXTRA)
C_DEFS += -DRMX_EMBEDDED_COMPRESSED_KERNELS=1
C_INCLUDES = -Iinclude -I../../../include -I..
C_SOURCES += $(LIBDAISY_DIR)/Middlewares/Third_Party/FatFs/src/option/ccsbcs.c
include $(LIBDAISY_DIR)/core/Makefile
CPPFLAGS += -fexceptions -frtti -funwind-tables
$(BUILD_DIR)/startup_stm32h750xx.o: CFLAGS += -mgeneral-regs-only
LDFLAGS += -T../StorageMemory.ld
$(BUILD_DIR)/$(TARGET).elf: ../StorageMemory.ld

$(BUILD_DIR)/FactoryRelease.o $(BUILD_DIR)/ReverbDown.o $(BUILD_DIR)/ReverbUp.o $(BUILD_DIR)/Kick.o $(BUILD_DIR)/Snare.o $(BUILD_DIR)/Clap.o $(BUILD_DIR)/Hat.o: CPPFLAGS += -ffp-contract=off
