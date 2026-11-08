// =====================================================================
//  SPITALUL VIRTUAL smartwatch firmware          made by Stancu Patrick
//  ESP32-C3 + MAX30102 (heart rate, SpO2) + LIS3DH (steps) + GC9A01 round display
//
//  Side button: short press = next screen, long press = screen off/on
//  Bluetooth LE: standard Heart Rate service, name "Spitalul Virtual"
//
//  Hobby project: the readings are estimates, NOT for medical use.
// =====================================================================
#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <time.h>
#include <Arduino_GFX_Library.h>
#include <Adafruit_LIS3DH.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include "config.h"

// ------------------------------------------------------------------ display
Arduino_DataBus *bus = new Arduino_ESP32SPI(PIN_LCD_DC, PIN_LCD_CS, PIN_LCD_SCK, PIN_LCD_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *panel = new Arduino_GC9A01(bus, GFX_NOT_DEFINED /* RES is tied to EN */, 0, true /* IPS */);
Arduino_Canvas *gfx = new Arduino_Canvas(240, 240, panel);   // draw off-screen, then flush = no flicker
const int CX = 120, CY = 120;
uint16_t C_BG, C_TXT, C_DIM, C_RED, C_CYAN, C_GREEN, C_AMBER;

// ------------------------------------------------------------------ sensors
MAX30105 hr;
Adafruit_LIS3DH acc;
bool hrOk = false, accOk = false;

// heart rate (beat detection) + SpO2 (Maxim algorithm on 100-sample windows)
const int BUF = 100;
uint32_t irBuf[BUF], redBuf[BUF];
int bufFill = 0, newSamples = 0;
int bpm = 0, spo2 = 0;
float bpmAvg = 0;
uint32_t lastBeat = 0;
bool finger = false;
int16_t wave[120]; int waveIdx = 0;

// steps
uint32_t steps = 0, lastStep = 0;
float accLP = 9.81f, accMean = 9.81f;
bool above = false;
const uint32_t STEP_GOAL = 8000;

// ui
int screen = 0;
const int SCREENS = 4;
bool screenOn = true;
uint32_t lastInput = 0, lastDraw = 0, lastHrNotify = 0;
uint32_t btnDown = 0; bool btnLatched = false;

// ble
BLECharacteristic *hrChar = nullptr;
bool bleConnected = false;
class SrvCB : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { bleConnected = true; }
  void onDisconnect(BLEServer *) override { bleConnected = false; BLEDevice::startAdvertising(); }
};

// ------------------------------------------------------------------ helpers
void buzz(int ms) { digitalWrite(PIN_MOTOR, HIGH); delay(ms); digitalWrite(PIN_MOTOR, LOW); }
void backlight(uint8_t v) { ledcWrite(0, v); }

int batteryMv() { return analogReadMilliVolts(PIN_VBAT) * 2; }
int batteryPct() { return constrain(map(batteryMv(), 3350, 4150, 0, 100), 0, 100); }

void centerText(const char *s, int y, uint8_t size, uint16_t col) {
  int16_t x1, y1; uint16_t w, h;
  gfx->setTextSize(size);
  gfx->getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  gfx->setTextColor(col);
  gfx->setCursor(CX - w / 2 - x1, y - h / 2 - y1);
  gfx->print(s);
}

void heart(int x, int y, int r, uint16_t col) {
  gfx->fillCircle(x - r / 2, y - r / 3, r / 2 + 1, col);
  gfx->fillCircle(x + r / 2, y - r / 3, r / 2 + 1, col);
  gfx->fillTriangle(x - r - 1, y - r / 6, x + r + 1, y - r / 6, x, y + r, col);
}

void ring(float frac, uint16_t col, int r1 = 112, int r2 = 119) {
  gfx->fillArc(CX, CY, r2, r1, 0, 360, C_DIM);
  if (frac > 0) gfx->fillArc(CX, CY, r2, r1, 270, 270 + 360.0f * constrain(frac, 0.0f, 1.0f), col);
}

