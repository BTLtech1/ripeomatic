// BTL Ripe-O-Matic: the web server. Serves the embedded page and a small JSON API.
#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>
#include "config.h"
#include "settings.h"
#include "machine.h"
#include "ui.h"

class Web {
 public:
  WebServer server{80};

  void begin() {
    server.on("/", HTTP_GET, [this] { page(); });
    server.on("/index.html", HTTP_GET, [this] { page(); });
    server.on("/manifest.json", HTTP_GET, [this] { server.send_P(200, "application/manifest+json", UI_MANIFEST); });
    server.on("/icon.svg", HTTP_GET, [this] { server.sendHeader("Cache-Control", "max-age=86400"); server.send_P(200, "image/svg+xml", UI_ICON_SVG); });
    server.on("/sw.js", HTTP_GET, [this] { server.send_P(200, "application/javascript", UI_SW_JS); });

    server.on("/api/status", HTTP_GET, [this] { status(); });
    server.on("/api/live", HTTP_GET, [this] { live(); });
    server.on("/api/settings", HTTP_GET, [this] { json(200, settingsJson()); });
    server.on("/api/settings", HTTP_POST, [this] { saveSettings(); });
    server.on("/api/measure", HTTP_POST, [this] { startJob(Job::Measure); });
    server.on("/api/newfruit", HTTP_POST, [this] { if (M.busy()) return fail(409, "busy"); M.forgetFruit(); startJob(Job::Measure); });
    server.on("/api/abort", HTTP_POST, [this] { M.abort(); ok(); });
    server.on("/api/home", HTTP_POST, [this] { startJob(Job::Home); });
    server.on("/api/jog", HTTP_POST, [this] {
      float mm = server.arg("mm").toFloat();
      if (mm == 0 || fabsf(mm) > 20) return fail(400, "mm must be within +-20");
      startJob(Job::Jog, mm);
    });
    server.on("/api/tip", HTTP_POST, [this] {
#if ENABLE_SERVO
      startJob(Job::Tip);
#else
      fail(400, "servo not enabled in this build (config.h ENABLE_SERVO)");
#endif
    });
    server.on("/api/rate", HTTP_POST, [this] {
      String r = server.arg("r");
      if (r != "hard" && r != "firm" && r != "ready" && r != "perfect" && r != "overripe") return fail(400, "bad rating");
      if (!M.rate(r.c_str(), server.arg("cut").c_str(), server.arg("notes").c_str())) return fail(500, "log write failed");
      ok();
    });
    server.on("/api/cal/zero", HTTP_POST, [this] { if (M.busy()) return fail(409, "busy"); float raw = M.captureZero(); json(200, String("{\"ok\":true,\"raw\":") + raw + "}"); });
    server.on("/api/cal/mass", HTTP_POST, [this] {
      if (M.busy()) return fail(409, "busy");
      float g = server.arg("g").toFloat();
      const char* why;
      if (!M.captureMass(g, &why)) return fail(400, why);
      json(200, String("{\"ok\":true,\"n_per_count\":") + String(S.hall_n_per_count, 6) + "}");
    });
    server.on("/api/cal/clear", HTTP_POST, [this] { M.clearCalibration(); ok(); });
    // first-run checklist
    server.on("/api/ntfy/new", HTTP_POST, [this] { M.newNtfyTopic(); json(200, String("{\"ok\":true,\"topic\":\"") + S.ntfy_topic + "\"}"); });
    server.on("/api/alerts/discord", HTTP_POST, [this] {
      String url = server.arg("url"); url.trim();
      if (url.length() && !(url.startsWith("https://discord.com/api/webhooks/") || url.startsWith("https://discordapp.com/api/webhooks/"))) return fail(400, "that isn't a Discord webhook URL (it starts with https://discord.com/api/webhooks/)");
      if (url.length() >= sizeof S.discord_webhook) return fail(400, "URL too long");
      strlcpy(S.discord_webhook, url.c_str(), sizeof S.discord_webhook);
      if (url.length()) S.ntfy_ok = false;
      settingsSave(); ok();
    });
    server.on("/api/ntfy/test", HTTP_POST, [this] {
      if (!S.ntfy_topic[0] && !S.discord_webhook[0]) return fail(400, "set up phone alerts or a Discord webhook first");
      if (!M.net.online()) return fail(400, "not online");
      if (M.busy()) return fail(409, "busy");
      M.net.lastOk = false;
      M.queueNotify("Ripe-O-Matic says hi", "Alerts are working. You'll hear from me when the avocado is ready.");
      ok();   // sent from the job task; the page polls status.ntfy_ok
    });
    server.on("/api/motor/checked", HTTP_POST, [this] {
      String r = server.arg("ok");
      if (r == "0") { S.motor_invert = !S.motor_invert; S.motor_checked = false; }
      else S.motor_checked = true;
      settingsSave(); M.applySettings(); ok();
    });
    server.on("/api/cal/blade", HTTP_POST, [this] { startJob(Job::BladeCal); });
    server.on("/api/scan", HTTP_GET, [this] { scan(); });
    server.on("/api/wifi", HTTP_POST, [this] { wifi(); });
    server.on("/api/reset", HTTP_POST, [this] { reset(); });
    server.on("/api/reboot", HTTP_POST, [this] { ok(); delay(300); ESP.restart(); });
    server.on("/data.csv", HTTP_GET, [this] { csv(); });
    server.on("/generate_204", HTTP_GET, [this] { portalRedirect(); });   // Android captive portal probe
    server.on("/hotspot-detect.html", HTTP_GET, [this] { portalRedirect(); });  // iOS/macOS
    server.on("/connecttest.txt", HTTP_GET, [this] { portalRedirect(); });  // Windows
    server.onNotFound([this] { if (M.net.apMode) portalRedirect(); else server.send(404, "text/plain", "not found"); });
    server.begin();
  }

