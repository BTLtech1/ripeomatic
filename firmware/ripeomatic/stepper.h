// BTL Ripe-O-Matic: 28BYJ-48 on a ULN2003, half-stepped, position in mm along the screw.
#pragma once
#include <Arduino.h>
#include "config.h"

class Stepper28BYJ {
 public:
  void begin() {
    const int pins[4] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
    for (int i = 0; i < 4; i++) { pins_[i] = pins[i]; pinMode(pins[i], OUTPUT); digitalWrite(pins[i], LOW); }
  }

  void configure(float steps_per_mm, bool invert) { spmm_ = steps_per_mm; invert_ = invert; }
  void setSpeedMmS(float mm_s) {
    if (mm_s < 0.01f) mm_s = 0.01f;
    step_us_ = (uint32_t)(1e6f / (mm_s * spmm_));
    if (step_us_ < 900) step_us_ = 900;   // ~1100 half-steps/s is already past what a 28BYJ-48 does reliably at 5 V
#if SIMULATE
    step_us_ /= 20;                       // no real motor: a whole reading in ~10 s instead of 3 min
#endif
  }

  float posMm() const { return steps_ / spmm_; }
  void setPosMm(float mm) { steps_ = (long)lroundf(mm * spmm_); }
  long steps() const { return steps_; }
  void setSteps(long s) { steps_ = s; }

  // Blocking relative move. +mm = away from the motor. Checks abort_ every step.
  // Position is tracked even past 0 (a ◀ 1 mm jog may creep past home to find
  // the end stop before "Set home here").
  void moveMm(float mm) {
    long n = (long)lroundf(mm * spmm_);
    int dir = n >= 0 ? 1 : -1;
    n = labs(n);
    uint32_t next = micros();
    for (long i = 0; i < n && !abort_; i++) {
      stepOnce(dir);
      next += step_us_;
      int32_t wait = (int32_t)(next - micros());
      if (wait > 0) {
        if (wait > 2000) { delay(wait / 1000); wait = (int32_t)(next - micros()); }
        if (wait > 0) delayMicroseconds(wait);
      } else {
        next = micros();   // we fell behind (Wi-Fi hiccup); don't try to catch up
      }
    }
  }

  // Cut coil current. The screw holds position on its own.
  void release() { for (int i = 0; i < 4; i++) digitalWrite(pins_[i], LOW); }

  void requestAbort() { abort_ = true; }
  void clearAbort() { abort_ = false; }
  bool aborted() const { return abort_; }

 private:
  void stepOnce(int dir) {
    // 8-step half-step sequence
    static const uint8_t seq[8] = {0b0001, 0b0011, 0b0010, 0b0110, 0b0100, 0b1100, 0b1000, 0b1001};
    int d = invert_ ? -dir : dir;
    phase_ = (phase_ + d) & 7;
    uint8_t m = seq[phase_];
    for (int i = 0; i < 4; i++) digitalWrite(pins_[i], (m >> i) & 1);
    steps_ += dir;
  }

  int pins_[4] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
  float spmm_ = DEFAULT_STEPS_PER_MM;
  bool invert_ = false;
  uint32_t step_us_ = 1100;
  int phase_ = 0;
  long steps_ = 0;
  volatile bool abort_ = false;
};
