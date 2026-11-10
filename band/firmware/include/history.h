#pragma once
// =====================================================================
//  Spitalul Virtual Band - all-day history in flash
//  One 12-byte record per minute, kept in a ring of 8 files on LittleFS
//  (96 KB each -> the last 40-45 days). The phone app downloads the records
//  over Bluetooth and writes them to Apple Health / Health Connect.
//  Protocol: see band/docs/SYNC_PROTOCOL.md
// =====================================================================
#include <Arduino.h>

struct __attribute__((packed)) HistRec {
  uint32_t t;       // start of the minute, Unix time UTC (seconds)
  uint8_t  hr;      // average heart rate in bpm, 0 = no reading
  uint8_t  spo2;    // average SpO2 in %, 0 = no reading
  int16_t  temp;    // average skin temperature x100 in deg C, INT16_MIN = no reading
  uint16_t steps;   // steps taken during this minute
  uint8_t  flags;   // HF_* bits
  uint8_t  rsv;     // reserved, 0
};
static_assert(sizeof(HistRec) == 12, "HistRec must be 12 bytes");

enum : uint8_t { HF_WRIST = 0x01, HF_HR = 0x02, HF_SPO2 = 0x04, HF_TEMP = 0x08 };
const int16_t TEMP_NONE = INT16_MIN;

bool     histBegin();                 // mount LittleFS, find the current file
void     histAppend(const HistRec &r);// buffered in RAM, written every few minutes
void     histFlush();                 // write the RAM buffer to flash now
void     histClear();                 // delete all history
uint32_t histCount();                 // records stored (flash + RAM)
uint32_t histOldest();                // timestamp of the oldest record, 0 if empty
uint32_t histNewest();                // timestamp of the newest record, 0 if empty

// Streaming for a sync: start, then call histSyncNext() until it returns 0.
void     histSyncStart(uint32_t since);   // records with t > since, oldest first
int      histSyncNext(HistRec *out, int max);
bool     histSyncing();
void     histSyncStop();
