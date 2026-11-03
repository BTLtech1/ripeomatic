// BTL Ripe-O-Matic: measurement logic.
//
// No Arduino in here on purpose. This file is the state machine that turns
// (sled position, force) samples into a reading, plus the line fit, the
// ripeness verdict and the CSV row. It compiles on a PC, and
// firmware/test/test_measure.cpp runs it against a simulated avocado.
//
// Units: mm, newtons, seconds. See docs/measurement.md for the routine.
#pragma once
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "config.h"   // FW_VERSION, HW_VERSION, SCHEMA_VERSION; no Arduino in there

namespace ripe {

// ---- Tunables (a copy of the user settings the routine needs) --------------
struct Tunables {
  float contact_threshold_n = 0.10f;  // force that counts as touching
  float preload_force_n     = 0.20f;  // seats the fruit; travel zero
  float force_cap_n         = 2.50f;  // never push harder than this
  float blade_k_n_per_mm    = 0.0f;   // 0 = not calibrated, no correction
  float sample_step_mm      = 0.05f;  // creep/measure increment
  float approach_step_mm    = 0.50f;  // fast approach increment (force is checked between)
  float safety_margin_mm    = 2.0f;   // switch to creep this far before last contact
  float max_travel_mm       = 42.0f;  // give up (empty nest) past this
  float max_squish_mm       = 12.0f;  // give up (mush / sensor fault) past this
  float ripe_abs_n_per_mm   = 1.5f;   // ripe below this stiffness (0 = off). PLACEHOLDER until data
  float ripe_pct_of_first   = 45.0f;  // ...or below this % of the fruit's first reading (0 = off)
  float swap_contact_mm     = 6.0f;   // contact position jump that means a new avocado
  float swap_stiffer_pct    = 60.0f;  // stiffness jump up by this % means a new avocado
};

enum class Stage : uint8_t { Idle, Homing, Taring, Approach, Creep, Preload, Measure, Retract, Done, Error };

inline const char* stageName(Stage s) {
  switch (s) {
    case Stage::Idle: return "idle";
    case Stage::Homing: return "homing";
    case Stage::Taring: return "taring";
    case Stage::Approach: return "approach";
    case Stage::Creep: return "creep";
    case Stage::Preload: return "preload";
    case Stage::Measure: return "measure";
    case Stage::Retract: return "retract";
    case Stage::Done: return "done";
    case Stage::Error: return "error";
  }
  return "?";
}

enum class Outcome : uint8_t { None, Reading, Empty, Aborted, Overtravel };

inline const char* outcomeName(Outcome o) {
  switch (o) {
    case Outcome::None: return "none";
    case Outcome::Reading: return "reading";
    case Outcome::Empty: return "empty";
    case Outcome::Aborted: return "aborted";
    case Outcome::Overtravel: return "overtravel";
  }
  return "?";
}

// ---- Least squares -----------------------------------------------------------
struct LineFit {
  float slope = 0, intercept = 0, r2 = 0;
  int n = 0;
};

inline LineFit fitLine(const float* x, const float* y, int n) {
  LineFit f;
  f.n = n;
  if (n < 2) return f;
  double sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
  for (int i = 0; i < n; i++) {
    sx += x[i]; sy += y[i]; sxx += (double)x[i] * x[i]; sxy += (double)x[i] * y[i]; syy += (double)y[i] * y[i];
  }
  double den = n * sxx - sx * sx;
  if (fabs(den) < 1e-12) return f;
  f.slope = (float)((n * sxy - sx * sy) / den);
  f.intercept = (float)((sy - f.slope * sx) / n);
  double ssTot = syy - sy * sy / n;
  double ssRes = 0;
  for (int i = 0; i < n; i++) {
    double e = y[i] - (f.slope * x[i] + f.intercept);
    ssRes += e * e;
  }
  f.r2 = ssTot > 1e-12 ? (float)(1.0 - ssRes / ssTot) : 1.0f;
  return f;
}

// ---- Result ------------------------------------------------------------------
static const int MAX_POINTS = 400;   // 12 mm / 0.05 mm = 240; headroom
static const int CURVE_POINTS = 24;  // points kept in the CSV "curve" field

struct Reading {
  Outcome outcome = Outcome::None;
  float contact_pos_mm = 0;      // absolute, from the end stop
  float preload_pos_mm = 0;      // where travel zero was set
  float stiffness_n_per_mm = 0;  // slope of force vs squish
  float r2 = 0;
  float squish_at_cap_mm = 0;
  float force_max_n = 0;         // force actually reached (= cap on a normal reading)
  float blade_k_n_per_mm = 0;    // the correction that was applied (0 = none)
  int n_points = 0;
  float squish[MAX_POINTS];
  float force[MAX_POINTS];
};

// ---- The state machine -------------------------------------------------------
// Drive it like this (the runner in ripeomatic.ino does):
//   core.start(tunables, last_contact_mm);
//   while (true) { auto c = core.feed(pos_mm, force_n); if (c.kind == Cmd::Stop) break; move(c.mm, c.fast); }
// The runner owns homing, taring and retracting; the core owns the part
// between "pad in the air at position 0" and "force cap reached".
class MeasureCore {
 public:
  struct Cmd {
    enum Kind : uint8_t { Move, Stop } kind;
    float mm;      // relative move to make before the next sample (>0 toward the fruit)
    bool fast;     // true = approach speed, false = creep speed
  };

