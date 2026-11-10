// Spitalul Virtual Band - all-day history in flash (see history.h)
#include "history.h"
#include <FS.h>
#include <LittleFS.h>

// 8 files of 96 KB used in a ring: when the newest is full the oldest is emptied,
// so at least 7 full files (~40 days) are always kept, at most 8 (~45 days).
static const int NFILES = 8;
static const size_t REC = sizeof(HistRec);
static const size_t FILE_MAX = 8192 * REC;                 // 96 KB = 8192 minutes
static const char *name(int i) { static char b[16]; snprintf(b, sizeof b, "/hist%d.bin", i); return b; }
static const int RAM_MAX = 64;     // records kept in RAM before a forced write
static const int RAM_FLUSH = 10;   // normally write to flash every 10 minutes

static bool ok = false;
static int cur = 0;                // file currently being appended to
static HistRec ram[RAM_MAX];
static int ramN = 0;

// sync state
static bool syncing = false;
static uint32_t syncSince = 0;
static int syncFile = 0;           // 0..NFILES-1 = oldest..current file
static File sf;

static size_t recCount(int i) {
  File f = LittleFS.open(name(i), "r");
  if (!f) return 0;
  size_t n = f.size() / REC;       // ignores a half-written record at the end
  f.close();
  return n;
}

static uint32_t recTime(int i, bool last) {
  File f = LittleFS.open(name(i), "r");
  if (!f) return 0;
  size_t n = f.size() / REC;
  uint32_t t = 0;
  if (n) {
    HistRec r;
    f.seek(last ? (n - 1) * REC : 0);
    if (f.read((uint8_t *)&r, REC) == REC) t = r.t;
  }
  f.close();
  return t;
}

bool histBegin() {
  ok = LittleFS.begin(true);       // formats the data partition on first boot
  if (!ok) return false;
  cur = 0;
  uint32_t best = 0;
  for (int i = 0; i < NFILES; i++) { uint32_t t = recTime(i, true); if (t > best) { best = t; cur = i; } }
  return true;
}

static void writeRam() {
  if (!ok || !ramN) return;
  File f = LittleFS.open(name(cur), "a");
  if (f && f.size() >= FILE_MAX) {           // current file full: reuse the oldest one
    f.close();
    cur = (cur + 1) % NFILES;
    f = LittleFS.open(name(cur), "w");       // "w" empties it
  }
  if (!f) return;
  f.write((const uint8_t *)ram, ramN * REC);
  f.close();
  ramN = 0;
}

void histFlush() { if (!syncing) writeRam(); }

void histAppend(const HistRec &r) {
  if (ramN >= RAM_MAX) { histSyncStop(); writeRam(); }   // should never happen
  ram[ramN++] = r;
  if (ramN >= RAM_FLUSH) histFlush();
}

void histClear() {
  histSyncStop();
  ramN = 0;
  if (!ok) return;
  for (int i = 0; i < NFILES; i++) LittleFS.remove(name(i));
  cur = 0;
}

uint32_t histCount() {
  uint32_t n = ramN;
  if (ok) for (int i = 0; i < NFILES; i++) n += recCount(i);
  return n;
}

uint32_t histOldest() {
  for (int k = 1; ok && k <= NFILES; k++) {  // oldest file is the one after the current
    uint32_t t = recTime((cur + k) % NFILES, false);
    if (t) return t;
  }
  return ramN ? ram[0].t : 0;
}

uint32_t histNewest() {
  if (ramN) return ram[ramN - 1].t;
  return ok ? recTime(cur, true) : 0;
}

// first record index with t > since (records are in time order)
static size_t firstAfter(File &f, uint32_t since) {
  size_t lo = 0, hi = f.size() / REC;
  HistRec r;
  while (lo < hi) {
    size_t mid = (lo + hi) / 2;
    f.seek(mid * REC);
    if (f.read((uint8_t *)&r, REC) != REC) break;
    if (r.t <= since) lo = mid + 1; else hi = mid;
  }
  return lo;
}

static bool openSyncFile() {
  while (syncFile < NFILES) {
    int idx = (cur + 1 + syncFile) % NFILES;
    sf = LittleFS.open(name(idx), "r");
    if (sf) {
      size_t start = firstAfter(sf, syncSince);
      if (start < sf.size() / REC) { sf.seek(start * REC); return true; }
      sf.close();
    }
    syncFile++;
  }
  return false;
}

void histSyncStart(uint32_t since) {
  histSyncStop();
  writeRam();                      // everything up to now goes to flash first
  syncSince = since;
  syncFile = 0;
  syncing = ok && openSyncFile();
}

int histSyncNext(HistRec *out, int max) {
  int n = 0;
  while (syncing && n < max) {
    if (sf.read((uint8_t *)&out[n], REC) == REC) {
      if (out[n].t > syncSince) n++;           // skip anything older (clock was moved back)
      continue;
    }
    sf.close();
    syncFile++;
    if (!openSyncFile()) syncing = false;
  }
  return n;
}

bool histSyncing() { return syncing; }

void histSyncStop() {
  if (syncing) sf.close();
  syncing = false;
}
