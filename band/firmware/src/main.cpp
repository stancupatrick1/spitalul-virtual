// =====================================================================
//  SPITALUL VIRTUAL BAND firmware              made by Stancu Patrick
//  ESP32-C3 + MAX30102 (heart rate, SpO2) + LIS3DH (steps) + TMP117 (skin temperature)
//  No screen: everything is sent over Bluetooth LE, the LED and motor give feedback.
//
//  Button:  short press  = LED shows battery (3 blinks >66 %, 2 >33 %, 1 low) + short buzz
//           double press = find-my-phone style "I'm here" buzz pattern, resets nothing
//           hold 3 s     = power off (sleep, history is saved first), press again to wake
//  LED:     slow blink while waiting for a phone, short blink every 5 s when connected
//
//  Bluetooth LE services (work with nRF Connect and most fitness apps):
//    Heart Rate 0x180D, Health Thermometer 0x1809, Pulse Oximeter 0x1822, Battery 0x180F
//    + Spitalul Virtual service (JSON with all values; used by the web app in /app)
//
//  All-day history: once the phone has set the clock, the band saves one record per
//  minute (heart rate, SpO2, skin temperature, steps) to flash, ~46 days. The
//  Spitalul Virtual phone app downloads it ("sync=") and writes it to Apple Health /
//  Google Health Connect. Protocol: band/docs/SYNC_PROTOCOL.md
//
//  Hobby project: readings are estimates, NOT for medical use.
// =====================================================================
#include <Arduino.h>
#include <Wire.h>
#include <time.h>
#include <sys/time.h>
#include <Adafruit_LIS3DH.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <Preferences.h>
#include "config.h"
#include "history.h"

#define SV_SERVICE   "5b7e0001-5356-4261-6e64-537461636e75"   // "SV Band Stancu"
#define SV_DATA      "5b7e0002-5356-4261-6e64-537461636e75"   // notify: JSON
#define SV_COMMAND   "5b7e0003-5356-4261-6e64-537461636e75"   // write: commands, see below
#define SV_HISTORY   "5b7e0004-5356-4261-6e64-537461636e75"   // notify: binary history / info
#define FW_VERSION   2

// Commands (UTF-8 text written to SV_COMMAND):
//   time=<unix UTC seconds>   set the clock (logging starts after this)
//   tz=<minutes east of UTC>  phone's time-zone offset, e.g. tz=120 for Romania in winter
//   sync=<unix UTC seconds>   send every record newer than this on SV_HISTORY
//   info                      send a status packet on SV_HISTORY
//   reset                     reset today's step counter
//   buzz                      short double vibration
//   clear                     delete all saved history

// ------------------------------------------------------------------ sensors
MAX30105 hr;
Adafruit_LIS3DH acc;
bool hrOk = false, accOk = false, tmpOk = false;

const int BUF = 100;
uint32_t irBuf[BUF], redBuf[BUF];
int bufFill = 0, newSamples = 0;
int bpm = 0, spo2 = 0;
float bpmAvg = 0;
uint32_t lastBeat = 0;
bool onWrist = false;
float skinTemp = NAN;

uint32_t steps = 0, lastStep = 0;
uint32_t totalSteps = 0;                  // never reset, used for per-minute steps
float accLP = 9.81f, accMean = 9.81f;
bool above = false;

// ------------------------------------------------------------------ ble
BLECharacteristic *chHr, *chTemp, *chPlx, *chBat, *chData, *chHist;
volatile bool bleConnected = false;
volatile uint16_t peerMtu = 23;
Preferences prefs;
int16_t tzMin = 0;                        // minutes east of UTC, saved in flash

// work requested by the phone, done in loop() (BLE callbacks run in another task)
volatile bool wantSync = false, wantInfo = false, wantClear = false, wantBuzz = false;
volatile uint32_t syncSince = 0;
volatile int16_t newTz = INT16_MIN;