  void loop() { server.handleClient(); }

 private:
  void page() {
    server.sendHeader("Cache-Control", "no-cache");
    server.send_P(200, "text/html", UI_HTML);
  }

  void portalRedirect() {
    server.sendHeader("Location", String("http://") + WiFi.softAPIP().toString() + "/", true);
    server.send(302, "text/plain", "");
  }

  void json(int code, const String& body) {
    server.sendHeader("Cache-Control", "no-store");
    server.send(code, "application/json", body);
  }
  void ok() { json(200, "{\"ok\":true}"); }
  void fail(int code, const char* msg) { String b = "{\"ok\":false,\"error\":\""; jsonEscape(msg, b); b += "\"}"; json(code, b); }

  void startJob(Job j, float param = 0) {
    if (M.busy()) return fail(409, "busy: another job is running");
    if (!M.start(j, param)) return fail(500, M.error[0] ? M.error : "could not start");
    ok();
  }

  static void addNum(String& o, const char* k, float v, int d = 3) {
    char b[24]; snprintf(b, sizeof b, "%.*f", d, (double)v);
    o += "\""; o += k; o += "\":"; o += b; o += ",";
  }
  static void addStr(String& o, const char* k, const char* v) { o += "\""; o += k; o += "\":\""; jsonEscape(v, o); o += "\","; }
  static void addBool(String& o, const char* k, bool v) { o += "\""; o += k; o += "\":"; o += v ? "true" : "false"; o += ","; }
  static void addInt(String& o, const char* k, long v) { o += "\""; o += k; o += "\":"; o += (int)v; o += ","; }
  static void closeObj(String& o) { if (o.endsWith(",")) o.remove(o.length() - 1); o += "}"; }

