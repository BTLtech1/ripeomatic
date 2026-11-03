// BTL Ripe-O-Matic: the machine. Owns the motor, the sensor, the measurement
// core and the fruit bookkeeping, and runs jobs (measure, jog, home, blade
// calibration, tip) in their own FreeRTOS task so the web server keeps
// answering while the sled creeps for two minutes.
#pragma once
#include <Arduino.h>
#include "config.h"
#include "settings.h"
#include "measure.h"
#include "stepper.h"
#include "hall.h"
#include "storage.h"
#include "net.h"
#include "servo.h"

enum class Job : uint8_t { Idle, Measure, Jog, Home, BladeCal, Tip };

inline const char* jobName(Job j) {
  switch (j) {
    case Job::Idle: return "idle";
    case Job::Measure: return "measure";
    case Job::Jog: return "jog";
    case Job::Home: return "home";
    case Job::BladeCal: return "bladecal";
    case Job::Tip: return "tip";
  }
  return "?";
}

struct LastReading {
  ripe::Outcome outcome = ripe::Outcome::None;
  char time[24] = "";
  float k = 0, r2 = 0, squish = 0, contact = 0, force_max = 0;
  int n_points = 0;
};

class Machine {
 public:
  Stepper28BYJ stepper;
  Hall hall;
  Storage store;
  Net net;
  NestServo servo;
  ripe::MeasureCore core;

  // live state for the UI (written by the job task, read by the web task)
  volatile Job job = Job::Idle;
  volatile ripe::Stage stage = ripe::Stage::Idle;
  volatile float live_force = 0;
  volatile float live_raw = 0;
  LastReading last;
  char error[64] = "";
  uint32_t last_measure_millis = 0;
  uint32_t boot_millis = 0;
  bool measured_since_boot = false;

  void begin() {
    boot_millis = millis();
    stepper.begin();
    applySettings();
    hall.begin(&stepper);
    store.begin();
    servo.begin();
    servo.relax();
  }

  void applySettings() {
    stepper.configure(S.steps_per_mm, S.motor_invert);
    stepper.setSpeedMmS(S.fast_mm_s);
  }

  bool busy() const { return job != Job::Idle; }

  // ---- starting jobs -------------------------------------------------------
  bool start(Job j, float param = 0) {
    if (busy()) return false;
    job = j;
    jobParam_ = param;
    stepper.clearAbort();
    error[0] = 0;
    // 16 kB: the ntfy push at the end runs TLS on this stack.
    BaseType_t ok = xTaskCreatePinnedToCore(taskEntry, "job", 16384, this, 1, &task_, 1);
    if (ok != pdPASS) { job = Job::Idle; strlcpy(error, "could not start task", sizeof error); return false; }
    return true;
  }

  void abort() { if (busy()) stepper.requestAbort(); }

  // Called from loop(): the scheduler.
  void tick() {
    if (busy() || !S.auto_enabled) return;
    uint32_t now = millis();
    // first reading a minute after boot (if the clock/Wi-Fi are up or not), then every interval
    uint32_t due = measured_since_boot ? last_measure_millis + (uint32_t)(intervalHours() * 3600000.0f) : boot_millis + 60000;
    if ((int32_t)(now - due) >= 0) start(Job::Measure);
  }

  // Readings come faster once the fruit is nearly ripe.
  float intervalHours() const {
    float h = S.interval_h;
    if (FR.loaded && FR.last_k > 0) {
      ripe::Verdict v = ripe::judge(FR.last_k, FR.first_k, S.t);
      if (v == ripe::Verdict::Nearly) h = h / 2;
    }
    return h < 0.25f ? 0.25f : h;
  }

  int32_t secondsToNextAuto() const {
    if (!S.auto_enabled) return -1;
    uint32_t due = measured_since_boot ? last_measure_millis + (uint32_t)(intervalHours() * 3600000.0f) : boot_millis + 60000;
    int32_t d = (int32_t)(due - millis()) / 1000;
    return d < 0 ? 0 : d;
  }

  float thresholdNow() const {
    float thr = S.t.ripe_abs_n_per_mm > 0 ? S.t.ripe_abs_n_per_mm : 0;
    if (S.t.ripe_pct_of_first > 0 && FR.first_k > 0) {
      float rel = FR.first_k * S.t.ripe_pct_of_first / 100.0f;
      if (rel > thr) thr = rel;
    }
    return thr;
  }

  float elapsedDays() const {
    if (!FR.loaded) return -1;
    uint32_t now = Net::epoch();
    if (FR.start_epoch && now) return (now - FR.start_epoch) / 86400.0f;
    return (millis() - FR.start_millis) / 86400000.0f;
  }

  // Human rating from the web page or the button. Logged as its own row.
  bool rate(const char* rating, const char* cut, const char* notes) {
    char ts[24], fid[16], row[400];
    Net::isoNow(ts, sizeof ts);
    fruitId(fid, sizeof fid);
    ripe::RowMeta m{S.device_id, ts, fid, S.variety, 0, NAN, "", rating, cut ? cut : "", notes ? notes : ""};
    ripe::formatEventRow(m, row, sizeof row);
    strlcpy(FR.last_rating, rating, sizeof FR.last_rating);
    fruitSave();
    return store.appendRow(row);
  }