void getNow(struct tm &t) {
  if (!getLocalTime(&t, 0)) {             // no NTP: count from the build time
    static time_t base = 0;
    if (!base) {
      struct tm b = {}; strptime(__DATE__ " " __TIME__, "%b %d %Y %H:%M:%S", &b); base = mktime(&b);
    }
    time_t n = base + millis() / 1000; localtime_r(&n, &t);
  }
}

// ------------------------------------------------------------------ screens
void drawBrand() {
  centerText("SPITALUL VIRTUAL", 34, 1, C_RED);
  centerText("by Stancu Patrick", 210, 1, C_DIM);
}

void drawWatchFace() {
  struct tm t; getNow(t);
  char buf[32];
  ring(batteryPct() / 100.0f, batteryPct() > 20 ? C_GREEN : C_RED);
  drawBrand();
  snprintf(buf, sizeof buf, "%02d:%02d", t.tm_hour, t.tm_min);
  centerText(buf, 92, 6, C_TXT);
  static const char *days[] = {"DUM", "LUN", "MAR", "MIE", "JOI", "VIN", "SAM"};
  snprintf(buf, sizeof buf, "%s %02d.%02d", days[t.tm_wday], t.tm_mday, t.tm_mon + 1);
  centerText(buf, 132, 2, C_DIM);
  // three small stats
  heart(62, 165, 7, C_RED);
  snprintf(buf, sizeof buf, "%d", finger ? bpm : 0);
  gfx->setTextSize(2); gfx->setTextColor(C_TXT); gfx->setCursor(48, 178); gfx->print(finger && bpm ? buf : "--");
  gfx->setTextColor(C_CYAN); gfx->setCursor(103, 160); gfx->setTextSize(1); gfx->print("SpO2");
  snprintf(buf, sizeof buf, "%d%%", spo2);
  gfx->setTextSize(2); gfx->setTextColor(C_TXT); gfx->setCursor(98, 178); gfx->print(finger && spo2 ? buf : "--");
  gfx->setTextColor(C_AMBER); gfx->setTextSize(1); gfx->setCursor(158, 160); gfx->print("PASI");
  snprintf(buf, sizeof buf, "%lu", (unsigned long)steps);
  gfx->setTextSize(2); gfx->setTextColor(C_TXT); gfx->setCursor(150, 178); gfx->print(buf);
  if (bleConnected) gfx->fillCircle(CX, 52, 3, C_CYAN);
}

void drawHeart() {
  char buf[16];
  ring(finger ? bpm / 200.0f : 0, C_RED);
  drawBrand();
  bool beat = millis() - lastBeat < 150;
  heart(CX, 70, beat ? 16 : 13, C_RED);
  snprintf(buf, sizeof buf, "%d", bpm);
  centerText(finger && bpm ? buf : "--", 118, 5, C_TXT);
  centerText("BPM", 150, 2, C_DIM);
  // pulse waveform
  int32_t mn = INT16_MAX, mx = INT16_MIN;
  for (int i = 0; i < 120; i++) { mn = min<int32_t>(mn, wave[i]); mx = max<int32_t>(mx, wave[i]); }
  int span = max<int32_t>(1, mx - mn);
  for (int i = 1; i < 120; i++) {
    int a = wave[(waveIdx + i - 1) % 120], b = wave[(waveIdx + i) % 120];
    gfx->drawLine(60 + i - 1, 190 - (a - mn) * 22 / span, 60 + i, 190 - (b - mn) * 22 / span, C_RED);
  }
  if (!finger) centerText("pune ceasul pe mana", 172, 1, C_AMBER);
}

void drawSpO2() {
  char buf[16];
  ring(finger ? spo2 / 100.0f : 0, C_CYAN);
  drawBrand();
  centerText("SpO2", 70, 3, C_CYAN);
  snprintf(buf, sizeof buf, "%d%%", spo2);
  centerText(finger && spo2 ? buf : "--", 122, 5, C_TXT);
  centerText("oxigen in sange", 160, 1, C_DIM);
  centerText("estimare - nu e aparat medical", 176, 1, C_DIM);
}

