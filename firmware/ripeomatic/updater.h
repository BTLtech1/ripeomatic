// BTL Ripe-O-Matic: firmware updates over Wi-Fi from the GitHub Pages build.
//
// Every push to main builds the firmware in CI and publishes it next to the web
// installer, with a manifest naming the commit it was built from. The device
// knows its own commit (FW_BUILD, written into build_id.h by CI), so "check"
// compares the two and "update" downloads the app image into the spare OTA
// slot and restarts into it. NVS (Wi-Fi, settings, calibration, home) and the
// log on LittleFS are untouched.
//
// TLS is not verified (no CA bundle on the board), the same as the ntfy push:
// someone already on your Wi-Fi could in principle serve a fake image.
#pragma once
#include <Arduino.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <WiFiClientSecure.h>
#include "config.h"

class Updater {
 public:
  volatile int pct = -1;
  char state[12] = "";      // "", checking, uptodate, available, downloading, done, failed
  char latest[40] = "";     // the published build, e.g. "2026-11-12 · 36c1cce"
  char latestId[12] = "";
  char err[72] = "";

  bool check() {
    set("checking"); err[0] = 0;
    WiFiClientSecure c; c.setInsecure();
    HTTPClient http;
    if (!http.begin(c, String(UPDATE_MANIFEST_URL))) return fail("couldn't reach GitHub");
    http.setTimeout(10000);
    int code = http.GET();
    if (code != 200) { http.end(); snprintf(err, sizeof err, "GitHub answered %d", code); set("failed"); return false; }
    String body = http.getString();
    http.end();
    if (!field(body, "build_id", latestId, sizeof latestId)) return fail("the published build has no build_id yet");
    if (!field(body, "build", latest, sizeof latest)) strlcpy(latest, latestId, sizeof latest);
    set(strcmp(latestId, FW_BUILD) == 0 ? "uptodate" : "available");
    return true;
  }

  bool run() {
    set("downloading"); pct = 0; err[0] = 0;
    WiFiClientSecure c; c.setInsecure();
    httpUpdate.rebootOnUpdate(false);
    httpUpdate.onProgress([this](int cur, int total) { if (total > 0) pct = (int)(100LL * cur / total); });
    t_httpUpdate_return r = httpUpdate.update(c, String(UPDATE_BIN_URL));
    if (r == HTTP_UPDATE_OK) { pct = 100; set("done"); return true; }
    strlcpy(err, r == HTTP_UPDATE_NO_UPDATES ? "no update offered" : httpUpdate.getLastErrorString().c_str(), sizeof err);
    set("failed");
    return false;
  }

 private:
  void set(const char* s) { strlcpy(state, s, sizeof state); }
  bool fail(const char* m) { strlcpy(err, m, sizeof err); set("failed"); return false; }
  // "key": "value" from a small, known JSON file
  static bool field(const String& j, const char* key, char* out, size_t n) {
    int i = j.indexOf(String("\"") + key + "\"");
    if (i < 0) return false;
    i = j.indexOf(':', i); if (i < 0) return false;
    i = j.indexOf('"', i); if (i < 0) return false;
    int e = j.indexOf('"', i + 1); if (e < 0) return false;
    strlcpy(out, j.substring(i + 1, e).c_str(), n);
    return true;
  }
};
