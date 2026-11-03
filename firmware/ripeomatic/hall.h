// BTL Ripe-O-Matic: SS49E hall sensor on the ESP32 ADC -> force in newtons.
#pragma once
#include <Arduino.h>
#include "config.h"
#include "settings.h"
#include "stepper.h"

class Hall {
 public:
  void begin(const Stepper28BYJ* stepper) {
    stepper_ = stepper;
#if !SIMULATE
    analogReadResolution(12);
    analogSetPinAttenuation(PIN_HALL, ADC_11db);
#endif
  }

  // Averaged raw ADC counts.
  float readRaw(int samples) {
#if SIMULATE
    return simulatedRaw(samples);
#else
    uint32_t acc = 0;
    for (int i = 0; i < samples; i++) acc += analogRead(PIN_HALL);
    return (float)acc / samples;
#endif
  }

  // Zero with the pad in the air. Call before every measurement.
  void tare() { tare_ = readRaw(HALL_SAMPLES_TARE); }
  float tareCounts() const { return tare_; }

  float countsToForce(float raw) const { return (raw - tare_) * S.hall_n_per_count; }
  float readForce(int samples = HALL_SAMPLES_LIVE) { return countsToForce(readRaw(samples)); }

 private:
#if SIMULATE
  // A virtual avocado 24 mm out that softens from 6 to 1 N/mm over ~20 minutes,
  // behind a 3 N/mm blade, read through a slightly noisy sensor.
  float simulatedRaw(int samples) {
    float k_fruit = 1.0f + 5.0f * expf(-(float)millis() / (20.0f * 60.0f * 1000.0f));
    float k_blade = 3.0f;
    float pen = stepper_->posMm() - 24.0f;
    float f = 0;
    if (pen > 0) f = pen * (k_fruit * k_blade) / (k_fruit + k_blade);
    float npc = S.hall_n_per_count != 0 ? S.hall_n_per_count : 0.0035f;
    float noise = ((int)(esp_random() % 1000) - 500) / 500.0f * 1.5f / sqrtf((float)samples);
    delay(samples / 10);   // roughly what the real ADC takes
    return 2000.0f + f / npc + noise;
  }
#endif
  const Stepper28BYJ* stepper_ = nullptr;
  float tare_ = 0;
};