  void start(const Tunables& t, float last_contact_mm) {
    t_ = t;
    r_ = Reading();
    consecutive_ = 0;
    // Approach fast to a few mm short of where the fruit was last time, then
    // creep. On the first run (last_contact <= 0) approach fast nearly to the
    // end: the force is checked every approach step, and a touch backs off
    // and drops to creep, so the worst case is one approach step of overshoot
    // (~0.5 mm, well under 1 N on even a rock-hard fruit).
    approach_to_ = last_contact_mm > 0 ? last_contact_mm - t.safety_margin_mm : t.max_travel_mm - 2.0f;
    if (approach_to_ < 0) approach_to_ = 0;
    stage_ = Stage::Approach;
  }

  Stage stage() const { return stage_; }
  const Reading& reading() const { return r_; }
  float travelZero() const { return r_.preload_pos_mm; }

  // pos_mm: absolute sled position (0 = end stop). force_n: tared, calibrated force (push positive).
  Cmd feed(float pos_mm, float force_n) {
    switch (stage_) {
      case Stage::Approach: {
        if (force_n >= t_.contact_threshold_n) {
          // Touched the fruit during the fast approach (up to one approach
          // step of overshoot). Back off past where we first touched and let
          // the creep find contact at sample-step resolution.
          stage_ = Stage::Creep;
          consecutive_ = 0;
          float back = t_.approach_step_mm + 2 * t_.sample_step_mm;
          if (pos_mm - back < 0) back = pos_mm;
          return Cmd{Cmd::Move, -back, true};
        }
        if (pos_mm >= t_.max_travel_mm) return finish(Outcome::Empty, pos_mm);
        if (pos_mm + 1e-4f >= approach_to_) {
          stage_ = Stage::Creep;
          return creepStep(pos_mm, force_n);
        }
        float step = t_.approach_step_mm;
        if (pos_mm + step > approach_to_) step = approach_to_ - pos_mm;
        return Cmd{Cmd::Move, step, true};
      }
      case Stage::Creep:
        return creepStep(pos_mm, force_n);
      case Stage::Preload: {
        if (force_n >= t_.preload_force_n) {
          r_.preload_pos_mm = pos_mm;
          preload_force_ = force_n;
          stage_ = Stage::Measure;
          addPoint(pos_mm, force_n);
          return Cmd{Cmd::Move, t_.sample_step_mm, false};
        }
        if (pos_mm >= t_.max_travel_mm) return finish(Outcome::Empty, pos_mm);
        // Lost contact (fruit settled or it was a wrinkle in the liner): back to creep.
        if (force_n < t_.contact_threshold_n * 0.5f) { stage_ = Stage::Creep; consecutive_ = 0; }
        return Cmd{Cmd::Move, t_.sample_step_mm, false};
      }
      case Stage::Measure: {
        addPoint(pos_mm, force_n);
        if (force_n >= t_.force_cap_n) return finish(Outcome::Reading, pos_mm);
        if (pos_mm - r_.preload_pos_mm >= t_.max_squish_mm) return finish(Outcome::Overtravel, pos_mm);
        if (pos_mm >= t_.max_travel_mm) return finish(Outcome::Overtravel, pos_mm);
        return Cmd{Cmd::Move, t_.sample_step_mm, false};
      }
      default:
        return Cmd{Cmd::Stop, 0, false};
    }
  }

  void abort() {
    r_.outcome = Outcome::Aborted;
    stage_ = Stage::Error;
  }

 private:
  Cmd creepStep(float pos_mm, float force_n) {
    if (force_n >= t_.contact_threshold_n) {
      if (consecutive_ == 0) first_touch_ = pos_mm;
      if (++consecutive_ >= 3) {              // three samples in a row: real contact, not a noise spike
        r_.contact_pos_mm = first_touch_;
        stage_ = Stage::Preload;
        return feed(pos_mm, force_n);   // may already be past preload
      }
    } else {
      consecutive_ = 0;
    }
    if (pos_mm >= t_.max_travel_mm) return finish(Outcome::Empty, pos_mm);
    return Cmd{Cmd::Move, t_.sample_step_mm, false};
  }