class SrvCB : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { bleConnected = true; peerMtu = 23; }
  void onDisconnect(BLEServer *) override { bleConnected = false; BLEDevice::startAdvertising(); }
  void onMtuChanged(BLEServer *, esp_ble_gatts_cb_param_t *p) override { peerMtu = p->mtu.mtu; }
};
void buzz(int ms);
class CmdCB : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue().c_str();
    v.trim();
    if (v.startsWith("time=")) {
      struct timeval tv = {(time_t)strtoul(v.c_str() + 5, nullptr, 10), 0};
      settimeofday(&tv, nullptr);
    } else if (v.startsWith("tz=")) {
      long m = v.substring(3).toInt();
      if (m >= -720 && m <= 840) newTz = (int16_t)m;
    } else if (v.startsWith("sync=")) {
      syncSince = strtoul(v.c_str() + 5, nullptr, 10); wantSync = true;
    } else if (v == "info") wantInfo = true;
    else if (v == "clear") wantClear = true;
    else if (v == "reset") steps = 0;
    else if (v == "buzz") wantBuzz = true;
  }
};

// ------------------------------------------------------------------ helpers
void led(bool on) { digitalWrite(PIN_LED, on ? HIGH : LOW); }
void buzz(int ms) { digitalWrite(PIN_MOTOR, HIGH); delay(ms); digitalWrite(PIN_MOTOR, LOW); }
void blink(int n, int on = 120, int off = 160) { for (int i = 0; i < n; i++) { led(true); delay(on); led(false); delay(off); } }
int batteryMv() { return analogReadMilliVolts(PIN_VBAT) * 2; }
int batteryPct() { return constrain(map(batteryMv(), 3350, 4150, 0, 100), 0, 100); }

bool timeValid() { return time(nullptr) > 1700000000; }     // set by the phone
// local calendar time using the phone's time-zone offset
void localTm(time_t t, struct tm *tm) { t += (time_t)tzMin * 60; gmtime_r(&t, tm); }

// IEEE-11073 helpers used by the standard health characteristics
uint32_t float32(float v, int exp) { int32_t m = lroundf(v * powf(10, -exp)); return (m & 0xFFFFFF) | ((uint32_t)(exp & 0xFF) << 24); }
uint16_t sfloat(float v) { int16_t m = lroundf(v); return (m & 0x0FFF); }   // exponent 0

// ------------------------------------------------------------------ TMP117 (direct registers)
bool tmpBegin() {
  Wire.beginTransmission(ADDR_TMP117); Wire.write(0x0F);                  // device ID
  if (Wire.endTransmission(false) != 0) return false;
  Wire.requestFrom(ADDR_TMP117, 2);
  uint16_t id = (Wire.read() << 8) | Wire.read();
  if ((id & 0x0FFF) != 0x0117) return false;
  // configuration: continuous conversion, 8 averages, 1 s cycle (CONV=100b)
  Wire.beginTransmission(ADDR_TMP117); Wire.write(0x01); Wire.write(0x02); Wire.write(0x20);
  return Wire.endTransmission() == 0;
}
float tmpRead() {
  Wire.beginTransmission(ADDR_TMP117); Wire.write(0x00);
  if (Wire.endTransmission(false) != 0) return NAN;
  Wire.requestFrom(ADDR_TMP117, 2);
  int16_t raw = (Wire.read() << 8) | Wire.read();
  return raw * 0.0078125f;
}

// ------------------------------------------------------------------ sensor loops
void pollHeart() {
  if (!hrOk) return;
  hr.check();
  while (hr.available()) {
    uint32_t red = hr.getFIFORed(), ir = hr.getFIFOIR();
    hr.nextSample();
    onWrist = ir > 50000;
    if (onWrist && checkForBeat(ir)) {
      uint32_t now = millis(), dt = now - lastBeat; lastBeat = now;
      float b = 60000.0f / dt;
      if (b > 35 && b < 210) { bpmAvg = bpmAvg ? bpmAvg * 0.75f + b * 0.25f : b; bpm = (int)(bpmAvg + 0.5f); }
    }
    if (bufFill < BUF) { irBuf[bufFill] = ir; redBuf[bufFill] = red; bufFill++; }
    else {
      memmove(irBuf, irBuf + 1, (BUF - 1) * sizeof(uint32_t)); memmove(redBuf, redBuf + 1, (BUF - 1) * sizeof(uint32_t));
      irBuf[BUF - 1] = ir; redBuf[BUF - 1] = red;
    }
    if (++newSamples >= 25 && bufFill == BUF) {
      newSamples = 0;
      int32_t s, h; int8_t sv, hv;
      maxim_heart_rate_and_oxygen_saturation(irBuf, BUF, redBuf, &s, &sv, &h, &hv);
      if (sv && s > 70 && s <= 100 && onWrist) spo2 = spo2 ? (spo2 * 3 + s) / 4 : s;
    }
  }
  if (!onWrist) { bpm = 0; bpmAvg = 0; spo2 = 0; }
}

