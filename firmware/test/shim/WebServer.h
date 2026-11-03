#pragma once
#include "Arduino.h"
enum HTTPMethod { HTTP_ANY, HTTP_GET, HTTP_POST, HTTP_PUT, HTTP_DELETE };
#define CONTENT_LENGTH_UNKNOWN ((size_t)-1)
class WebServer {
 public:
  typedef std::function<void(void)> THandlerFunction;
  explicit WebServer(int = 80) {}
  void on(const char*, THandlerFunction) {}
  void on(const char*, HTTPMethod, THandlerFunction) {}
  void onNotFound(THandlerFunction) {}
  void begin() {}
  void handleClient() {}
  void send(int, const char*, const String&) {}
  void send(int, const char*, const char*) {}
  void send_P(int, const char*, const char*) {}
  void sendHeader(const String&, const String&, bool first = false) { (void)first; }
  void sendContent(const String&) {}
  void setContentLength(size_t) {}
  String arg(const char*) { return String(); }
  String arg(int) { return String(); }
  String argName(int) { return String(); }
  int args() { return 0; }
};
