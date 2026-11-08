# Ordering the Spitalul Virtual Band PCB at JLCPCB

Files (all in `hardware/jlcpcb/`):

| File | What it is |
|---|---|
| `spitalul_virtual_band_gerbers.zip` | the board (copper, mask, silkscreen, drills, outline) |
| `spitalul_virtual_band_BOM.csv` | parts list with LCSC numbers |
| `spitalul_virtual_band_CPL.csv` | part positions, rotation and side |

## 1. Bare PCB

jlcpcb.com → **Order now** → **Add gerber file** → upload the zip, then set:

| Option | Value |
|---|---|
| Layers | 2 |
| Dimensions | detected (40 × 24 mm) |
| PCB thickness | **1.0 mm** (the band is designed for it) |
| PCB color | **Black** |
| Silkscreen | White |
| Surface finish | **ENIG** (gold pads, flatter for the tiny sensors) – HASL lead-free also works |
| Mark on PCB | **Remove mark** if offered for your order, otherwise "Order number" – there is no free spot reserved for it on this small board |

## 2. Assembly

Parts sit on **both sides**:

* **Top (battery side):** ESP32-C3 module, USB-C, button, charger, 3.3 V regulator, motor driver, green status LED.
* **Bottom (skin side):** MAX30102 (heart rate / SpO2), TMP117 (temperature), LIS3DH (steps), 1.8 V regulator, red charge LED and small passives.

**Option A – fully assembled:** PCB Assembly → **Standard** → **both sides**. Standard assembly needs a ≥ 70 × 70 mm panel with rails, so choose **Panel by JLCPCB** (e.g. 2 × 3 boards with rails).

**Option B – cheaper:** **Economic**, **top side** only, and solder the bottom parts yourself (U2, U3, U6, U7, D2, R1–R3, R5–R12, C1–C3, C8–C16). The MAX30102, TMP117 and LIS3DH have pads underneath – you need solder paste, a stencil and a hotplate or hot air.

Then upload the BOM and CPL, check that every part is found and in stock, and check the orientation preview (pin-1 marks of U1–U7, USB-C, LED / diode polarity). Rotate any part that looks wrong.

## 3. Also buy

| Item | Notes |
|---|---|
| Li-Po **302025** 3.7 V (~110 mAh) | with protection circuit; 202025 makes the band ~1 mm thinner |
| 8 mm coin vibration motor (0827 / 0830) | sticks on top of the USB-C connector |
| 30 AWG wire | battery + motor |
| TPU filament or platinum silicone | band |
| clear PETG / clear resin | top cap |
| 3 mm thermal pad (or 3 mm copper disc) | temperature window |
