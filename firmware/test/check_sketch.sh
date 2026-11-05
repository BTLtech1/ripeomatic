#!/bin/sh
# Type-check the whole sketch with a desktop g++ against the API shim in test/shim.
# Catches typos and signature mistakes without an ESP32 toolchain. Not a build.
set -e
cd "$(dirname "$0")"
for v in 2 3; do
  g++ -std=gnu++17 -fsyntax-only -x c++ -Wall -Wextra -Wno-unused-parameter -Wno-unused-function \
      -DARDUINO=10819 -DESP_ARDUINO_VERSION_MAJOR_OVERRIDE=$v -I shim -I ../ripeomatic -include Arduino.h ../ripeomatic/ripeomatic.ino
done
echo "sketch type-checks OK (core 2.x and 3.x code paths)"
