// BTL Ripe-O-Matic v2: SG90 on the yoke that tips the nest. 50 Hz PWM through LEDC,
// no library. Only compiled in when ENABLE_SERVO is 1 (config.h).
#pragma once
#include <Arduino.h>
#include "config.h"
#include "esp_arduino_version.h"

class NestServo {
 public:
  void begin() {
#if ENABLE_SERVO
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(PIN_SERVO, 50, 16);
#else
    ledcSetup(kChannel, 50, 16);
    ledcAttachPin(PIN_SERVO, kChannel);
#endif
    attached_ = true;
#endif
  }

  // 0..180 degrees. SG90: 0.5 ms = 0 deg, 2.5 ms = 180 deg (clones vary; trim in settings).
  void write(int deg) {
#if ENABLE_SERVO
    if (!attached_) begin();
    if (deg < 0) deg = 0;
    if (deg > 180) deg = 180;
    float ms = 0.5f + 2.0f * deg / 180.0f;
    uint32_t duty = (uint32_t)(ms / 20.0f * 65535.0f);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(PIN_SERVO, duty);
#else
    ledcWrite(kChannel, duty);
#endif
#else
    (void)deg;
#endif
  }

  // Stop sending pulses: the servo relaxes and stops buzzing. The nest's
  // forward bias and the stop tab keep it upright without power.
  void relax() {
#if ENABLE_SERVO
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(PIN_SERVO, 0);
#else
    ledcWrite(kChannel, 0);
#endif
#endif
  }

  // Swing the nest back, hold, return. Blocking (runs inside the job task).
  void tip(int rest_deg, int tip_deg, int hold_ms) {
    write(rest_deg);
    delay(300);
    // ease out so the fruit rolls rather than flies
    int steps = 20;
    for (int i = 1; i <= steps; i++) { write(rest_deg + (tip_deg - rest_deg) * i / steps); delay(40); }
    delay(hold_ms);
    for (int i = steps - 1; i >= 0; i--) { write(rest_deg + (tip_deg - rest_deg) * i / steps); delay(30); }
    delay(300);
    relax();
  }

 private:
  static const int kChannel = 4;
  bool attached_ = false;
};