  void status() {
    String o; o.reserve(1200);
    char ts[24]; Net::isoNow(ts, sizeof ts);
    o += "{";
    addStr(o, "fw", FW_VERSION); addStr(o, "hw", HW_VERSION); addStr(o, "device_id", S.device_id); addStr(o, "host", S.host);
    addStr(o, "ip", M.net.apMode ? WiFi.softAPIP().toString().c_str() : WiFi.localIP().toString().c_str());
    addBool(o, "ap_mode", M.net.apMode); addStr(o, "ap_ssid", M.net.apSsid);
    addInt(o, "rssi", M.net.online() ? WiFi.RSSI() : 0);
    addStr(o, "time", ts); addInt(o, "uptime_s", millis() / 1000);
    addStr(o, "job", jobName(M.job)); addStr(o, "stage", ripe::stageName(M.stage));
    addNum(o, "pos_mm", M.stepper.posMm(), 2);
    addNum(o, "force_n", M.busy() ? M.live_force : M.hall.readForce(16), 3);
    addNum(o, "raw", M.busy() ? M.live_raw : M.hall.readRaw(16), 0);
    addBool(o, "calibrated", S.cal_points[0] != 0);
    addNum(o, "n_per_count", S.hall_n_per_count, 6);
    addInt(o, "cal_points_n", M.calPointCount());
    addBool(o, "blade_calibrated", S.t.blade_k_n_per_mm > 0.01f);
    addBool(o, "setup_done", M.calibrated());
    addBool(o, "simulate", SIMULATE);
    addStr(o, "ntfy_topic", S.ntfy_topic); addBool(o, "ntfy_ok", S.ntfy_ok); addBool(o, "discord_set", S.discord_webhook[0] != 0); addBool(o, "notify_pending", M.pendingTitle[0] != 0); addBool(o, "notify_last_ok", M.net.lastOk);
    addBool(o, "motor_checked", S.motor_checked); addBool(o, "motor_invert", S.motor_invert);
    addBool(o, "online", M.net.online());
    addInt(o, "fruit_count", FR.counter);
    addNum(o, "blade_k", S.t.blade_k_n_per_mm, 2);
    addBool(o, "servo", ENABLE_SERVO);
    addInt(o, "log_bytes", M.store.logSize()); addInt(o, "fs_free", M.store.freeBytes());
    addInt(o, "next_auto_s", M.secondsToNextAuto());
    addStr(o, "error", M.error);

    // fruit
    char fid[16]; fruitId(fid, sizeof fid);
    o += "\"fruit\":{";
    addStr(o, "id", fid); addBool(o, "loaded", FR.loaded); addInt(o, "n", FR.n_readings);
    addNum(o, "first_k", FR.first_k); addNum(o, "last_k", FR.last_k);
    addNum(o, "first_contact", FR.first_contact_mm, 2); addNum(o, "last_contact", FR.last_contact_mm, 2);
    addInt(o, "start_epoch", FR.start_epoch);
    float days = M.elapsedDays();
    if (days >= 0) addNum(o, "elapsed_days", days, 2);
    float thr = M.thresholdNow();
    addNum(o, "threshold", thr, 3);
    addStr(o, "verdict", ripe::verdictName(FR.loaded ? ripe::judge(FR.last_k, FR.first_k, S.t) : ripe::Verdict::Unknown));
    addNum(o, "days_to_ripe", FR.loaded ? ripe::daysToRipe(FR.first_k, FR.last_k, days, thr) : -1, 1);
    addStr(o, "rating", FR.last_rating);
    addBool(o, "ripe_notified", FR.notified_ripe);
    closeObj(o); o += ",";

    // last reading
    o += "\"last\":{";
    addStr(o, "outcome", ripe::outcomeName(M.last.outcome)); addStr(o, "time", M.last.time);
    addNum(o, "k", M.last.k); addNum(o, "r2", M.last.r2); addNum(o, "squish", M.last.squish, 2);
    addNum(o, "contact", M.last.contact, 2); addNum(o, "force_max", M.last.force_max, 2); addInt(o, "n_points", M.last.n_points);
    closeObj(o);
    o += "}";
    json(200, o);
  }

  // The in-progress (or last) force-vs-squish curve.
  void live() {
    const ripe::Reading& r = M.core.reading();
    String o; o.reserve(64 + r.n_points * 14);
    o += "{";
    addStr(o, "stage", ripe::stageName(M.stage)); addNum(o, "pos", M.stepper.posMm(), 2); addNum(o, "force", M.live_force, 3);
    addNum(o, "k", r.stiffness_n_per_mm); addNum(o, "r2", r.r2);
    o += "\"pts\":[";
    int n = r.n_points;
    if (n > ripe::MAX_POINTS) n = ripe::MAX_POINTS;
    char b[32];
    for (int i = 0; i < n; i++) { snprintf(b, sizeof b, "%s[%.3f,%.3f]", i ? "," : "", r.squish[i], r.force[i]); o += b; }
    o += "]}";
    json(200, o);
  }