  void addPoint(float pos_mm, float force_n) {
    if (r_.n_points >= MAX_POINTS) return;
    float travel = pos_mm - r_.preload_pos_mm;
    float bend = 0;
    if (t_.blade_k_n_per_mm > 0.01f) bend = (force_n - preload_force_) / t_.blade_k_n_per_mm;
    float squish = travel - bend;
    if (squish < 0) squish = 0;
    r_.squish[r_.n_points] = squish;
    r_.force[r_.n_points] = force_n;
    r_.n_points++;
    if (force_n > r_.force_max_n) r_.force_max_n = force_n;
  }

  Cmd finish(Outcome o, float pos_mm) {
    (void)pos_mm;
    r_.outcome = o;
    r_.blade_k_n_per_mm = t_.blade_k_n_per_mm;
    if ((o == Outcome::Reading || o == Outcome::Overtravel) && r_.n_points >= 3) {
      LineFit f = fitLine(r_.squish, r_.force, r_.n_points);
      r_.stiffness_n_per_mm = f.slope;
      r_.r2 = f.r2;
      r_.squish_at_cap_mm = r_.squish[r_.n_points - 1];
    } else if (o == Outcome::Reading) {
      // Reached the cap in under 3 samples: very hard fruit, or the cap is too low.
      // Report what we have: treat as very stiff.
      r_.stiffness_n_per_mm = r_.n_points >= 2 ? fitLine(r_.squish, r_.force, r_.n_points).slope : 99.0f;
      r_.squish_at_cap_mm = r_.n_points ? r_.squish[r_.n_points - 1] : 0;
    }
    stage_ = Stage::Done;
    return Cmd{Cmd::Stop, 0, false};
  }

