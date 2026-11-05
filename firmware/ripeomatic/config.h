// BTL Ripe-O-Matic firmware: compile-time configuration.
// Everything that depends on how YOU wired or printed the machine lives here
// or in the web settings page. Pins match hardware/README.md.
#pragma once

#define FW_VERSION "0.1.0"
#define HW_VERSION "v1"
#define SCHEMA_VERSION 1

// ---- Pins -----------------------------------------------------------------
// 28BYJ-48 through the ULN2003. IN1..IN4 in order.
// (16/17 are free on WROOM boards; on a WROVER they are the PSRAM pins: use 25/26/27/14 there.)
#define PIN_IN1 16
#define PIN_IN2 17
#define PIN_IN3 18
#define PIN_IN4 19

// SS49E hall sensor output. Must be an ADC1 pin (32-39); ADC2 dies when Wi-Fi is on.
#define PIN_HALL 34

// BOOT button on the dev board. Short press = measure now, hold 2 s = "it was perfect".
#define PIN_BUTTON 0

// On-board LED (blue on most ESP32 DevKits). Set to -1 if yours has none.
#define PIN_LED 2

// v2: SG90 servo that tips the nest. Set ENABLE_SERVO 1 once it is fitted.
#ifndef ENABLE_SERVO
#define ENABLE_SERVO 0
#endif
#define PIN_SERVO 25

// Optional DS18B20 for room_temp_c. Not implemented yet; reserved pin.
#define PIN_TEMP 27

// ---- Behaviour -------------------------------------------------------------
// Run without any hardware: a virtual avocado that softens over time.
// Lets you try the web UI on a bare ESP32 before the printer finishes.
// (CI builds both variants with -DSIMULATE=1 / 0, hence the #ifndef.)
#ifndef SIMULATE
#define SIMULATE 0
#endif

// Arduino OTA updates (upload from the IDE over Wi-Fi). Hostname = mDNS name.
#define ENABLE_OTA 1

// Motor: the 28BYJ-48 is driven in half steps (8-step sequence).
// 64:1 gearbox -> 4096 half steps per turn (nominally; the true ratio is 63.68:1,
// 4076 half steps, which the force-vs-squish slope does not care about).
// TR10x2 screw: 2 mm per turn -> 2048 half steps per mm.
#define DEFAULT_STEPS_PER_MM 2048.0f

// Maximum sled travel from the end stop before giving up (empty nest).
#define DEFAULT_MAX_TRAVEL_MM 42.0f

// Speeds in mm/s. The 28BYJ-48 runs out of torque at about 15 rpm (~0.5 mm/s here).
#define DEFAULT_FAST_MM_S  0.45f
#define DEFAULT_CREEP_MM_S 0.25f

// Measurement step size while creeping and measuring (mm per force sample).
#define DEFAULT_SAMPLE_STEP_MM 0.05f

// Hall sensor averaging. The ESP32 ADC is noisy; average lots of samples.
#define HALL_SAMPLES_TARE 256
#define HALL_SAMPLES_LIVE 48

// Log file on LittleFS. When it passes LOG_MAX_BYTES it is rotated once
// to readings.old.csv (so you never lose the current fruit). The "Minimal
// SPIFFS" partition scheme leaves ~190 kB for the filesystem: 80 kB per file
// is ~200 readings each, about 100 days at two a day, plus the old file.
#define LOG_PATH "/readings.csv"
#define LOG_OLD_PATH "/readings.old.csv"
#define LOG_MAX_BYTES 80000

// Wi-Fi setup access point when no network is stored or it can't be joined.
#define AP_SSID_PREFIX "RipeOMatic-"
#define WIFI_CONNECT_TIMEOUT_MS 20000

#define NTP_SERVER "pool.ntp.org"
