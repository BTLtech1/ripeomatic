// BTL Ripe-O-Matic: persistent settings (NVS via Preferences) and fruit state.
#pragma once
#include <Arduino.h>
#include <Preferences.h>
#if __has_include(<esp_random.h>)
#include <esp_random.h>   // esp_random() moved here in IDF 5 (Arduino core 3.x)
#endif
#include "config.h"
#include "measure.h"

// ---- Settings ---------------------------------------------------------------
struct Settings {
  // identity / network
  char device_id[8]   = "";            // 6 hex chars, generated on first boot
  char host[32]       = "ripeomatic";  // mDNS name: http://ripeomatic.local
  char wifi_ssid[33]  = "";
  char wifi_pass[65]  = "";
  // notifications
  char ntfy_server[64] = "https://ntfy.sh";
  char ntfy_topic[48]  = "";
  bool notify_nearly   = true;
  // fruit
  char variety[24]     = "hass";
  // schedule
  bool  auto_enabled   = true;
  float interval_h     = 12.0f;
  // motion
  float steps_per_mm   = DEFAULT_STEPS_PER_MM;
  bool  motor_invert   = false;        // flip if "jog +" moves the sled away from the nest
  float fast_mm_s      = DEFAULT_FAST_MM_S;
  float creep_mm_s     = DEFAULT_CREEP_MM_S;
  // force sensing
  float hall_n_per_count = 0.0035f;    // GUESS until calibrated (sign included)
  float cal_zero_counts  = 0;          // raw counts with nothing on the pad during calibration
  char  cal_points[64]   = "";         // "grams:counts;grams:counts" captured during calibration
  // the measurement routine
  ripe::Tunables t;
  // v2 servo
  int   servo_rest_deg = 0;
  int   servo_tip_deg  = 110;
  int   servo_hold_ms  = 1500;
};

extern Settings S;

// One line per field: web/JSON name, NVS key (<= 15 chars!), type, pointer.
enum FieldType : uint8_t { F_FLOAT, F_INT, F_BOOL, F_STR };
struct FieldDef {
  const char* name;
  const char* key;
  FieldType type;
  void* ptr;
  uint16_t len;      // for F_STR
  bool secret;       // never sent to the browser
};

