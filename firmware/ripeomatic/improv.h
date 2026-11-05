// BTL Ripe-O-Matic: Improv Wi-Fi over serial (https://www.improv-wifi.com/serial/).
// Lets the web installer set Wi-Fi right after flashing, over the same USB
// cable, and then show a "Visit device" link. No library; the protocol is a
// few dozen lines. The framing/checksum part is plain C++ (host-tested in
// ../test/test_improv.cpp); the Wi-Fi part is in ImprovSerial below.
#pragma once
#include <stdint.h>
#include <string.h>

namespace improv {

enum Type : uint8_t { CURRENT_STATE = 0x01, ERROR_STATE = 0x02, RPC_COMMAND = 0x03, RPC_RESULT = 0x04 };
enum State : uint8_t { STATE_AUTHORIZED = 0x02, STATE_PROVISIONING = 0x03, STATE_PROVISIONED = 0x04 };
enum Error : uint8_t { ERR_NONE = 0x00, ERR_INVALID_RPC = 0x01, ERR_UNKNOWN_RPC = 0x02, ERR_UNABLE_TO_CONNECT = 0x03, ERR_UNKNOWN = 0xFF };
enum Command : uint8_t { CMD_WIFI_SETTINGS = 0x01, CMD_GET_STATE = 0x02, CMD_GET_DEVICE_INFO = 0x03, CMD_GET_NETWORKS = 0x04 };

static const uint8_t HEADER[6] = {'I', 'M', 'P', 'R', 'O', 'V'};
static const uint8_t VERSION = 1;
static const int MAX_DATA = 255;

// Build a packet into out (>= 6+3+len+1 bytes). Returns total length.
inline int encode(uint8_t type, const uint8_t* data, int len, uint8_t* out) {
  int n = 0;
  memcpy(out, HEADER, 6); n = 6;
  out[n++] = VERSION;
  out[n++] = type;
  out[n++] = (uint8_t)len;
  memcpy(out + n, data, len); n += len;
  uint8_t sum = 0;
  for (int i = 0; i < n; i++) sum += out[i];
  out[n++] = sum;
  return n;
}

// Encode an RPC result: command + a list of strings (each length-prefixed).
inline int encodeResult(uint8_t command, const char* const* strings, int count, uint8_t* out) {
  uint8_t data[MAX_DATA];
  int n = 0;
  data[n++] = command;
  data[n++] = 0;   // payload length, filled below
  for (int i = 0; i < count; i++) {
    int l = (int)strlen(strings[i]);
    if (n + 1 + l > MAX_DATA) break;
    data[n++] = (uint8_t)l;
    memcpy(data + n, strings[i], l); n += l;
  }
  data[1] = (uint8_t)(n - 2);
  return encode(RPC_RESULT, data, n, out);
}

// Byte-at-a-time packet assembler. feed() returns true when a full, valid
// packet is ready in type/data/len.
class Parser {
 public:
  uint8_t type = 0;
  uint8_t data[MAX_DATA];
  int len = 0;

  bool feed(uint8_t b) {
    if (pos_ < 6) {                      // header
      if (b == HEADER[pos_]) { pos_++; return false; }
      pos_ = (b == HEADER[0]) ? 1 : 0;   // resync
      return false;
    }
    if (pos_ == 6) { if (b != VERSION) { pos_ = 0; return false; } sum_ = headerSum() + b; pos_++; return false; }
    if (pos_ == 7) { type = b; sum_ += b; pos_++; return false; }
    if (pos_ == 8) { len = b; sum_ += b; got_ = 0; pos_++; if (len == 0) pos_ = 9; return false; }
    if (got_ < len) { data[got_++] = b; sum_ += b; return false; }
    // checksum byte
    bool ok = (b == sum_);
    pos_ = 0;
    return ok;
  }

 private:
  static uint8_t headerSum() { uint8_t s = 0; for (int i = 0; i < 6; i++) s += HEADER[i]; return s; }
  int pos_ = 0, got_ = 0;
  uint8_t sum_ = 0;
};

// Decode the Wi-Fi settings command payload: [ssid_len][ssid][pass_len][pass].
inline bool parseWifiSettings(const uint8_t* data, int len, char* ssid, int ssidMax, char* pass, int passMax) {
  if (len < 2 || data[0] != CMD_WIFI_SETTINGS) return false;
  int payload = data[1], p = 2;
  if (payload + 2 > len || payload < 2) return false;
  int sl = data[p++];
  if (sl + 1 > payload || sl >= ssidMax) return false;
  memcpy(ssid, data + p, sl); ssid[sl] = 0; p += sl;
  int pl = data[p++];
  if (p + pl > len || pl >= passMax) return false;
  memcpy(pass, data + p, pl); pass[pl] = 0;
  return true;
}

}  // namespace improv