void drawSteps() {
  char buf[24];
  ring((float)steps / STEP_GOAL, C_AMBER);
  drawBrand();
  centerText("PASI", 70, 3, C_AMBER);
  snprintf(buf, sizeof buf, "%lu", (unsigned long)steps);
  centerText(buf, 118, 5, C_TXT);
  snprintf(buf, sizeof buf, "obiectiv %lu", (unsigned long)STEP_GOAL);
  centerText(buf, 156, 2, C_DIM);
  snprintf(buf, sizeof buf, "%.2f km", steps * 0.00075f);
  centerText(buf, 180, 1, C_DIM);
}

void draw() {
  gfx->fillScreen(C_BG);
  switch (screen) {
    case 0: drawWatchFace(); break;
    case 1: drawHeart(); break;
    case 2: drawSpO2(); break;
    case 3: drawSteps(); break;
  }
  gfx->flush();
}

// ------------------------------------------------------------------ sensor loops
void pollHeart() {
  if (!hrOk) return;
  hr.check();
  while (hr.available()) {
    uint32_t red = hr.getFIFORed(), ir = hr.getFIFOIR();
    hr.nextSample();
    finger = ir > 50000;
    wave[waveIdx] = (int16_t)((ir >> 4) & 0x7FFF); waveIdx = (waveIdx + 1) % 120;
    if (finger && checkForBeat(ir)) {
      uint32_t now = millis(), dt = now - lastBeat; lastBeat = now;
      float b = 60000.0f / dt;
      if (b > 35 && b < 210) { bpmAvg = bpmAvg ? bpmAvg * 0.75f + b * 0.25f : b; bpm = (int)(bpmAvg + 0.5f); }
    }
    // rolling window for SpO2
    if (bufFill < BUF) { irBuf[bufFill] = ir; redBuf[bufFill] = red; bufFill++; }
    else {
      memmove(irBuf, irBuf + 1, (BUF - 1) * sizeof(uint32_t)); memmove(redBuf, redBuf + 1, (BUF - 1) * sizeof(uint32_t));
      irBuf[BUF - 1] = ir; redBuf[BUF - 1] = red;
    }
    if (++newSamples >= 25 && bufFill == BUF) {
      newSamples = 0;
      int32_t s, h; int8_t sv, hv;
      maxim_heart_rate_and_oxygen_saturation(irBuf, BUF, redBuf, &s, &sv, &h, &hv);
      if (sv && s > 70 && s <= 100 && finger) spo2 = spo2 ? (spo2 * 3 + s) / 4 : s;
    }
  }
  if (!finger) { bpm = 0; bpmAvg = 0; spo2 = 0; }
}

void pollSteps() {
  if (!accOk) return;
  static uint32_t last = 0;
  if (millis() - last < 20) return;      // 50 Hz
  last = millis();
  sensors_event_t e; acc.getEvent(&e);
  float m = sqrtf(e.acceleration.x * e.acceleration.x + e.acceleration.y * e.acceleration.y + e.acceleration.z * e.acceleration.z);
  accLP += (m - accLP) * 0.25f;          // smooth
  accMean += (accLP - accMean) * 0.02f;  // slow baseline
  uint32_t now = millis();
  if (!above && accLP > accMean + 1.3f) {
    above = true;
    if (now - lastStep > 280) { steps++; lastStep = now; }
  } else if (above && accLP < accMean + 0.3f) above = false;
}

void pollButton() {
  bool down = digitalRead(PIN_BUTTON) == LOW;
  uint32_t now = millis();
  if (down && !btnDown) btnDown = now;
  if (down && !btnLatched && now - btnDown > 900) {          // long press
    btnLatched = true; screenOn = !screenOn; backlight(screenOn ? 200 : 0); buzz(60);
    lastInput = now;
  }
  if (!down && btnDown) {
    if (!btnLatched && now - btnDown > 30) {                 // short press
      if (!screenOn) { screenOn = true; backlight(200); }
      else screen = (screen + 1) % SCREENS;
      buzz(20); lastInput = now; draw();
    }
    btnDown = 0; btnLatched = false;
  }
}