void pollSteps() {
  if (!accOk) return;
  static uint32_t last = 0;
  if (millis() - last < 20) return;        // 50 Hz
  last = millis();
  sensors_event_t e; acc.getEvent(&e);
  float m = sqrtf(e.acceleration.x * e.acceleration.x + e.acceleration.y * e.acceleration.y + e.acceleration.z * e.acceleration.z);
  accLP += (m - accLP) * 0.25f;
  accMean += (accLP - accMean) * 0.02f;
  uint32_t now = millis();
  if (!above && accLP > accMean + 1.3f) {
    above = true;
    if (now - lastStep > 280) { steps++; totalSteps++; lastStep = now; }
  } else if (above && accLP < accMean + 0.3f) above = false;
}

void pollTemp() {
  static uint32_t last = 0;
  if (!tmpOk || millis() - last < 2000) return;
  last = millis();
  float t = tmpRead();
  if (!isnan(t)) skinTemp = isnan(skinTemp) ? t : skinTemp * 0.8f + t * 0.2f;
}

// ------------------------------------------------------------------ button
void powerOff() {
  // GPIO9 cannot wake the ESP32-C3 from deep sleep, so "off" = light sleep with
  // radio and sensors shut down (a few hundred uA), woken by the button.
  buzz(300); blink(2, 300, 200);
  histSyncStop(); histFlush();              // keep the last minutes of history
  if (hrOk) hr.shutDown();
  if (accOk) acc.setDataRate(LIS3DH_DATARATE_POWERDOWN);
  btStop();
  while (digitalRead(PIN_BUTTON) == LOW) delay(10);
  delay(50);
  gpio_wakeup_enable((gpio_num_t)PIN_BUTTON, GPIO_INTR_LOW_LEVEL);
  esp_sleep_enable_gpio_wakeup();
  esp_light_sleep_start();
  ESP.restart();                            // button pressed: start fresh
}

void pollButton() {
  static uint32_t down = 0, lastRelease = 0; static int clicks = 0; static bool latched = false;
  bool pressed = digitalRead(PIN_BUTTON) == LOW;
  uint32_t now = millis();
  if (pressed && !down) down = now;
  if (pressed && !latched && now - down > 3000) { latched = true; powerOff(); }
  if (!pressed && down) {
    if (!latched && now - down > 30) { clicks++; lastRelease = now; }
    down = 0; latched = false;
  }
  if (clicks && !pressed && now - lastRelease > 350) {
    if (clicks == 1) { int p = batteryPct(); buzz(40); blink(p > 66 ? 3 : p > 33 ? 2 : 1); }
    else { for (int i = 0; i < 3; i++) { buzz(150); delay(120); } }
    clicks = 0;
  }
}

// ------------------------------------------------------------------ ble publish
void publish() {
  static uint32_t last = 0;
  if (!bleConnected || histSyncing() || millis() - last < 1000) return;
  last = millis();
  if (onWrist && bpm) { uint8_t v[2] = {0x00, (uint8_t)bpm}; chHr->setValue(v, 2); chHr->notify(); }
  if (!isnan(skinTemp)) {
    uint8_t v[5]; uint32_t f = float32(skinTemp, -2);
    v[0] = 0x00; memcpy(v + 1, &f, 4);                      // Celsius
    chTemp->setValue(v, 5); chTemp->indicate();
  }
  if (onWrist && spo2) {
    uint8_t v[5]; uint16_t s = sfloat(spo2), p = sfloat(bpm);
    v[0] = 0x00; memcpy(v + 1, &s, 2); memcpy(v + 3, &p, 2);
    chPlx->setValue(v, 5); chPlx->notify();
  }
  uint8_t b = batteryPct(); chBat->setValue(&b, 1); chBat->notify();
  char json[160];
  snprintf(json, sizeof json, "{\"hr\":%d,\"spo2\":%d,\"temp\":%.2f,\"steps\":%lu,\"bat\":%d,\"wrist\":%d}",
           onWrist ? bpm : 0, onWrist ? spo2 : 0, isnan(skinTemp) ? 0.0f : skinTemp,
           (unsigned long)steps, (int)b, onWrist ? 1 : 0);
  chData->setValue((uint8_t *)json, strlen(json)); chData->notify();
}

