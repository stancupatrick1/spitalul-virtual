# Ordering the Spitalul Virtual PCB at JLCPCB

Files you need (all in `hardware/jlcpcb/`):

| File | What it is |
|---|---|
| `spitalul_virtual_gerbers.zip` | the board itself (copper, mask, silkscreen, drills, outline) |
| `spitalul_virtual_BOM.csv` | parts list with LCSC numbers (for assembly) |
| `spitalul_virtual_CPL.csv` | where each part goes, rotation and side (for assembly) |

## 1. Bare PCB

Go to jlcpcb.com → **Order now** → **Add gerber file** → upload `spitalul_virtual_gerbers.zip`. Set:

| Option | Value |
|---|---|
| Base material | FR-4 |
| Layers | 2 |
| Dimensions | detected automatically (≈ 42 × 39 mm) |
| PCB thickness | **1.0 mm** (the case is designed for 1.0 mm) |
| PCB color | **Black** |
| Silkscreen | White |
| Surface finish | **ENIG** (gold pads – looks best on black and is flatter for the tiny sensor packages). LeadFree HASL also works and is cheaper. |
| Mark on PCB | **Order number (Specify position)** – the text `JLCJLCJLCJLC` is already placed on the battery side, so nothing gets printed on the pretty side. |
| Everything else | default |

## 2. Assembly (recommended – the sensor chips are very hard to solder by hand)

This board has parts on **both sides** (the heart-rate sensor must face your skin):

* **Top / battery side:** ESP32-C3 module, USB-C, charger, 3.3 V regulator, button, motor driver, …
* **Bottom / skin side:** MAX30102, LIS3DH, 1.8 V regulator, a few capacitors, charge LED.

JLCPCB's **Economic** assembly only does one side, so pick one of these:

**Option A – everything assembled (easiest)**
1. Turn on **PCB Assembly**, choose **Standard**, **Assemble both sides**.
2. Standard assembly needs a panel of at least 70 × 70 mm with edge rails. In the PCB options choose **Panel by JLCPCB** (e.g. 2 × 2 boards with edge rails). You get 4 boards per panel.
3. Tooling holes / fiducials: *Added by JLCPCB*.

**Option B – cheaper, more soldering**
1. Choose **Economic**, **Top side** only. JLCPCB assembles the battery side.
2. Remove the bottom parts from the BOM (U2, U3, U6, C8–C14, R5, D2) or let the website mark them "not placed".
3. Order those parts separately (same LCSC numbers) plus a **stencil**, and solder the bottom side with solder paste and hot air. The MAX30102 (OLGA-14) and LIS3DH (LGA-16) have hidden pads, so a hotplate or hot-air station is required – not a normal iron.

Then:
1. Upload `spitalul_virtual_BOM.csv` and `spitalul_virtual_CPL.csv`.
2. Check that every line found its part and is **in stock**. If something is out of stock, pick an equivalent with the same package (resistors/capacitors are easy; for the ICs look for the exact part number).
3. On the placement preview check **orientation**: pin-1 dots of U1–U6, the USB-C connector, D1/D2 polarity. If a part is rotated wrong, rotate it in the preview (common for SOT-23 / SOT-23-5 / SOD-323). JLCPCB engineers also review this before production.

## 3. What else to buy

| Item | Notes |
|---|---|
| 1.28" round TFT, GC9A01, 240×240, SPI | bare panel ≤ 36 mm across, ≤ 2.2 mm thick |
| Li-Po 402530 3.7 V (~250 mAh) | **must have a protection circuit** (most small cells do) |
| 8 mm coin vibration motor (0827) | optional |
| Thin wire (30 AWG / 0.25 mm) | display, battery, motor |
| Flexible TPU filament or silicone + mold | for the case |

Parts in the BOM, for reference:

| Ref | Part | LCSC |
|---|---|---|
| U1 | ESP32-C3-WROOM-02-N4 | C2934560 |
| U2 | MAX30102EFD+T | C6454833 |
| U3 | LIS3DHTR | C15134 |
| U4 | MCP73831T-2ACI/OT | C424093 |
| U5 | ME6211C33M5G-N | C82942 |
| U6 | XC6206P182MR | C347373 |
| J1 | USB-C HRO TYPE-C-31-M-12 | C165948 |
| SW1 | EVQ-P7C01P | C388883 |
| Q1 | AO3400A | C20917 |
| D1 | 1N4148WS | C2128 |
| D2 | red LED 0603 | C2286 |
| R/C | 0402 / 0603 basic parts | see BOM |