inline const FieldDef* settingsFields(int& count) {
  static FieldDef f[] = {
    {"device_id",         "dev_id",   F_STR,   S.device_id,          sizeof S.device_id,   false},
    {"host",              "host",     F_STR,   S.host,               sizeof S.host,        false},
    {"wifi_ssid",         "ssid",     F_STR,   S.wifi_ssid,          sizeof S.wifi_ssid,   false},
    {"wifi_pass",         "pass",     F_STR,   S.wifi_pass,          sizeof S.wifi_pass,   true},
    {"ntfy_server",       "ntfy_srv", F_STR,   S.ntfy_server,        sizeof S.ntfy_server, false},
    {"ntfy_topic",        "ntfy_top", F_STR,   S.ntfy_topic,         sizeof S.ntfy_topic,  false},
    {"notify_nearly",     "ntf_near", F_BOOL,  &S.notify_nearly,     0, false},
    {"variety",           "variety",  F_STR,   S.variety,            sizeof S.variety,     false},
    {"auto_enabled",      "auto",     F_BOOL,  &S.auto_enabled,      0, false},
    {"interval_h",        "interval", F_FLOAT, &S.interval_h,        0, false},
    {"steps_per_mm",      "spmm",     F_FLOAT, &S.steps_per_mm,      0, false},
    {"motor_invert",      "inv",      F_BOOL,  &S.motor_invert,      0, false},
    {"fast_mm_s",         "fast",     F_FLOAT, &S.fast_mm_s,         0, false},
    {"creep_mm_s",        "creep",    F_FLOAT, &S.creep_mm_s,        0, false},
    {"hall_n_per_count",  "npc",      F_FLOAT, &S.hall_n_per_count,  0, false},
    {"cal_zero_counts",   "cal_zero", F_FLOAT, &S.cal_zero_counts,   0, false},
    {"cal_points",        "cal_pts",  F_STR,   S.cal_points,         sizeof S.cal_points,  false},
    {"contact_threshold_n","contact", F_FLOAT, &S.t.contact_threshold_n, 0, false},
    {"preload_force_n",   "preload",  F_FLOAT, &S.t.preload_force_n, 0, false},
    {"force_cap_n",       "cap",      F_FLOAT, &S.t.force_cap_n,     0, false},
    {"blade_k_n_per_mm",  "blade_k",  F_FLOAT, &S.t.blade_k_n_per_mm,0, false},
    {"sample_step_mm",    "sstep",    F_FLOAT, &S.t.sample_step_mm,  0, false},
    {"approach_step_mm",  "astep",    F_FLOAT, &S.t.approach_step_mm,0, false},
    {"safety_margin_mm",  "margin",   F_FLOAT, &S.t.safety_margin_mm,0, false},
    {"max_travel_mm",     "maxtrav",  F_FLOAT, &S.t.max_travel_mm,   0, false},
    {"max_squish_mm",     "maxsq",    F_FLOAT, &S.t.max_squish_mm,   0, false},
    {"ripe_abs_n_per_mm", "ripe_abs", F_FLOAT, &S.t.ripe_abs_n_per_mm,0, false},
    {"ripe_pct_of_first", "ripe_pct", F_FLOAT, &S.t.ripe_pct_of_first,0, false},
    {"swap_contact_mm",   "swap_mm",  F_FLOAT, &S.t.swap_contact_mm, 0, false},
    {"swap_stiffer_pct",  "swap_pct", F_FLOAT, &S.t.swap_stiffer_pct,0, false},
    {"servo_rest_deg",    "srv_rest", F_INT,   &S.servo_rest_deg,    0, false},
    {"servo_tip_deg",     "srv_tip",  F_INT,   &S.servo_tip_deg,     0, false},
    {"servo_hold_ms",     "srv_hold", F_INT,   &S.servo_hold_ms,     0, false},
  };
  count = sizeof f / sizeof f[0];
  return f;
}

inline void settingsLoad() {
  Preferences p;
  p.begin("ripe", false);   // read-write so the namespace is created on first boot (read-only open fails until it exists)
  int n; const FieldDef* f = settingsFields(n);
  for (int i = 0; i < n; i++) {
    if (!p.isKey(f[i].key)) continue;
    switch (f[i].type) {
      case F_FLOAT: *(float*)f[i].ptr = p.getFloat(f[i].key, *(float*)f[i].ptr); break;
      case F_INT:   *(int*)f[i].ptr   = p.getInt(f[i].key, *(int*)f[i].ptr); break;
      case F_BOOL:  *(bool*)f[i].ptr  = p.getBool(f[i].key, *(bool*)f[i].ptr); break;
      case F_STR:   p.getString(f[i].key, (char*)f[i].ptr, f[i].len); break;
    }
  }
  p.end();
  if (S.device_id[0] == 0) {
    uint32_t r = esp_random();
    snprintf(S.device_id, sizeof S.device_id, "%06x", (unsigned)(r & 0xffffff));
    Preferences w; w.begin("ripe", false); w.putString("dev_id", S.device_id); w.end();
  }
}

inline void settingsSave() {
  Preferences p;
  p.begin("ripe", false);
  int n; const FieldDef* f = settingsFields(n);
  for (int i = 0; i < n; i++) {
    switch (f[i].type) {
      case F_FLOAT: p.putFloat(f[i].key, *(float*)f[i].ptr); break;
      case F_INT:   p.putInt(f[i].key, *(int*)f[i].ptr); break;
      case F_BOOL:  p.putBool(f[i].key, *(bool*)f[i].ptr); break;
      case F_STR:   p.putString(f[i].key, (const char*)f[i].ptr); break;
    }
  }
  p.end();
}