// ------------------------------------------------------------------ all-day history
// Every second the current values are added up; at each full minute (UTC) one
// averaged record is saved. Nothing is saved until the phone has set the clock.
void logMinute() {
  static uint32_t lastSample = 0, minute = 0, stepsAtStart = 0;
  static uint32_t hrSum = 0, hrN = 0, spSum = 0, spN = 0; static float tSum = 0; static uint32_t tN = 0;
  static bool wrist = false;
  if (millis() - lastSample < 1000) return;
  lastSample = millis();
  if (!timeValid()) { minute = 0; return; }
  uint32_t m = (uint32_t)time(nullptr) / 60;
  if (minute && m != minute) {
    if (m < minute || m - minute > 1) {
      // clock was changed by more than a minute: don't save a wrong record
    } else {
      HistRec r = {};
      r.t = minute * 60;
      r.hr = hrN ? (uint8_t)((hrSum + hrN / 2) / hrN) : 0;
      r.spo2 = spN ? (uint8_t)((spSum + spN / 2) / spN) : 0;
      r.temp = tN ? (int16_t)lroundf(tSum / tN * 100) : TEMP_NONE;
      uint32_t ds = totalSteps - stepsAtStart; r.steps = (uint16_t)(ds > 65535 ? 65535 : ds);
      r.flags = (wrist ? HF_WRIST : 0) | (hrN ? HF_HR : 0) | (spN ? HF_SPO2 : 0) | (tN ? HF_TEMP : 0);
      histAppend(r);
    }
  }
  if (m != minute) {                       // start a new minute
    minute = m; stepsAtStart = totalSteps;
    hrSum = hrN = spSum = spN = tN = 0; tSum = 0; wrist = false;
  }
  if (onWrist) wrist = true;
  if (onWrist && bpm) { hrSum += bpm; hrN++; }
  if (onWrist && spo2) { spSum += spo2; spN++; }
  if (onWrist && !isnan(skinTemp)) { tSum += skinTemp; tN++; }   // off the wrist it is air temperature
}

void put32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }   // ESP32 is little-endian

// status packet: 0x03, count u32, oldest u32, newest u32, now u32, tz i16, fw u8, battery u8
void sendInfo() {
  uint8_t p[20];
  p[0] = 0x03;
  put32(p + 1, histCount()); put32(p + 5, histOldest()); put32(p + 9, histNewest());
  put32(p + 13, timeValid() ? (uint32_t)time(nullptr) : 0);
  memcpy(p + 17, &tzMin, 2);
  p[19] = FW_VERSION;
  chHist->setValue(p, 20); chHist->notify();
  delay(10);
  uint8_t b[2] = {0x04, (uint8_t)batteryPct()};             // 0x04: battery, sent separately to fit MTU 23
  chHist->setValue(b, 2); chHist->notify();
}

// sends the history in packets: 0x01 + N records of 12 bytes ... then 0x02 + count u32 + newest u32
void pumpSync() {
  static uint32_t lastPkt = 0, sent = 0, newest = 0;
  static bool active = false;
  if (wantSync) {
    wantSync = false;
    histSyncStart(syncSince);
    active = true; sent = 0; newest = syncSince;
  }
  if (!active) return;
  if (!bleConnected) { histSyncStop(); active = false; return; }
  if (millis() - lastPkt < 8) return;      // give the BLE stack time to send each packet
  lastPkt = millis();
  int per = constrain(((int)peerMtu - 3 - 1) / (int)sizeof(HistRec), 1, 20);
  uint8_t pkt[1 + 20 * sizeof(HistRec)];
  int n = histSyncNext((HistRec *)(pkt + 1), per);
  if (n) {
    pkt[0] = 0x01;
    chHist->setValue(pkt, 1 + n * sizeof(HistRec)); chHist->notify();
    sent += n;
    newest = ((HistRec *)(pkt + 1))[n - 1].t;
    return;
  }
  uint8_t end[9] = {0x02};
  put32(end + 1, sent); put32(end + 5, newest);
  chHist->setValue(end, 9); chHist->notify();
  active = false;
  Serial.printf("sync: sent %lu records\n", (unsigned long)sent);
}

void handleCommands() {
  if (newTz != INT16_MIN) { tzMin = newTz; newTz = INT16_MIN; prefs.putShort("tz", tzMin); }
  if (wantBuzz) { wantBuzz = false; buzz(120); delay(80); buzz(120); }
  if (wantClear) { wantClear = false; histClear(); }
  if (wantInfo && bleConnected) { wantInfo = false; sendInfo(); }
}