  void saveSettings() {
    if (M.busy()) return fail(409, "busy: settings can't change while the motor is moving");
    bool hostChanged = false;
    int unknown = 0;
    for (int i = 0; i < server.args(); i++) {
      String n = server.argName(i);
      if (n == "wifi_pass" || n == "wifi_ssid" || n == "device_id" || n == "discord_webhook" || n == "plain") continue;   // not through this route
      if (n == "host" && server.arg(i) != S.host) hostChanged = true;
      if (!settingsSet(n.c_str(), server.arg(i).c_str())) unknown++;
    }
    settingsSave();
    M.applySettings();
    String o = "{\"ok\":true,\"unknown\":" + String(unknown) + ",\"reboot_needed\":" + (hostChanged ? "true" : "false") + "}";
    json(200, o);
  }

  void scan() {
    int n = WiFi.scanNetworks();
    String o = "{\"networks\":[";
    for (int i = 0; i < n && i < 20; i++) {
      if (i) o += ",";
      o += "{\"ssid\":\""; jsonEscape(WiFi.SSID(i).c_str(), o); o += "\",\"rssi\":"; o += WiFi.RSSI(i);
      o += ",\"open\":"; o += WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "true" : "false"; o += "}";
    }
    o += "]}";
    WiFi.scanDelete();
    json(200, o);
  }

  void wifi() {
    String ssid = server.arg("ssid"), pass = server.arg("pass");
    if (!ssid.length()) return fail(400, "ssid required");
    bool sameNetwork = ssid == S.wifi_ssid;
    strlcpy(S.wifi_ssid, ssid.c_str(), sizeof S.wifi_ssid);
    // An empty password on the same network means "keep the old one".
    if (pass.length() || !sameNetwork) strlcpy(S.wifi_pass, pass.c_str(), sizeof S.wifi_pass);
    settingsSave();
    ok();
    delay(500);
    ESP.restart();
  }

  // Factory settings, but the device keeps its id so its contributed data stays one unit.
  static void clearSettingsKeepId() {
    Preferences p; p.begin("ripe", false); p.clear(); p.putString("dev_id", S.device_id); p.end();
  }

  void reset() {
    String what = server.arg("what");
    if (M.busy()) return fail(409, "busy");
    if (what == "fruit") { FR = FruitState(); fruitSave(); ok(); }
    else if (what == "data") { M.store.wipe(); FR = FruitState(); fruitSave(); ok(); }
    else if (what == "settings") { clearSettingsKeepId(); ok(); delay(300); ESP.restart(); }
    else if (what == "all") { M.store.wipe(); clearSettingsKeepId(); Preferences p; p.begin("fruit", false); p.clear(); p.end(); ok(); delay(300); ESP.restart(); }
    else fail(400, "what = fruit | data | settings | all");
  }

  // Streams the log. ?fruit=current (default) | all, &old=1 to include the rotated file.
  struct ChunkOut {
    WebServer& s; String buf;
    explicit ChunkOut(WebServer& sv) : s(sv) { buf.reserve(1500); }
    void print(const String& x) { buf += x; if (buf.length() > 1200) flush(); }
    void print(char c) { buf += c; if (buf.length() > 1200) flush(); }
    void flush() { if (buf.length()) { s.sendContent(buf); buf = ""; } }
  };

  void csv() {
    String fruit = server.arg("fruit");
    bool includeOld = server.arg("old") == "1";
    char prefix[16] = "";
    if (fruit != "all") fruitId(prefix, sizeof prefix);
    server.setContentLength(CONTENT_LENGTH_UNKNOWN);
    server.sendHeader("Cache-Control", "no-store");
    if (fruit == "all") server.sendHeader("Content-Disposition", String("attachment; filename=\"ripeomatic-") + S.device_id + ".csv\"");
    server.send(200, "text/csv", "");
    ChunkOut out(server);
    M.store.streamLog(out, prefix, includeOld);
    out.flush();
    server.sendContent("");   // end of chunked body
  }
};
