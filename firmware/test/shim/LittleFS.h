#pragma once
#include "Arduino.h"
class File {
 public:
  operator bool() const { return ok_; }
  size_t size() const { return 0; }
  void close() {}
  int available() { return 0; }
  String readStringUntil(char) { return String(); }
  size_t println(const char*) { return 0; }
  size_t println(const String&) { return 0; }
  size_t print(const String&) { return 0; }
  bool ok_ = true;
};
class LittleFSClass {
 public:
  bool begin(bool formatOnFail = false, const char* base = "/littlefs", uint8_t maxFiles = 10, const char* label = "spiffs") { (void)formatOnFail; (void)base; (void)maxFiles; (void)label; return true; }
  bool exists(const char*) { return true; }
  File open(const char*, const char* mode = "r") { (void)mode; return File(); }
  bool remove(const char*) { return true; }
  bool rename(const char*, const char*) { return true; }
  size_t totalBytes() { return 1500000; }
  size_t usedBytes() { return 0; }
};
static LittleFSClass LittleFS;