void setupBle() {
  BLEDevice::init(DEVICE_NAME);
  BLEDevice::setMTU(247);                   // bigger packets = faster history download
  BLEServer *srv = BLEDevice::createServer();
  srv->setCallbacks(new SrvCB());
  auto mk = [&](BLEService *s, uint16_t uuid, uint32_t props) {
    BLECharacteristic *c = s->createCharacteristic(BLEUUID(uuid), props);
    c->addDescriptor(new BLE2902()); return c;
  };
  BLEService *sHr = srv->createService(BLEUUID((uint16_t)0x180D));
  chHr = mk(sHr, 0x2A37, BLECharacteristic::PROPERTY_NOTIFY); sHr->start();
  BLEService *sT = srv->createService(BLEUUID((uint16_t)0x1809));
  chTemp = mk(sT, 0x2A1C, BLECharacteristic::PROPERTY_INDICATE); sT->start();
  BLEService *sP = srv->createService(BLEUUID((uint16_t)0x1822));
  chPlx = mk(sP, 0x2A5F, BLECharacteristic::PROPERTY_NOTIFY); sP->start();
  BLEService *sB = srv->createService(BLEUUID((uint16_t)0x180F));
  chBat = mk(sB, 0x2A19, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY); sB->start();
  BLEService *sSv = srv->createService(BLEUUID(SV_SERVICE));
  chData = sSv->createCharacteristic(BLEUUID(SV_DATA), BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
  chData->addDescriptor(new BLE2902());
  BLECharacteristic *cmd = sSv->createCharacteristic(BLEUUID(SV_COMMAND), BLECharacteristic::PROPERTY_WRITE);
  cmd->setCallbacks(new CmdCB());
  chHist = sSv->createCharacteristic(BLEUUID(SV_HISTORY), BLECharacteristic::PROPERTY_NOTIFY);
  chHist->addDescriptor(new BLE2902());
  sSv->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(BLEUUID((uint16_t)0x180D));
  adv->addServiceUUID(BLEUUID(SV_SERVICE));
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
}

// ------------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(115200);
  pinMode(PIN_MOTOR, OUTPUT); digitalWrite(PIN_MOTOR, LOW);
  pinMode(PIN_LED, OUTPUT); led(false);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  analogReadResolution(12);
  blink(3, 80, 80); buzz(80);                // hello

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  hrOk = hr.begin(Wire, I2C_SPEED_FAST);
  if (hrOk) hr.setup(60, 4, 2, 100, 411, 4096);
  accOk = acc.begin(ADDR_LIS3DH);
  if (accOk) { acc.setRange(LIS3DH_RANGE_4_G); acc.setDataRate(LIS3DH_DATARATE_50_HZ); }
  tmpOk = tmpBegin();
  prefs.begin("sv", false);
  tzMin = prefs.getShort("tz", 0);
  bool fsOk = histBegin();
  Serial.printf("Spitalul Virtual Band: MAX30102 %s, LIS3DH %s, TMP117 %s, flash log %s (%lu records), battery %d mV\n",
                hrOk ? "OK" : "missing", accOk ? "OK" : "missing", tmpOk ? "OK" : "missing",
                fsOk ? "OK" : "FAILED", (unsigned long)histCount(), batteryMv());
  setupBle();
}

void loop() {
  pollHeart();
  pollSteps();
  pollTemp();
  pollButton();
  publish();
  logMinute();
  handleCommands();
  pumpSync();
  // status LED
  static uint32_t lastBlink = 0;
  uint32_t period = bleConnected ? 5000 : 1500, now = millis();
  if (now - lastBlink > period) { lastBlink = now; led(true); }
  if (now - lastBlink > 30) led(false);
  // midnight: reset steps (once the phone app has sent the time)
  static int lastDay = -1; time_t t = time(nullptr);
  if (timeValid()) { struct tm tm; localTm(t, &tm); if (lastDay != -1 && tm.tm_mday != lastDay) steps = 0; lastDay = tm.tm_mday; }
  // serial log every 5 s
  static uint32_t lastLog = 0;
  if (now - lastLog > 5000) {
    lastLog = now;
    Serial.printf("HR %d bpm  SpO2 %d %%  skin %.2f C  steps %lu  battery %d %%  wrist %d\n",
                  bpm, spo2, skinTemp, (unsigned long)steps, batteryPct(), onWrist);
  }
}
