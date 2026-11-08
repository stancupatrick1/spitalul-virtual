#pragma once
// ===================== Spitalul Virtual BAND - pin map (matches the KiCad board) =====================
#define PIN_SDA         5   // MAX30102 + LIS3DH + TMP117
#define PIN_SCL         4
#define PIN_HR_INT     20   // MAX30102 INT (active low, polled in firmware)
#define PIN_ACC_INT    21   // LIS3DH INT1
#define PIN_TEMP_ALERT  6   // TMP117 ALERT (open drain)
#define PIN_LED         7   // green status LED (active high)
#define PIN_BUTTON      9   // side button, active low (also BOOT)
#define PIN_MOTOR       0   // vibration motor MOSFET gate
#define PIN_VBAT        3   // battery / 2 (100k / 100k divider)

#define ADDR_TMP117   0x48
#define ADDR_LIS3DH   0x19  // SA0 tied to 3.3 V

#define DEVICE_NAME   "Spitalul Virtual Band"
