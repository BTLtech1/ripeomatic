#pragma once
#include "Arduino.h"
class ArduinoOTAClass { public: void setHostname(const char*) {} void onStart(std::function<void(void)>) {} void begin() {} void handle() {} };
static ArduinoOTAClass ArduinoOTA;
