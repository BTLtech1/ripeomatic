// BTL Ripe-O-Matic: the readings log on LittleFS (schema v1 CSV).
#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include "config.h"
#include "measure.h"

class Storage {
 public:
  bool begin() {
    ok_ = LittleFS.begin(true);   // format on first use
    if (ok_ && !LittleFS.exists(LOG_PATH)) {
      File f = LittleFS.open(LOG_PATH, "w");
      if (f) { f.println(ripe::csvHeader()); f.close(); }
    }
    return ok_;
  }

  bool ok() const { return ok_; }

  // Append one CSV row (no trailing newline needed). Rotates the log when it gets big.
  bool appendRow(const char* row) {
    if (!ok_) return false;
    File f = LittleFS.open(LOG_PATH, "a");
    if (!f) return false;
    if (f.size() > LOG_MAX_BYTES) {
      f.close();
      LittleFS.remove(LOG_OLD_PATH);
      LittleFS.rename(LOG_PATH, LOG_OLD_PATH);
      f = LittleFS.open(LOG_PATH, "w");
      if (!f) return false;
      f.println(ripe::csvHeader());
    }
    f.println(row);
    f.close();
    return true;
  }

  size_t logSize() {
    if (!ok_) return 0;
    File f = LittleFS.open(LOG_PATH, "r");
    size_t s = f ? f.size() : 0;
    if (f) f.close();
    return s;
  }

  size_t freeBytes() { return ok_ ? LittleFS.totalBytes() - LittleFS.usedBytes() : 0; }

  // Stream the log to a client. If fruit_prefix is set, keep the header and
  // only the rows whose fruit_id (6th column) starts with it.
  template <typename Out>
  void streamLog(Out& out, const char* fruit_prefix, bool include_old) {
    if (!ok_) return;
    bool header_done = false;
    if (include_old) streamFile(out, LOG_OLD_PATH, fruit_prefix, header_done);
    streamFile(out, LOG_PATH, fruit_prefix, header_done);
  }

  // Delete everything (settings page "reset data").
  void wipe() {
    if (!ok_) return;
    LittleFS.remove(LOG_PATH);
    LittleFS.remove(LOG_OLD_PATH);
    File f = LittleFS.open(LOG_PATH, "w");
    if (f) { f.println(ripe::csvHeader()); f.close(); }
  }

 private:
  template <typename Out>
  void streamFile(Out& out, const char* path, const char* fruit_prefix, bool& header_done) {
    File f = LittleFS.open(path, "r");
    if (!f) return;
    String line;
    line.reserve(600);
    bool first = true;
    while (f.available()) {
      line = f.readStringUntil('\n');
      if (line.length() == 0) continue;
      if (first) {
        first = false;
        if (!header_done) { out.print(line); out.print('\n'); header_done = true; }
        continue;
      }
      if (fruit_prefix && fruit_prefix[0]) {
        // column 6 = fruit_id; columns 1-5 never contain commas or quotes
        int c = 0, start = 0;
        for (int i = 0; i < (int)line.length() && c < 5; i++) if (line[i] == ',') { c++; start = i + 1; }
        if (c < 5 || !line.startsWith(fruit_prefix, start)) continue;
      }
      out.print(line);
      out.print('\n');
    }
    f.close();
  }

  bool ok_ = false;
};