// ------------------------------------------------------------------ setup / loop
void setupBle() {
  BLEDevice::init(DEVICE_NAME);
  BLEServer *srv = BLEDevice::createServer();
  srv->setCallbacks(new SrvCB());
  BLEService *svc = srv->createService(BLEUUID((uint16_t)0x180D));          // Heart Rate service
  hrChar = svc->createCharacteristic(BLEUUID((uint16_t)0x2A37), BLECharacteristic::PROPERTY_NOTIFY);
  hrChar->addDescriptor(new BLE2902());
  svc->start();
  BLEDevice::getAdvertising()->addServiceUUID(BLEUUID((uint16_t)0x180D));
  BLEDevice::startAdvertising();
}

void setupClock() {
  if (strlen(WIFI_SSID) == 0) return;
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  if (WiFi.status() == WL_CONNECTED) {
    configTzTime(TZ_INFO, "pool.ntp.org", "time.google.com");
    struct tm t; getLocalTime(&t, 5000);
  }
  WiFi.disconnect(true); WiFi.mode(WIFI_OFF);              // save battery
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MOTOR, OUTPUT); digitalWrite(PIN_MOTOR, LOW);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  ledcSetup(0, 5000, 8); ledcAttachPin(PIN_LCD_BLK, 0); backlight(0);
  analogReadResolution(12);

  gfx->begin();
  C_BG = gfx->color565(0, 0, 0);       C_TXT = gfx->color565(255, 255, 255);
  C_DIM = gfx->color565(70, 70, 80);   C_RED = gfx->color565(235, 40, 60);
  C_CYAN = gfx->color565(40, 200, 255); C_GREEN = gfx->color565(40, 220, 120);
  C_AMBER = gfx->color565(255, 180, 40);
  gfx->fillScreen(C_BG);
  // splash
  heart(CX, 95, 22, C_RED);
  gfx->drawLine(40, 140, 85, 140, C_RED); gfx->drawLine(85, 140, 95, 120, C_RED);
  gfx->drawLine(95, 120, 108, 160, C_RED); gfx->drawLine(108, 160, 118, 140, C_RED);
  gfx->drawLine(118, 140, 200, 140, C_RED);
  centerText("SPITALUL", 172, 2, C_TXT); centerText("VIRTUAL", 192, 2, C_TXT);
  centerText("made by Stancu Patrick", 214, 1, C_DIM);
  gfx->flush();
  for (int b = 0; b <= 200; b += 10) { backlight(b); delay(15); }
  buzz(80);

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  hrOk = hr.begin(Wire, I2C_SPEED_FAST);
  if (hrOk) hr.setup(60 /*LED*/, 4 /*avg*/, 2 /*red+IR*/, 100 /*Hz*/, 411 /*pw*/, 4096 /*range*/);
  accOk = acc.begin(0x19);   // SA0 tied to 3.3 V
  if (accOk) { acc.setRange(LIS3DH_RANGE_4_G); acc.setDataRate(LIS3DH_DATARATE_50_HZ); }
  Serial.printf("Spitalul Virtual: MAX30102 %s, LIS3DH %s, battery %d mV\n",
                hrOk ? "OK" : "missing", accOk ? "OK" : "missing", batteryMv());

  setupClock();
  setupBle();
  delay(600);
  lastInput = millis();
}

void loop() {
  pollHeart();
  pollSteps();
  pollButton();
  uint32_t now = millis();
  if (screenOn && now - lastDraw > 200) { lastDraw = now; draw(); }
  if (screenOn && now - lastInput > 20000) { screenOn = false; backlight(0); }     // auto off
  if (hrChar && bleConnected && finger && bpm && now - lastHrNotify > 1000) {
    lastHrNotify = now;
    uint8_t v[2] = {0x00, (uint8_t)bpm};
    hrChar->setValue(v, 2); hrChar->notify();
  }
  // midnight: reset steps
  static int lastDay = -1; struct tm t; getNow(t);
  if (lastDay != -1 && t.tm_mday != lastDay) steps = 0;
  lastDay = t.tm_mday;
}