  Tunables t_;
  Reading r_;
  Stage stage_ = Stage::Idle;
  float approach_to_ = 0;
  float preload_force_ = 0;
  float first_touch_ = 0;
  int consecutive_ = 0;
};

// ---- Interpretation ----------------------------------------------------------
enum class Verdict : uint8_t { Unknown, Hard, Firming, Nearly, Ripe };

inline const char* verdictName(Verdict v) {
  switch (v) {
    case Verdict::Unknown: return "unknown";
    case Verdict::Hard: return "hard";
    case Verdict::Firming: return "firming";
    case Verdict::Nearly: return "nearly";
    case Verdict::Ripe: return "ripe";
  }
  return "?";
}

// first_stiffness: the fruit's first reading (0 if unknown).
inline Verdict judge(float stiffness, float first_stiffness, const Tunables& t) {
  if (stiffness <= 0) return Verdict::Unknown;
  float thr = 0;
  if (t.ripe_abs_n_per_mm > 0) thr = t.ripe_abs_n_per_mm;
  if (t.ripe_pct_of_first > 0 && first_stiffness > 0) {
    float rel = first_stiffness * t.ripe_pct_of_first / 100.0f;
    if (rel > thr) thr = rel;   // whichever comes first = the higher threshold
  }
  if (thr <= 0) return Verdict::Unknown;
  if (stiffness <= thr) return Verdict::Ripe;
  if (stiffness <= thr * 1.3f) return Verdict::Nearly;
  if (first_stiffness > 0 && stiffness < first_stiffness * 0.8f) return Verdict::Firming;
  return Verdict::Hard;
}

// Has the avocado been swapped since the last reading of the current fruit?
inline bool looksLikeNewFruit(float contact_pos, float first_contact_pos, float stiffness, float last_stiffness, const Tunables& t) {
  if (first_contact_pos > 0 && fabsf(contact_pos - first_contact_pos) > t.swap_contact_mm) return true;
  if (last_stiffness > 0 && stiffness > last_stiffness * (1.0f + t.swap_stiffer_pct / 100.0f)) return true;
  return false;
}

// Rough days-to-ripe from the fruit's own decay so far. Stiffness decays about
// exponentially; with two points (first, now) and the time between them we get
// the rate. Returns -1 if it can't say. Pooled data will replace this.
inline float daysToRipe(float first_stiffness, float now_stiffness, float days_elapsed, float threshold) {
  if (first_stiffness <= 0 || now_stiffness <= 0 || threshold <= 0 || days_elapsed < 0.5f) return -1;
  if (now_stiffness <= threshold) return 0;
  if (now_stiffness >= first_stiffness * 0.98f) return -1;   // hasn't started softening
  float rate = logf(first_stiffness / now_stiffness) / days_elapsed;   // per day
  if (rate <= 1e-4f) return -1;
  float d = logf(now_stiffness / threshold) / rate;
  return d > 30 ? 30 : d;
}

// ---- CSV -----------------------------------------------------------------------
// Schema v1 (docs/data-sharing.md). Human ratings are their own rows with the
// measurement columns blank.
inline const char* csvHeader() {
  return "schema,device_id,fw_version,hw_version,timestamp,fruit_id,variety,fruit_mass_g,room_temp_c,"
         "contact_pos_mm,stiffness_n_per_mm,squish_at_cap_mm,force_cap_n,blade_k_n_per_mm,cal_points,curve,"
         "human_rating,cut_open,notes";
}

// Quote a field if it needs it. Writes into out (len bytes). Returns chars written.
inline int csvField(const char* s, char* out, int len) {
  bool needs = false;
  for (const char* p = s; *p; p++) if (*p == ',' || *p == '"' || *p == '\n' || *p == '\r') { needs = true; break; }
  int n = 0;
  if (!needs) {
    for (const char* p = s; *p && n < len - 1; p++) out[n++] = *p;
  } else {
    if (n < len - 1) out[n++] = '"';
    for (const char* p = s; *p && n < len - 3; p++) {
      if (*p == '"') out[n++] = '"';
      out[n++] = *p;
    }
    if (n < len - 1) out[n++] = '"';
  }
  out[n] = 0;
  return n;
}

// Downsample the curve to <= CURVE_POINTS "squish:force" pairs separated by ';'.
inline void formatCurve(const Reading& r, char* out, int len) {
  int n = 0;
  out[0] = 0;
  if (r.n_points == 0) return;
  int stride = (r.n_points + CURVE_POINTS - 1) / CURVE_POINTS;
  if (stride < 1) stride = 1;
  for (int i = 0; i < r.n_points; i += stride) {
    int w = snprintf(out + n, len - n, "%s%.2f:%.2f", n ? ";" : "", r.squish[i], r.force[i]);
    if (w < 0 || w >= len - n) { out[n] = 0; return; }
    n += w;
  }
  // always include the last point
  int last = r.n_points - 1;
  if (last % stride != 0) {
    int w = snprintf(out + n, len - n, ";%.2f:%.2f", r.squish[last], r.force[last]);
    if (w > 0 && w < len - n) n += w;
  }
  out[n] = 0;
}

struct RowMeta {
  const char* device_id;
  const char* timestamp;   // ISO 8601 UTC, or "" if the clock is not set
  const char* fruit_id;
  const char* variety;
  float fruit_mass_g;      // <= 0 = blank
  float room_temp_c;       // NAN = blank
  const char* cal_points;  // "0:0,100:0.98" or ""
  const char* human_rating;
  const char* cut_open;
  const char* notes;
};

inline int formatReadingRow(const Reading& r, const RowMeta& m, float force_cap_n, char* out, int len) {
  char var[64], notes[160], curve[CURVE_POINTS * 12 + 16], cal[96], mass[16], temp[16];
  csvField(m.variety ? m.variety : "", var, sizeof var);
  csvField(m.notes ? m.notes : "", notes, sizeof notes);
  csvField(m.cal_points ? m.cal_points : "", cal, sizeof cal);
  formatCurve(r, curve, sizeof curve);
  if (m.fruit_mass_g > 0) snprintf(mass, sizeof mass, "%.0f", m.fruit_mass_g); else mass[0] = 0;
  if (!isnan(m.room_temp_c)) snprintf(temp, sizeof temp, "%.1f", m.room_temp_c); else temp[0] = 0;
  char bk[16];
  if (r.blade_k_n_per_mm > 0) snprintf(bk, sizeof bk, "%.2f", r.blade_k_n_per_mm); else bk[0] = 0;
  return snprintf(out, len, "%d,%s,%s,%s,%s,%s,%s,%s,%s,%.2f,%.3f,%.2f,%.2f,%s,%s,%s,%s,%s,%s",
                  SCHEMA_VERSION, m.device_id, FW_VERSION, HW_VERSION, m.timestamp, m.fruit_id, var, mass, temp,
                  r.contact_pos_mm, r.stiffness_n_per_mm, r.squish_at_cap_mm, force_cap_n, bk, cal, curve,
                  m.human_rating ? m.human_rating : "", m.cut_open ? m.cut_open : "", notes);
}

// A rating or note without a measurement: measurement columns blank.
inline int formatEventRow(const RowMeta& m, char* out, int len) {
  char var[64], notes[160];
  csvField(m.variety ? m.variety : "", var, sizeof var);
  csvField(m.notes ? m.notes : "", notes, sizeof notes);
  return snprintf(out, len, "%d,%s,%s,%s,%s,%s,%s,,,,,,,,,,%s,%s,%s",
                  SCHEMA_VERSION, m.device_id, FW_VERSION, HW_VERSION, m.timestamp, m.fruit_id, var,
                  m.human_rating ? m.human_rating : "", m.cut_open ? m.cut_open : "", notes);
}

}  // namespace ripe
