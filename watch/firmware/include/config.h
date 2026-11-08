#pragma once
// ===================== Spitalul Virtual - pin map (matches the KiCad board) =====================
#define PIN_SDA        5   // MAX30102 + LIS3DH
#define PIN_SCL        4
#define PIN_HR_INT    20   // MAX30102 INT (active low)
#define PIN_ACC_INT   21   // LIS3DH INT1
#define PIN_LCD_SCK    6
#define PIN_LCD_MOSI   7
#define PIN_LCD_CS    10
#define PIN_LCD_DC     1
#define PIN_LCD_BLK    2   // backlight (PWM)
#define PIN_BUTTON     9   // side button, active low (also BOOT)
#define PIN_MOTOR      0   // vibration motor MOSFET gate
#define PIN_VBAT       3   // battery / 2 (100k / 100k divider)

// ===================== optional WiFi for the clock (leave empty to skip) =====================
#define WIFI_SSID      ""
#define WIFI_PASSWORD  ""
#define TZ_INFO        "EET-2EEST,M3.5.0/3,M10.5.0/4"   // Romania (Bucharest)

#define DEVICE_NAME    "Spitalul Virtual"
