#pragma once
#include "Arduino.h"
class Preferences {
 public:
  bool begin(const char*, bool readOnly = false) { (void)readOnly; return true; }
  void end() {}
  bool clear() { return true; }
  bool isKey(const char*) { return false; }
  float getFloat(const char*, float d = 0) { return d; }
  int getInt(const char*, int d = 0) { return d; }
  bool getBool(const char*, bool d = false) { return d; }
  uint32_t getUInt(const char*, uint32_t d = 0) { return d; }
  uint16_t getUShort(const char*, uint16_t d = 0) { return d; }
  size_t getString(const char*, char* out, size_t len) { if (len) out[0] = 0; return 0; }
  String getString(const char*, String d = String()) { return d; }
  size_t putFloat(const char*, float) { return 4; }
  size_t putInt(const char*, int) { return 4; }
  size_t putBool(const char*, bool) { return 1; }
  size_t putUInt(const char*, uint32_t) { return 4; }
  size_t putUShort(const char*, uint16_t) { return 2; }
  size_t putString(const char*, const char*) { return 1; }
  size_t putString(const char*, const String&) { return 1; }
};
