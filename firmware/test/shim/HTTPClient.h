#pragma once
#include "WiFi.h"
class HTTPClient {
 public:
  bool begin(WiFiClient&, const String&) { return true; }
  void addHeader(const String&, const String&) {}
  void setTimeout(uint16_t) {}
  int POST(uint8_t*, size_t) { return 200; }
  int POST(const String&) { return 200; }
  void end() {}
};