// Set one field from text (web form). Returns false for unknown names.
inline bool settingsSet(const char* name, const char* value) {
  int n; const FieldDef* f = settingsFields(n);
  for (int i = 0; i < n; i++) {
    if (strcmp(f[i].name, name) != 0) continue;
    switch (f[i].type) {
      case F_FLOAT: *(float*)f[i].ptr = atof(value); break;
      case F_INT:   *(int*)f[i].ptr = atoi(value); break;
      case F_BOOL:  *(bool*)f[i].ptr = (strcmp(value, "1") == 0 || strcmp(value, "true") == 0 || strcmp(value, "on") == 0); break;
      case F_STR:   strncpy((char*)f[i].ptr, value, f[i].len - 1); ((char*)f[i].ptr)[f[i].len - 1] = 0; break;
    }
    return true;
  }
  return false;
}

inline void jsonEscape(const char* s, String& out) {
  for (; *s; s++) {
    switch (*s) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': break;
      default: out += *s;
    }
  }
}

inline String settingsJson() {
  String o = "{";
  int n; const FieldDef* f = settingsFields(n);
  bool first = true;
  for (int i = 0; i < n; i++) {
    if (f[i].secret) continue;
    if (!first) o += ",";
    first = false;
    o += "\""; o += f[i].name; o += "\":";
    char buf[32];
    switch (f[i].type) {
      case F_FLOAT: snprintf(buf, sizeof buf, "%.5g", (double)*(float*)f[i].ptr); o += buf; break;
      case F_INT:   o += *(int*)f[i].ptr; break;
      case F_BOOL:  o += *(bool*)f[i].ptr ? "true" : "false"; break;
      case F_STR:   o += "\""; jsonEscape((const char*)f[i].ptr, o); o += "\""; break;
    }
  }
  o += ",\"wifi_pass_set\":"; o += S.wifi_pass[0] ? "true" : "false";
  o += "}";
  return o;
}

// ---- Fruit state (what we know about the avocado in the nest) ----------------
struct FruitState {
  uint32_t counter = 0;          // increments for every new fruit
  bool     loaded = false;       // something was in the nest at the last reading
  float    first_contact_mm = 0; // where this fruit was first touched
  float    first_k = 0;          // this fruit's first stiffness
  float    last_k = 0;
  float    last_contact_mm = 0;
  uint32_t start_epoch = 0;      // unix time of the first reading (0 if clock unset)
  uint32_t start_millis = 0;     // fallback for elapsed time
  uint16_t n_readings = 0;
  bool     notified_nearly = false;
  bool     notified_ripe = false;
  char     last_rating[12] = "";
};

extern FruitState FR;

inline void fruitLoad() {
  Preferences p; p.begin("fruit", false);
  FR.counter = p.getUInt("counter", 0);
  FR.loaded = p.getBool("loaded", false);
  FR.first_contact_mm = p.getFloat("fc", 0);
  FR.first_k = p.getFloat("fk", 0);
  FR.last_k = p.getFloat("lk", 0);
  FR.last_contact_mm = p.getFloat("lc", 0);
  FR.start_epoch = p.getUInt("start", 0);
  FR.n_readings = (uint16_t)p.getUShort("n", 0);
  FR.notified_nearly = p.getBool("nn", false);
  FR.notified_ripe = p.getBool("nr", false);
  p.getString("rating", FR.last_rating, sizeof FR.last_rating);
  p.end();
}

inline void fruitSave() {
  Preferences p; p.begin("fruit", false);
  p.putUInt("counter", FR.counter);
  p.putBool("loaded", FR.loaded);
  p.putFloat("fc", FR.first_contact_mm);
  p.putFloat("fk", FR.first_k);
  p.putFloat("lk", FR.last_k);
  p.putFloat("lc", FR.last_contact_mm);
  p.putUInt("start", FR.start_epoch);
  p.putUShort("n", FR.n_readings);
  p.putBool("nn", FR.notified_nearly);
  p.putBool("nr", FR.notified_ripe);
  p.putString("rating", FR.last_rating);
  p.end();
}

// Start tracking a new avocado. Keeps the counter, clears everything else.
inline void fruitNew() {
  uint32_t c = FR.counter + 1;
  FR = FruitState();
  FR.counter = c;
  FR.start_millis = millis();
  fruitSave();
}

inline void fruitId(char* out, int len) {
  snprintf(out, len, "%s-%04u", S.device_id, (unsigned)FR.counter);
}
