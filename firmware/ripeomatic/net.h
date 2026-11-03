// BTL Ripe-O-Matic: Wi-Fi (with a setup access point), mDNS, NTP time, ntfy push.
#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <DNSServer.h>
#include <time.h>
#include "config.h"
#include "settings.h"

class Net {
 public:
  bool apMode = false;

  // Try the stored network; fall back to an open setup AP.
  void begin() {
    WiFi.persistent(false);
    WiFi.setHostname(S.host);
    if (S.wifi_ssid[0]) {
      WiFi.mode(WIFI_STA);
      WiFi.begin(S.wifi_ssid, S.wifi_pass);
      uint32_t t0 = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_CONNECT_TIMEOUT_MS) delay(100);
    }
    if (WiFi.status() == WL_CONNECTED) {
      apMode = false;
      Serial.printf("Wi-Fi: %s  http://%s.local  %s\n", S.wifi_ssid, S.host, WiFi.localIP().toString().c_str());
      if (MDNS.begin(S.host)) MDNS.addService("http", "tcp", 80);
      configTzTime("UTC0", NTP_SERVER);
    } else {
      startAp();
    }
  }

  void startAp() {
    apMode = true;
    snprintf(apSsid, sizeof apSsid, "%s%s", AP_SSID_PREFIX, S.device_id);
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(apSsid);
    delay(100);
    dns.start(53, "*", WiFi.softAPIP());
    Serial.printf("Setup AP: %s  http://%s/\n", apSsid, WiFi.softAPIP().toString().c_str());
  }

  void loop() {
    if (apMode) dns.processNextRequest();
    // Reconnect if the router dropped us.
    else if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect > 30000) {
      lastReconnect = millis();
      WiFi.disconnect();
      WiFi.begin(S.wifi_ssid, S.wifi_pass);
    }
  }

  bool online() const { return !apMode && WiFi.status() == WL_CONNECTED; }

  // Unix time, or 0 if NTP hasn't set the clock.
  static uint32_t epoch() {
    time_t now = time(nullptr);
    return now > 1600000000 ? (uint32_t)now : 0;
  }

  // "2026-11-09T07:30:12Z", or "" if the clock isn't set.
  static void isoNow(char* out, int len) {
    time_t now = time(nullptr);
    if (now < 1600000000) { out[0] = 0; return; }
    struct tm tm;
    gmtime_r(&now, &tm);
    strftime(out, len, "%Y-%m-%dT%H:%M:%SZ", &tm);
  }

  // Push a notification through ntfy (https://ntfy.sh). Returns true on 2xx.
  // priority 1-5; tags are emoji shortcodes, e.g. "avocado".
  bool ntfy(const char* title, const char* message, int priority = 3, const char* tags = "avocado") {
    if (!online() || !S.ntfy_topic[0]) return false;
    String url = String(S.ntfy_server) + "/" + S.ntfy_topic;
    HTTPClient http;
    bool ok = false;
    if (url.startsWith("https://")) {
      WiFiClientSecure client;
      client.setInsecure();   // no CA bundle on board; a spoofed ntfy only ever learns "your avocado is ripe"
      ok = http.begin(client, url);
      if (ok) ok = post(http, title, message, priority, tags);
    } else {
      WiFiClient client;
      ok = http.begin(client, url);
      if (ok) ok = post(http, title, message, priority, tags);
    }
    http.end();
    return ok;
  }

  char apSsid[40] = "";

 private:
  bool post(HTTPClient& http, const char* title, const char* message, int priority, const char* tags) {
    http.addHeader("Title", title);
    http.addHeader("Priority", String(priority));
    http.addHeader("Tags", tags);
    http.setTimeout(8000);
    int code = http.POST((uint8_t*)message, strlen(message));
    Serial.printf("ntfy %d: %s\n", code, title);
    return code >= 200 && code < 300;
  }

  DNSServer dns;
  uint32_t lastReconnect = 0;
};
