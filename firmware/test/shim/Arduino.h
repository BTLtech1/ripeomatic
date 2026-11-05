// Minimal Arduino-ESP32 API shim so the sketch can be type-checked with a desktop g++.
// Not a simulator: nothing here does anything. Signatures mirror the real core.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <string>
#include <functional>

#define PROGMEM
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define ADC_11db 3

inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 1; }
inline int analogRead(int) { return 2048; }
inline void analogReadResolution(int) {}
inline void analogSetPinAttenuation(int, int) {}
inline uint32_t millis() { return 0; }
inline uint32_t micros() { return 0; }
inline void delay(uint32_t) {}
inline void delayMicroseconds(uint32_t) {}
inline uint32_t esp_random() { return 4; }
inline size_t strlcpy(char* d, const char* s, size_t n) { if (n) { strncpy(d, s, n - 1); d[n - 1] = 0; } return strlen(s); }

// LEDC (both API generations)
inline bool ledcAttach(uint8_t, uint32_t, uint8_t) { return true; }
inline double ledcSetup(uint8_t, double, uint8_t) { return 0; }
inline void ledcAttachPin(uint8_t, uint8_t) {}
inline void ledcWrite(uint8_t, uint32_t) {}

class String {
 public:
  String() {}
  String(const char* s) : s_(s ? s : "") {}
  String(const std::string& s) : s_(s) {}
  String(char c) : s_(1, c) {}
  String(int v) : s_(std::to_string(v)) {}
  String(unsigned v) : s_(std::to_string(v)) {}
  String(long v) : s_(std::to_string(v)) {}
  String(unsigned long v) : s_(std::to_string(v)) {}
  String(float v, int digits = 2) { char b[32]; snprintf(b, sizeof b, "%.*f", digits, (double)v); s_ = b; }
  String(double v, int digits = 2) { char b[32]; snprintf(b, sizeof b, "%.*f", digits, v); s_ = b; }
  unsigned length() const { return (unsigned)s_.size(); }
  const char* c_str() const { return s_.c_str(); }
  void reserve(unsigned) {}
  String& operator+=(const String& o) { s_ += o.s_; return *this; }
  String& operator+=(const char* o) { s_ += o ? o : ""; return *this; }
  String& operator+=(char c) { s_ += c; return *this; }
  String& operator+=(int v) { s_ += std::to_string(v); return *this; }
  String& operator+=(unsigned v) { s_ += std::to_string(v); return *this; }
  String& operator+=(long v) { s_ += std::to_string(v); return *this; }
  String& operator+=(unsigned long v) { s_ += std::to_string(v); return *this; }
  String& operator+=(float v) { s_ += String(v).s_; return *this; }
  String& operator+=(double v) { s_ += String(v).s_; return *this; }
  bool operator==(const String& o) const { return s_ == o.s_; }
  bool operator==(const char* o) const { return s_ == (o ? o : ""); }
  bool operator!=(const String& o) const { return !(*this == o); }
  bool operator!=(const char* o) const { return !(*this == o); }
  char operator[](unsigned i) const { return i < s_.size() ? s_[i] : 0; }
  bool startsWith(const String& p, unsigned off = 0) const { return s_.compare(off, p.s_.size(), p.s_) == 0; }
  bool endsWith(const String& p) const { return s_.size() >= p.s_.size() && s_.compare(s_.size() - p.s_.size(), p.s_.size(), p.s_) == 0; }
  void remove(unsigned idx) { if (idx < s_.size()) s_.erase(idx); }
  void remove(unsigned idx, unsigned n) { if (idx < s_.size()) s_.erase(idx, n); }
  float toFloat() const { return (float)atof(s_.c_str()); }
  int toInt() const { return atoi(s_.c_str()); }
  int indexOf(char c) const { auto p = s_.find(c); return p == std::string::npos ? -1 : (int)p; }
  std::string s_;
};
template <typename T> inline String operator+(String a, const T& b) { a += b; return a; }
inline String operator+(const char* a, const String& b) { return String(a) + b; }

class Print {
 public:
  void begin(unsigned long) {}
  template <typename... A> int printf(const char* f, A... a) { return ::printf(f, a...); }
  void println(const char* s) { ::printf("%s\n", s); }
  void println(const String& s) { ::printf("%s\n", s.c_str()); }
  void println() { ::printf("\n"); }
  void print(const char* s) { ::printf("%s", s); }
  void print(const String& s) { ::printf("%s", s.c_str()); }
  void print(char c) { ::printf("%c", c); }
  int available() { return 0; }
  int read() { return -1; }
  size_t write(const uint8_t*, size_t n) { return n; }
  size_t write(uint8_t) { return 1; }
  void flush() {}
};
static Print Serial;

class IPAddress {
 public:
  String toString() const { return "0.0.0.0"; }
};

class EspClass {
 public:
  void restart() {}
};
static EspClass ESP;

// FreeRTOS
typedef void* TaskHandle_t;
typedef int BaseType_t;
#define pdPASS 1
typedef void (*TaskFunction_t)(void*);
inline BaseType_t xTaskCreatePinnedToCore(TaskFunction_t, const char*, uint32_t, void*, unsigned, TaskHandle_t*, int) { return pdPASS; }
inline void vTaskDelete(TaskHandle_t) {}

// time
#include <time.h>
inline void configTzTime(const char*, const char*) {}
