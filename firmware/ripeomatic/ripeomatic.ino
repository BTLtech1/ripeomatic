/*
  BTL Ripe-O-Matic — ESP32 firmware
  https://github.com/BTLtech1/ripeomatic

  A horizontal press measures an avocado's stiffness (N/mm) twice a day and
  tells your phone when it's ripe. Everything is served from the device:
  open http://ripeomatic.local on your phone and "Add to Home Screen".

  Board: ESP32 Dev Module (any WROOM DevKit). Arduino-ESP32 core 2.0.x or 3.x.
  Libraries: none beyond the core (WiFi, WebServer, Preferences, LittleFS, HTTPClient, ESPmDNS, DNSServer, ArduinoOTA).
  Partition scheme: Minimal SPIFFS (1.9 MB app with OTA, 190 kB LittleFS). The default 1.25 MB app partition is too small.

  Files:
    config.h    pins and compile-time options (SIMULATE, ENABLE_SERVO)
    measure.h   the measurement state machine, pure C++, unit-tested in ../test
    settings.h  persistent settings + fruit state (NVS)
    stepper.h   28BYJ-48 half-step driver
    hall.h      SS49E on the ADC
    storage.h   CSV log on LittleFS
    net.h       Wi-Fi, setup AP, mDNS, NTP, ntfy push
    machine.h   the job task: home, tare, press, log, notify
    web.h       HTTP API
    improv.h    Improv Wi-Fi over serial, for the web installer
    ui.h        the web page (generated from ../ui/index.html by tools/build_ui.py)

  First boot: no Wi-Fi stored -> it starts an open access point "RipeOMatic-xxxxxx".
  Join it, a setup page opens (or go to http://192.168.4.1), pick your network.
  Or flash from the web installer, which asks for Wi-Fi over USB (Improv) and
  then links straight to the device.
*/
#include "config.h"
#include "settings.h"
#include "machine.h"
#include "web.h"
#include "improv.h"
#if ENABLE_OTA
#include <ArduinoOTA.h>
#endif

Settings S;
FruitState FR;
Machine M;
Web web;
ImprovSerial improvSerial;   // Wi-Fi setup over USB from the web installer

static void ledOn(bool on) {
#if PIN_LED >= 0
  digitalWrite(PIN_LED, on ? HIGH : LOW);
#else
  (void)on;
#endif
}

// ---- BOOT button: short press = measure now, hold 2 s = "it was perfect" ----
static uint32_t btnDown = 0;
static bool btnLongFired = false;
static uint32_t ledFlashUntil = 0;

static void pollButton() {
  bool down = digitalRead(PIN_BUTTON) == LOW;
  uint32_t now = millis();
  if (down && !btnDown) { btnDown = now; btnLongFired = false; }
  if (down && btnDown && !btnLongFired && now - btnDown > 2000) {
    btnLongFired = true;
    M.rate("perfect", "", "button");
    M.queueNotify("Logged: perfect", "Thanks. That's the data point that matters most.");   // sent from the job task, not here
    ledFlashUntil = now + 600;
  }
  if (!down && btnDown) {
    if (!btnLongFired && now - btnDown > 40 && now - btnDown < 1000) M.start(Job::Measure);
    btnDown = 0;
  }
}

// LED: fast blink in setup mode, breathing pulse while measuring, off otherwise.
static void updateLed() {
#if PIN_LED >= 0
  uint32_t t = millis();
  bool on = false;
  if ((int32_t)(ledFlashUntil - t) > 0) on = (t / 80) % 2;   // quick flutter: rating logged
  else if (M.net.apMode) on = (t / 150) % 2;
  else if (M.busy()) on = (t / 500) % 2;
  ledOn(on);
#endif
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.printf("\nBTL Ripe-O-Matic fw %s hw %s%s\n", FW_VERSION, HW_VERSION, SIMULATE ? " (SIMULATE)" : "");

#if PIN_LED >= 0
  pinMode(PIN_LED, OUTPUT);
#endif
  pinMode(PIN_BUTTON, INPUT_PULLUP);

  settingsLoad();
  fruitLoad();
  FR.start_millis = millis();
  Serial.printf("device %s  host %s\n", S.device_id, S.host);

  M.begin();
  M.net.begin();
  web.begin();

#if ENABLE_OTA
  if (!M.net.apMode) {
    ArduinoOTA.setHostname(S.host);
    ArduinoOTA.onStart([] { M.abort(); delay(400); M.stepper.release(); });
    ArduinoOTA.begin();
  }
#endif
  Serial.println("ready");
}

void loop() {
  web.loop();
  improvSerial.loop();
  M.net.loop();
  M.tick();
  pollButton();
  updateLed();
#if ENABLE_OTA
  if (!M.net.apMode) ArduinoOTA.handle();
#endif
  delay(2);   // lets the job task run undisturbed between client requests
}
