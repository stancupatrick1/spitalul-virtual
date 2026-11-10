# Spitalul Virtual Band – history sync protocol

The band saves **one record per minute** (heart rate, SpO2, skin temperature, steps) to its flash
once the phone has set its clock. It keeps the last **40–45 days**. The
[Spitalul Virtual Android app](../../companion/) downloads the records over Bluetooth LE and writes them to
**Health Connect**. From there the Spitalul Virtual
platform imports them through ROOK, like data from any other watch.

```
 band ──BLE──▶ Spitalul Virtual app ──▶ Health Connect ──ROOK──▶ Spitalul Virtual platform
```

## GATT

Service `5b7e0001-5356-4261-6e64-537461636e75`

| Characteristic | UUID | Properties | Content |
|---|---|---|---|
| Live data | `5b7e0002-…` | notify, read | JSON every second: `{"hr","spo2","temp","steps","bat","wrist"}` |
| Command | `5b7e0003-…` | write | UTF-8 text commands (below) |
| History | `5b7e0004-…` | notify | binary packets (below) |

All `5b7e000X` UUIDs end in `-5356-4261-6e64-537461636e75`.
The band asks for an MTU of 247; with it, one packet carries 20 records.

## Commands

| Command | Meaning |
|---|---|
| `time=<seconds>` | set the clock, Unix time **UTC**. Logging starts after this. |
| `tz=<minutes>` | phone's offset from UTC in minutes (Romania: `120` in winter, `180` in summer). Used for the midnight step reset. |
| `sync=<seconds>` | send every record with `t` **greater than** this value, oldest first. `sync=0` sends everything. |
| `info` | send a status packet |
| `reset` | reset today's step counter |
| `buzz` | double vibration (find the band) |
| `clear` | delete all saved history |

## History packets (little-endian)

| First byte | Packet | Layout |
|---|---|---|
| `0x01` | records | `0x01` + N × 12-byte record (N = 1…20, depending on MTU) |
| `0x02` | end of sync | `0x02`, `count` u32, `newest` u32 (time of the last record sent; send it as `sync=` next time) |
| `0x03` | info | `0x03`, `count` u32, `oldest` u32, `newest` u32, `now` u32 (0 = clock not set), `tz` i16, `fw` u8 |
| `0x04` | battery | `0x04`, `battery %` u8 |

### Record (12 bytes)

| Offset | Type | Field |
|---:|---|---|
| 0 | u32 | `t` – start of the minute, Unix time UTC |
| 4 | u8 | average heart rate, bpm (0 = none) |
| 5 | u8 | average SpO2, % (0 = none) |
| 6 | i16 | average skin temperature × 100, °C (−32768 = none) |
| 8 | u16 | steps during this minute |
| 10 | u8 | flags: `0x01` on wrist · `0x02` HR valid · `0x04` SpO2 valid · `0x08` temperature valid |
| 11 | u8 | reserved (0) |

Temperature is only averaged while the band is on the wrist (off the wrist it would be air temperature).

## A typical sync

1. phone connects, subscribes to History
2. `time=1762780000`, `tz=120`
3. `sync=<newest from last time>` (0 the first time)
4. band sends `0x01` packets about every 8 ms, then `0x02`
5. phone writes the records to the health store, then saves `newest` for next time

Records made while a sync is running stay in RAM and arrive with the next sync.

## Storage

The records sit in a ring of 8 files of 96 KB on LittleFS (the `spiffs` data partition). The
band writes the RAM buffer to flash every 10 minutes and before it switches off. When the newest
file is full, the oldest one is emptied and reused.
