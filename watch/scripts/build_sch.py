"""Generate the KiCad 7 schematic + symbol library from design.py (net labels on every pin)."""
import os, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
from design import *

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KDIR = os.path.join(ROOT, "hardware", "kicad")
G = 2.54

def U(): return str(uuid.uuid4())
def q(s): return '"' + str(s).replace('"', '\\"') + '"'
def snap(v): return round(round(v / 1.27) * 1.27, 4)

# ------------------------------------------------------------ pin names for the drawing
NAMES = {
 "U1": {"1": "3V3", "2": "EN", "3": "IO4", "4": "IO5", "5": "IO6", "6": "IO7", "7": "IO8", "8": "IO9/BOOT",
        "9": "GND", "10": "IO10", "11": "IO20/RX", "12": "IO21/TX", "13": "IO18/D-", "14": "IO19/D+",
        "15": "IO3/ADC", "16": "IO2", "17": "IO1", "18": "IO0", "19": "EPAD"},
 "U2": {"1": "NC", "2": "SCL", "3": "SDA", "4": "PGND", "5": "R_DRV", "6": "IR_DRV", "7": "NC", "8": "NC",
        "9": "VLED+", "10": "VLED+", "11": "VDD", "12": "GND", "13": "~{INT}", "14": "NC"},
 "U3": {"1": "VDD_IO", "2": "NC", "3": "NC", "4": "SCL", "5": "GND", "6": "SDA", "7": "SA0", "8": "CS",
        "9": "INT2", "10": "RES", "11": "INT1", "12": "GND", "13": "ADC3", "14": "VDD", "15": "ADC2", "16": "ADC1"},
 "U4": {"1": "STAT", "2": "VSS", "3": "VBAT", "4": "VDD", "5": "PROG"},
 "U5": {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
 "U6": {"1": "GND", "2": "VOUT", "3": "VIN"},
 "J1": {"A1": "GND", "A4": "VBUS", "A5": "CC1", "A6": "D+", "A7": "D-", "A8": "SBU1", "A9": "VBUS", "A12": "GND",
        "B1": "GND", "B4": "VBUS", "B5": "CC2", "B6": "D+", "B7": "D-", "B8": "SBU2", "B9": "VBUS", "B12": "GND",
        "S1": "SHIELD"},
 "Q1": {"1": "G", "2": "S", "3": "D"},
 "SW1": {"1": "1", "2": "2"},
 "J2": {"1": "GND", "2": "VCC", "3": "SCL", "4": "SDA", "5": "RES", "6": "DC", "7": "CS", "8": "BLK"},
 "BT1": {"1": "+", "2": "-"}, "M1": {"1": "+", "2": "-"},
}
TWO_PIN = {"R": "res", "C": "cap", "D": "diode"}

def kind(p):
    r = p["ref"].rstrip("0123456789")
    if r in TWO_PIN and p["ref"] not in ("D1",) or p["ref"] in ("D1", "D2"):
        return TWO_PIN.get(r, "diode")
    return "box"

def symname(p):
    k = kind(p)
    if k == "res": return "R"
    if k == "cap": return "C"
    if k == "diode": return "LED" if "LED" in p["value"] else "D"
    return p["value"].replace(" ", "_").replace("/", "_").replace("+", "P").replace(".", "_")

# ------------------------------------------------------------ symbol definitions
def font(s=1.27): return f"(effects (font (size {s} {s})))"

def pin(num, name, x, y, ang, length=G, hide_name=False):
    return (f'      (pin passive line (at {x} {y} {ang}) (length {length})\n'
            f'        (name {q(name)} {font()}) (number {q(num)} {font()}))\n')

def sym_box(name, p, ref_prefix):
    names = NAMES[p["ref"]]
    nums = list(names.keys())
    left, right = nums[: (len(nums) + 1) // 2], nums[(len(nums) + 1) // 2:]
    h = max(len(left), len(right)) * G + G
    w = 15.24 if max(len(n) for n in names.values()) > 4 else 10.16
    top = snap(h / 2)
    body = f'    (symbol {q(name + "_0_1")}\n      (rectangle (start {-w/2} {top}) (end {w/2} {-top}) (stroke (width 0.254) (type default)) (fill (type background)))\n    )\n'
    pins = ""
    pos = {}
    for k, n in enumerate(left):
        y = snap(top - G - k * G); x = -w / 2 - G
        pins += pin(n, names[n], x, y, 0); pos[n] = (x, y)
    for k, n in enumerate(right):
        y = snap(top - G - k * G); x = w / 2 + G
        pins += pin(n, names[n], x, y, 180); pos[n] = (x, y)
    s = (f'  (symbol {q(name)} (in_bom yes) (on_board yes)\n'
         f'    (property "Reference" {q(ref_prefix)} (at 0 {top + 1.27} 0) {font()})\n'
         f'    (property "Value" {q(name)} (at 0 {-top - 1.27} 0) {font()})\n'
         f'    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
         f'    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
         + body + f'    (symbol {q(name + "_1_1")}\n' + pins + '    )\n  )\n')
    return s, pos, (w, h)

def sym_two(name, k):
    if k == "res":
        g = '      (rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))\n'
    elif k == "cap":
        g = ('      (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy 0 2.54) (xy 0 0.762)) (stroke (width 0) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy 0 -2.54) (xy 0 -0.762)) (stroke (width 0) (type default)) (fill (type none)))\n')
    else:  # diode, cathode = pin 1 at the top (current flows up)
        g = ('      (polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016) (xy 0 1.016) (xy -1.27 -1.016)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy -1.27 1.016) (xy 1.27 1.016)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy 0 2.54) (xy 0 1.016)) (stroke (width 0) (type default)) (fill (type none)))\n'
             '      (polyline (pts (xy 0 -2.54) (xy 0 -1.016)) (stroke (width 0) (type default)) (fill (type none)))\n')
        if name == "LED":
            g += ('      (polyline (pts (xy 1.778 0.254) (xy 3.048 1.524)) (stroke (width 0.2) (type default)) (fill (type none)))\n'
                  '      (polyline (pts (xy 1.778 -0.762) (xy 3.048 0.508)) (stroke (width 0.2) (type default)) (fill (type none)))\n')
    prefix = {"res": "R", "cap": "C"}.get(k, "D")
    s = (f'  (symbol {q(name)} (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)\n'
         f'    (property "Reference" {q(prefix)} (at 2.54 1.27 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
         f'    (property "Value" {q(name)} (at 2.54 -1.27 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
         f'    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
         f'    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
         f'    (symbol {q(name + "_0_1")}\n' + g + '    )\n'
         f'    (symbol {q(name + "_1_1")}\n' + pin("1", "1", 0, 5.08, 270) + pin("2", "2", 0, -5.08, 90) + '    )\n  )\n')
    return s, {"1": (0, 5.08), "2": (0, -5.08)}, (2.54, 10.16)

symdefs, sympos, symsize = {}, {}, {}
for p in P:
    n = symname(p)
    if n in symdefs: continue
    k = kind(p)
    if k == "box":
        prefix = "".join(c for c in p["ref"] if c.isalpha())
        s, pos, sz = sym_box(n, p, prefix)
    else:
        s, pos, sz = sym_two(n, k)
    symdefs[n], sympos[n], symsize[n] = s, pos, sz

lib = "(kicad_symbol_lib (version 20220914) (generator spitalul_virtual)\n" + "".join(symdefs.values()) + ")\n"
os.makedirs(os.path.join(KDIR, "lib"), exist_ok=True)
open(os.path.join(KDIR, "lib", "SpitalulVirtual.kicad_sym"), "w").write(lib)

# ------------------------------------------------------------ layout (A3, blocks)
BLOCKS = [
    ("MCU  ESP32-C3 (WiFi + BLE, native USB)", 30, 40, ["U1", "R1", "C1", "C2", "C3", "R11", "R12", "SW1"]),
    ("Heart rate + SpO2  (MAX30102, skin side)", 170, 40, ["U2", "C10", "C11", "C12", "U6", "C8", "C9"]),
    ("Step counter  (LIS3DH)", 300, 40, ["U3", "C13", "C14", "R6", "R7"]),
    ("USB-C + Li-Po charger", 30, 165, ["J1", "R2", "R3", "C4", "U4", "R4", "C5", "R5", "D2"]),
    ("3.3 V supply + battery sense", 190, 165, ["U5", "C6", "C7", "R8", "R9", "C15", "BT1"]),
    ("Display, vibration motor", 300, 165, ["J2", "R10", "Q1", "D1", "R13", "M1"]),
]
byref = {p["ref"]: p for p in P}
out = []
wires, labels, ncs = [], [], []
root = U()

def place(p, X, Y):
    n = symname(p); pos = sympos[n]
    pins_txt = "".join(f'    (pin {q(num)} (uuid {U()}))\n' for num in pos)
    k = kind(p)
    fp = p["fp"].split(":")[1]
    w = symsize[n][0]
    refat = (X + 2.54, Y - 1.27) if k != "box" else (X, Y - symsize[n][1] / 2 - 1.27)
    valat = (X + 2.54, Y + 1.27) if k != "box" else (X, Y + symsize[n][1] / 2 + 1.27)
    just = " (justify left)" if k != "box" else ""
    out.append(
        f'  (symbol (lib_id {q("SpitalulVirtual:" + n)}) (at {X} {Y} 0) (unit 1)\n'
        f'    (in_bom {"yes" if p["lcsc"] else "no"}) (on_board yes) (dnp no) (uuid {U()})\n'
        f'    (property "Reference" {q(p["ref"])} (at {refat[0]} {refat[1]} 0) (effects (font (size 1.27 1.27)){just}))\n'
        f'    (property "Value" {q(p["value"])} (at {valat[0]} {valat[1]} 0) (effects (font (size 1.27 1.27)){just}))\n'
        f'    (property "Footprint" {q("SpitalulVirtual:" + fp)} (at {X} {Y} 0) (effects (font (size 1.27 1.27)) hide))\n'
        f'    (property "Datasheet" "" (at {X} {Y} 0) (effects (font (size 1.27 1.27)) hide))\n'
        f'    (property "LCSC" {q(p["lcsc"])} (at {X} {Y} 0) (effects (font (size 1.27 1.27)) hide))\n'
        f'    (property "Description" {q(p["desc"])} (at {X} {Y} 0) (effects (font (size 1.27 1.27)) hide))\n'
        + pins_txt +
        f'    (instances (project {q(PROJECT)} (path {q("/" + root)} (reference {q(p["ref"])}) (unit 1))))\n  )\n')
    # wire stub + label on every pin
    for num, (px, py) in pos.items():
        ax, ay = snap(X + px), snap(Y - py)
        net = p["pins"].get(num)
        if k == "box":
            dx = -1 if px < 0 else 1
        else:
            dx = 0
        if k == "box":
            bx, by = snap(ax + dx * 2.54), ay
            ang = 180 if dx < 0 else 0
            just = "right" if dx < 0 else "left"
        else:
            dy = -1 if py > 0 else 1
            bx, by = ax, snap(ay + dy * 2.54)
            ang = 90 if dy < 0 else 270
            just = "left"
        if net is None:
            ncs.append(f'  (no_connect (at {ax} {ay}) (uuid {U()}))\n')
            continue
        wires.append(f'  (wire (pts (xy {ax} {ay}) (xy {bx} {by})) (stroke (width 0) (type default)) (uuid {U()}))\n')
        labels.append(f'  (label {q(net)} (at {bx} {by} {ang}) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {U()}))\n')

texts = []
for title, bx, by, refs in BLOCKS:
    texts.append(f'  (text {q(title)} (at {bx} {by - 12} 0) (effects (font (size 2.2 2.2) bold) (justify left bottom)) (uuid {U()}))\n')
    x, y = bx + 20, by + 5
    col_h = 0
    boxes = [r for r in refs if kind(byref[r]) == "box"]
    small = [r for r in refs if kind(byref[r]) != "box"]
    for r in boxes:
        n = symname(byref[r]); w, h = symsize[n]
        X, Y = snap(x), snap(y + h / 2)
        place(byref[r], X, Y)
        y += h + 12
        col_h = max(col_h, y)
    sx, sy = bx + 62, by + 8
    for k2, r in enumerate(small):
        X = snap(sx + (k2 % 4) * 15.24); Y = snap(sy + (k2 // 4) * 22.86)
        place(byref[r], X, Y)

notes = [
    "SPITALUL VIRTUAL smartwatch  -  made by Stancu Patrick",
    "Every pin has a net label: same label text = same wire. Generated from scripts/design.py.",
    "Power: USB-C 5V -> MCP73831 charger (~210 mA) -> Li-Po -> ME6211 3.3V. MAX30102 core runs from XC6206 1.8V.",
    "Display: GC9A01 1.28in round 240x240 SPI, wired to the 8 edge pads. RES is tied to the ESP32 EN (resets together).",
    "Hobby project - heart-rate / SpO2 readings are NOT for medical use.",
]
for k, s in enumerate(notes):
    texts.append(f'  (text {q(s)} (at 30 {246 + k * 4.5} 0) (effects (font (size 1.8 1.8)) (justify left bottom)) (uuid {U()}))\n')

sch = (f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {root})\n  (paper "A3")\n'
       f'  (title_block (title "Spitalul Virtual Smartwatch") (date "2026-10-26") (rev "1.0") (company "made by Stancu Patrick")\n'
       f'    (comment 1 "ESP32-C3 + MAX30102 + LIS3DH, USB-C charging"))\n'
       f'  (lib_symbols\n' + "".join(s.replace('(symbol "', '(symbol "SpitalulVirtual:', 1) for s in symdefs.values()) + '  )\n'
       + "".join(out) + "".join(wires) + "".join(labels) + "".join(ncs) + "".join(texts) +
       f'  (sheet_instances (path "/" (page "1")))\n)\n')
open(os.path.join(KDIR, PROJECT + ".kicad_sch"), "w").write(sch)

# project / library tables
open(os.path.join(KDIR, "sym-lib-table"), "w").write(
    '(sym_lib_table\n  (lib (name "SpitalulVirtual")(type "KiCad")(uri "${KIPRJMOD}/lib/SpitalulVirtual.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
open(os.path.join(KDIR, "fp-lib-table"), "w").write(
    '(fp_lib_table\n  (lib (name "SpitalulVirtual")(type "KiCad")(uri "${KIPRJMOD}/lib/SpitalulVirtual.pretty")(options "")(descr "Project footprints"))\n)\n')
print("schematic written,", len(P), "symbols,", len(labels), "labels,", len(ncs), "no-connects")
