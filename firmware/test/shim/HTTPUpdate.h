#pragma once
#include <functional>
#include "WiFi.h"
enum t_httpUpdate_return { HTTP_UPDATE_FAILED, HTTP_UPDATE_NO_UPDATES, HTTP_UPDATE_OK };
class HTTPUpdate {
 public:
  void rebootOnUpdate(bool) {}
  void onProgress(std::function<void(int, int)>) {}
  t_httpUpdate_return update(WiFiClient&, const String&) { return HTTP_UPDATE_OK; }
  String getLastErrorString() { return String(""); }
};
extern HTTPUpdate httpUpdate;
