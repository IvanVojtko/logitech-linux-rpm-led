SCS_SDK_DIR ?= ../scs_sdk_1_14

SDK_INCLUDES := \
	-I$(SCS_SDK_DIR)/include \
	-I$(SCS_SDK_DIR)/include/common \
	-I$(SCS_SDK_DIR)/include/eurotrucks2 \
	-I$(SCS_SDK_DIR)/include/amtrucks

PLUGIN_SOURCE := logitech_rpm_telemetry.cpp
LINUX_PLUGIN := logitech_rpm_telemetry.so
WINDOWS_PLUGIN := logitech_rpm_telemetry.dll

LINUX_CXX ?= g++
WINDOWS_CXX ?= x86_64-w64-mingw32-g++

COMMON_CXXFLAGS ?= -O2 -Wall -Wextra
LINUX_CXXFLAGS ?= -fPIC
WINDOWS_CXXFLAGS ?=

.PHONY: all linux windows clean

all: linux windows

linux: $(LINUX_PLUGIN)

windows: $(WINDOWS_PLUGIN)

$(LINUX_PLUGIN): $(PLUGIN_SOURCE)
	$(LINUX_CXX) -o $@ --shared $(COMMON_CXXFLAGS) $(LINUX_CXXFLAGS) -Wl,-soname,$@ $(SDK_INCLUDES) $<

$(WINDOWS_PLUGIN): $(PLUGIN_SOURCE)
	$(WINDOWS_CXX) -o $@ --shared $(COMMON_CXXFLAGS) $(WINDOWS_CXXFLAGS) $(SDK_INCLUDES) $< -lws2_32

clean:
	rm -f -- $(LINUX_PLUGIN) $(WINDOWS_PLUGIN)