  // ---- force calibration ---------------------------------------------------
  float captureZero() {
    float raw = hall.readRaw(HALL_SAMPLES_TARE);
    S.cal_zero_counts = raw;
    S.cal_points[0] = 0;
    settingsSave();
    return raw;
  }

  // Add a (grams, counts) point and refit newtons-per-count through the zero.
  bool captureMass(float grams) {
    if (grams <= 0) return false;
    float raw = hall.readRaw(HALL_SAMPLES_TARE);
    char pt[24];
    snprintf(pt, sizeof pt, "%s%.1f:%.0f", S.cal_points[0] ? ";" : "", grams, raw);
    if (strlen(S.cal_points) + strlen(pt) >= sizeof S.cal_points) return false;
    strcat(S.cal_points, pt);
    refitCalibration();
    settingsSave();
    return true;
  }

  int calPointCount() const {
    if (!S.cal_points[0]) return 0;
    int n = 1;
    for (const char* p = S.cal_points; *p; p++) if (*p == ';') n++;
    return n;
  }

  void clearCalibration() { S.cal_points[0] = 0; settingsSave(); }

  // ---- the jobs (run inside the task) -------------------------------------
 private:
  static void taskEntry(void* arg) {
    Machine* m = (Machine*)arg;
    m->runJob();
    m->job = Job::Idle;
    m->stage = ripe::Stage::Idle;
    m->task_ = nullptr;
    vTaskDelete(nullptr);
  }

  void runJob() {
    switch (job) {
      case Job::Measure:  runMeasurement(false); break;
      case Job::BladeCal: runMeasurement(true); break;
      case Job::Jog:      stepper.setSpeedMmS(S.fast_mm_s); stepper.moveMm(jobParam_); stepper.release(); break;
      case Job::Home:     home(); stepper.release(); break;
      case Job::Tip:      servo.tip(S.servo_rest_deg, S.servo_tip_deg, S.servo_hold_ms); break;
      default: break;
    }
  }

  void home() {
    stage = ripe::Stage::Homing;
    stepper.setSpeedMmS(S.fast_mm_s);
    float back = stepper.posMm() > 0 ? stepper.posMm() + 3.0f : S.t.max_travel_mm + 3.0f;
    stepper.moveMm(-back);          // into the end stop; the 28BYJ-48 slips the last few steps
    stepper.setPosMm(0);
    stepper.moveMm(0.3f);           // come off the stop so it isn't loading the screw
    stepper.setPosMm(0);
  }

  void runMeasurement(bool bladeCal) {
    ripe::Tunables t = S.t;
    if (bladeCal) t.blade_k_n_per_mm = 0;   // we want the raw machine slope

    home();
    if (stepper.aborted()) { finishAborted("stopped"); return; }

    stage = ripe::Stage::Taring;
    delay(300);                     // let the blade stop wobbling
    hall.tare();
    live_raw = hall.tareCounts();
    live_force = 0;

    core.start(t, bladeCal ? 0 : FR.last_contact_mm);
    stage = core.stage();
    float pos = stepper.posMm();
    float force = hall.readForce();
    int negativeRun = 0;
    while (true) {
      ripe::MeasureCore::Cmd c = core.feed(pos, force);
      stage = core.stage();
      if (c.kind == ripe::MeasureCore::Cmd::Stop) break;
      stepper.setSpeedMmS(c.fast ? S.fast_mm_s : S.creep_mm_s);
      stepper.moveMm(c.mm);
      if (stepper.aborted()) { core.abort(); break; }
      pos = stepper.posMm();
      float raw = hall.readRaw(HALL_SAMPLES_LIVE);
      force = hall.countsToForce(raw);
      live_raw = raw;
      live_force = force;
      // Sensor sanity: the force should never go strongly negative while we push.
      // If it does, hall_n_per_count has the wrong sign (or the magnet is flipped).
      if (force < -5 * t.contact_threshold_n) { if (++negativeRun >= 3) { core.abort(); strlcpy(error, "force reads negative: flip the sign of hall_n_per_count (or the magnet)", sizeof error); break; } }
      else negativeRun = 0;
    }

    // Always come back and let go of the fruit, even after an abort.
    stage = ripe::Stage::Retract;
    stepper.clearAbort();
    stepper.setSpeedMmS(S.fast_mm_s);
    stepper.moveMm(-stepper.posMm() - 1.0f);
    stepper.setPosMm(0);
    stepper.release();

    const ripe::Reading& r = core.reading();
    char ts[24];
    Net::isoNow(ts, sizeof ts);
    last.outcome = r.outcome;
    if (ts[0]) strlcpy(last.time, ts, sizeof last.time);
    else snprintf(last.time, sizeof last.time, "up+%lu", (unsigned long)(millis() / 1000));   // clock not set yet
    last.k = r.stiffness_n_per_mm; last.r2 = r.r2; last.squish = r.squish_at_cap_mm;
    last.contact = r.contact_pos_mm; last.force_max = r.force_max_n; last.n_points = r.n_points;
    last_measure_millis = millis();
    measured_since_boot = true;

    if (bladeCal) {
      if (r.outcome == ripe::Outcome::Reading && r.stiffness_n_per_mm > 0.2f) {
        S.t.blade_k_n_per_mm = r.stiffness_n_per_mm;
        settingsSave();
        Serial.printf("blade_k = %.2f N/mm (r2 %.3f)\n", r.stiffness_n_per_mm, r.r2);
      } else {
        strlcpy(error, "blade calibration failed: nothing hard in the nest?", sizeof error);
      }
      return;
    }

    switch (r.outcome) {
      case ripe::Outcome::Reading:
      case ripe::Outcome::Overtravel:
        processReading(r, ts);
        break;
      case ripe::Outcome::Empty:
        if (FR.loaded) {
          FR.loaded = false;
          fruitSave();
          net.ntfy("Nest is empty", "The avocado is gone. Put the next one in.", 2, "avocado");
        }
        break;
      case ripe::Outcome::Aborted:
        if (!error[0]) strlcpy(error, "stopped", sizeof error);
        break;
      default: break;
    }
  }

