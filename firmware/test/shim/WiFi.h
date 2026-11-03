#pragma once
#include "Arduino.h"
enum { WL_CONNECTED = 3, WL_DISCONNECTED = 6 };
enum { WIFI_OFF = 0, WIFI_STA = 1, WIFI_AP = 2, WIFI_AP_STA = 3 };
enum wifi_auth_mode_t { WIFI_AUTH_OPEN = 0, WIFI_AUTH_WPA2_PSK = 3 };
class WiFiClient { public: bool connected() { return false; } };
class WiFiClass {
 public:
  void persistent(bool) {}
  bool setHostname(const char*) { return true; }
  bool mode(int) { return true; }
  int begin(const char*, const char* = nullptr) { return 0; }
  int status() { return WL_DISCONNECTED; }
  IPAddress localIP() { return IPAddress(); }
  IPAddress softAPIP() { return IPAddress(); }
  bool softAP(const char*, const char* = nullptr) { return true; }
  bool disconnect(bool = false) { return true; }
  int32_t RSSI() { return -60; }
  int32_t RSSI(uint8_t) { return -60; }
  int16_t scanNetworks() { return 0; }
  String SSID(uint8_t) { return String(); }
  wifi_auth_mode_t encryptionType(uint8_t) { return WIFI_AUTH_OPEN; }
  void scanDelete() {}
};
static WiFiClass WiFi;