#ifdef ARDUINO
#include <Arduino.h>
#include <WiFi.h>
#include "config.h"
#include "settings.h"

// Listens on Serial and answers the installer. Call loop() from loop().
class ImprovSerial {
 public:
  void loop() {
    while (Serial.available()) {
      if (parser_.feed((uint8_t)Serial.read())) handle();
    }
  }

 private:
  void send(uint8_t type, const uint8_t* data, int len) {
    uint8_t buf[6 + 3 + improv::MAX_DATA + 1];
    int n = improv::encode(type, data, len, buf);
    Serial.write(buf, n);
    Serial.flush();
  }
  void sendState(uint8_t s) { send(improv::CURRENT_STATE, &s, 1); }
  void sendError(uint8_t e) { send(improv::ERROR_STATE, &e, 1); }
  void sendResult(uint8_t cmd, const char* const* strings, int count) {
    uint8_t buf[6 + 3 + improv::MAX_DATA + 1];
    int n = improv::encodeResult(cmd, strings, count, buf);
    Serial.write(buf, n);
    Serial.flush();
  }
  uint8_t state() const { return WiFi.status() == WL_CONNECTED ? improv::STATE_PROVISIONED : improv::STATE_AUTHORIZED; }
  void deviceUrl(char* out, int len) {
    if (WiFi.status() == WL_CONNECTED) snprintf(out, len, "http://%s/", WiFi.localIP().toString().c_str());
    else snprintf(out, len, "http://%s.local/", S.host);
  }

  void handle() {
    if (parser_.type != improv::RPC_COMMAND || parser_.len < 2) { sendError(improv::ERR_INVALID_RPC); return; }
    uint8_t cmd = parser_.data[0];
    switch (cmd) {
      case improv::CMD_GET_STATE: {
        sendState(state());
        if (state() == improv::STATE_PROVISIONED) { char url[48]; deviceUrl(url, sizeof url); const char* s[] = {url}; sendResult(cmd, s, 1); }
        break;
      }
      case improv::CMD_GET_DEVICE_INFO: {
        char name[40]; snprintf(name, sizeof name, "Ripe-O-Matic %s", S.device_id);
        const char* s[] = {"BTL Ripe-O-Matic", FW_VERSION, "ESP32", name};
        sendResult(cmd, s, 4);
        break;
      }
      case improv::CMD_GET_NETWORKS: {
        int n = WiFi.scanNetworks();
        for (int i = 0; i < n && i < 15; i++) {
          char rssi[8]; snprintf(rssi, sizeof rssi, "%d", (int)WiFi.RSSI(i));
          String ssid = WiFi.SSID(i);
          const char* s[] = {ssid.c_str(), rssi, WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "NO" : "YES"};
          sendResult(cmd, s, 3);
        }
        WiFi.scanDelete();
        sendResult(cmd, nullptr, 0);   // end of list
        break;
      }
      case improv::CMD_WIFI_SETTINGS: {
        char ssid[33], pass[65];
        if (!improv::parseWifiSettings(parser_.data, parser_.len, ssid, sizeof ssid, pass, sizeof pass)) { sendError(improv::ERR_INVALID_RPC); return; }
        sendState(improv::STATE_PROVISIONING);
        WiFi.mode(WIFI_AP_STA);
        WiFi.begin(ssid, pass);
        uint32_t t0 = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) delay(100);
        if (WiFi.status() != WL_CONNECTED) { sendError(improv::ERR_UNABLE_TO_CONNECT); sendState(improv::STATE_AUTHORIZED); return; }
        strlcpy(S.wifi_ssid, ssid, sizeof S.wifi_ssid);
        strlcpy(S.wifi_pass, pass, sizeof S.wifi_pass);
        settingsSave();
        sendState(improv::STATE_PROVISIONED);
        char url[48]; deviceUrl(url, sizeof url);
        const char* s[] = {url};
        sendResult(cmd, s, 1);
        delay(500);        // let the installer read the result before we reboot into station mode
        ESP.restart();
        break;
      }
      default:
        sendError(improv::ERR_UNKNOWN_RPC);
    }
  }

  improv::Parser parser_;
};
#endif