  void finishAborted(const char* why) {
    strlcpy(error, why, sizeof error);
    last.outcome = ripe::Outcome::Aborted;
    stepper.clearAbort();
    stepper.release();
  }

  void processReading(const ripe::Reading& r, const char* ts) {
    // New avocado?
    bool isNew = !FR.loaded || ripe::looksLikeNewFruit(r.contact_pos_mm, FR.first_contact_mm, r.stiffness_n_per_mm, FR.last_k, S.t);
    if (isNew) {
      fruitNew();
      FR.loaded = true;
      FR.first_contact_mm = r.contact_pos_mm;
      FR.first_k = r.stiffness_n_per_mm;
      FR.start_epoch = Net::epoch();
      FR.start_millis = millis();
    }
    FR.last_k = r.stiffness_n_per_mm;
    FR.last_contact_mm = r.contact_pos_mm;
    FR.n_readings++;
    FR.last_rating[0] = 0;

    // Log it.
    char fid[16], row[700], notes[48] = "";
    fruitId(fid, sizeof fid);
    if (r.outcome == ripe::Outcome::Overtravel) strlcpy(notes, "overtravel: cap not reached", sizeof notes);
    else if (isNew && FR.counter > 1) strlcpy(notes, "new fruit detected", sizeof notes);
    ripe::RowMeta m{S.device_id, ts, fid, S.variety, 0, NAN, S.cal_points, "", "", notes};
    ripe::formatReadingRow(r, m, S.t.force_cap_n, row, sizeof row);
    store.appendRow(row);
    Serial.println(row);

    // Verdict + notifications (once per fruit each).
    ripe::Verdict v = ripe::judge(FR.last_k, FR.first_k, S.t);
    char msg[160];
    if (v == ripe::Verdict::Ripe && !FR.notified_ripe) {
      snprintf(msg, sizeof msg, "Stiffness %.2f N/mm (%.0f%% of day 1). Eat it today or fridge it.", FR.last_k, FR.first_k > 0 ? 100 * FR.last_k / FR.first_k : 0);
      if (net.ntfy("Avocado is ripe", msg, 4, "avocado,tada")) FR.notified_ripe = true;
    } else if (v == ripe::Verdict::Nearly && S.notify_nearly && !FR.notified_nearly) {
      float d = ripe::daysToRipe(FR.first_k, FR.last_k, elapsedDays(), thresholdNow());
      snprintf(msg, sizeof msg, "Stiffness %.2f N/mm. Probably ripe %s.", FR.last_k, d > 0 && d < 1.5f ? "tomorrow" : "in a day or two");
      if (net.ntfy("Avocado almost ripe", msg, 3, "avocado")) FR.notified_nearly = true;
    }
    fruitSave();
  }

  void refitCalibration() {
    // points: grams:counts;...  fit force (N) vs (counts - zero), through the origin-ish via least squares incl. (0,0)
    float x[6], y[6];
    int n = 0;
    x[n] = 0; y[n] = 0; n++;
    const char* p = S.cal_points;
    while (*p && n < 6) {
      float g = atof(p);
      const char* c = strchr(p, ':');
      if (!c) break;
      float counts = atof(c + 1);
      x[n] = counts - S.cal_zero_counts;
      y[n] = g / 1000.0f * 9.80665f;
      n++;
      const char* s = strchr(p, ';');
      if (!s) break;
      p = s + 1;
    }
    if (n >= 2) {
      ripe::LineFit f = ripe::fitLine(x, y, n);
      if (fabsf(f.slope) > 1e-7f) S.hall_n_per_count = f.slope;
    }
  }

  TaskHandle_t task_ = nullptr;
  float jobParam_ = 0;
};

extern Machine M;
