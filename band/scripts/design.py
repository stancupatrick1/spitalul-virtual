"""
Spitalul Virtual BAND (screenless wearable) - single source of truth for the circuit.
Schematic and PCB are both generated from this file.

Coordinates in mm relative to the board centre (x along the band module, y across, y down = KiCad).
side: "F" = top (battery side), "B" = bottom (skin side, sensors face the wrist).
"""
import math

PROJECT = "spitalul_virtual_band"
TITLE = "Spitalul Virtual Band"
BOARD_L, BOARD_W, CORNER_R = 40.0, 24.0, 5.0     # rounded-rectangle "pill" board
HL, HW = BOARD_L / 2, BOARD_W / 2
BOARD_R = HL                                      # half extent (router grid size)
CENTER = (100.0, 100.0)

def outline_pts(inset=0.0, n=24):
    """rounded rectangle outline, clockwise, as a list of (x, y)"""
    r = CORNER_R - inset; hl, hw = HL - inset, HW - inset
    pts = []
    for cx, cy, a0 in ((hl - CORNER_R, -hw + r, -90), (hl - CORNER_R, hw - r, 0),
                       (-hl + CORNER_R, hw - r, 90), (-hl + CORNER_R, -hw + r, 180)):
        cx = math.copysign(hl - r, cx); cy = math.copysign(hw - r, cy)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def outline_poly(inset=0.0):
    from shapely.geometry import Polygon
    return Polygon(outline_pts(inset))

GND, VBUS, VBAT, V33, V18 = "GND", "VBUS", "VBAT", "+3V3", "+1V8"

P = []
def part(ref, value, fp, lcsc, side, x, y, rot, pins, desc=""):
    P.append(dict(ref=ref, value=value, fp=fp, lcsc=lcsc, side=side, x=x, y=y, rot=rot, pins=pins, desc=desc))

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
MOD_X = -5.6          # module origin; antenna points to -x (left end of the band)
USB_X = HL - 4.17     # USB-C origin; opening flush with the +x end

# ---------------------------------------------------------------- top side
part("U1", "ESP32-C3-WROOM-02-N4", "RF_Module:ESP32-C3-WROOM-02", "C2934560", "F", MOD_X, 0, 90, {
    "1": V33, "2": "EN", "3": "SCL", "4": "SDA", "5": "TEMP_ALERT", "6": "LED_STAT",
    "7": "IO8", "8": "BTN", "9": GND, "10": None, "11": "HR_INT", "12": "ACC_INT",
    "13": "USB_D-", "14": "USB_D+", "15": "VBAT_SENSE", "16": "IO2", "17": None,
    "18": "MOTOR_EN", "19": GND}, "MCU module, WiFi/BLE, PCB antenna")
part("J1", "USB-C 16P", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "F", USB_X, 0, 90, {
    "A1": GND, "B12": GND, "A12": GND, "B1": GND,
    "A4": VBUS, "B9": VBUS, "A9": VBUS, "B4": VBUS,
    "A5": "CC1", "B5": "CC2", "A6": "USB_D+", "B6": "USB_D+", "A7": "USB_D-", "B7": "USB_D-",
    "A8": None, "B8": None, "S1": GND}, "USB-C receptacle (charging + programming)")
part("SW1", "EVQP7C01P", "Button_Switch_SMD:SW_SPST_EVQP7C", "C388883", "F", 10.4, 9.8, 0, {
    "1": "BTN", "2": GND}, "Side push button")
part("U4", "MCP73831T-2ACI/OT", "Package_TO_SOT_SMD:SOT-23-5", "C424093", "F", 5.4, -5.6, 0, {
    "1": "CHG_STAT", "2": GND, "3": VBAT, "4": VBUS, "5": "PROG"}, "Li-Po charger 4.2 V")
part("C4",  "10uF",  C0603, "C19702", "F", 8.6, -5.6, 90,  {"1": VBUS, "2": GND}, "VBUS bulk")
part("C5",  "10uF",  C0603, "C19702", "F", 2.6, -5.6, 90,  {"1": VBAT, "2": GND}, "Charger out")
part("R4",  "4.7k",  R0402, "C25900", "F", 5.4, -8.4, 0,   {"1": "PROG", "2": GND}, "Charge current ~210mA")
part("U5", "ME6211C33M5G-N", "Package_TO_SOT_SMD:SOT-23-5", "C82942", "F", 5.4, 3.8, 0, {
    "1": VBAT, "2": GND, "3": VBAT, "4": None, "5": V33}, "LDO 3.3 V 500 mA")
part("C6",  "10uF",  C0603, "C19702", "F", 2.6, 3.8, 90,   {"1": VBAT, "2": GND}, "LDO in")
part("C7",  "10uF",  C0603, "C19702", "F", 8.6, 3.8, 90,   {"1": V33, "2": GND}, "LDO out")
part("R2",  "5.1k",  R0402, "C25905", "B", 9.0, 0.0, 0,    {"1": "CC1", "2": GND}, "USB-C CC1")
part("R3",  "5.1k",  R0402, "C25905", "B", 9.0, 1.4, 0,   {"1": "CC2", "2": GND}, "USB-C CC2")
part("Q1", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", "F", 9.2, -9.0, 0, {
    "1": "MOTOR_EN", "2": GND, "3": "MOTOR-"}, "N-MOSFET motor driver")
part("R13", "100k",  R0402, "C25741", "F", 6.0, -10.4, 0,  {"1": "MOTOR_EN", "2": GND}, "Motor gate pull-down")
part("D1", "1N4148WS", "Diode_SMD:D_SOD-323", "C2128", "F", 2.8, -9.6, 90, {
    "1": VBAT, "2": "MOTOR-"}, "Motor flyback diode")
part("D3", "Green LED", "LED_SMD:LED_0603_1608Metric", "C72043", "F", 12.6, -6.7, 0, {
    "1": GND, "2": "LED_STAT_A"}, "Status LED (visible through the top)")
part("R14", "1k",    R0402, "C11702", "F", 12.6, -8.1, 0,  {"1": "LED_STAT", "2": "LED_STAT_A"}, "Status LED resistor")
part("BT1", "LiPo 302025 3.7V", "SpitalulVirtual:BatteryPads", "", "F", 0, 0, 0, {
    "1": VBAT, "2": GND}, "Battery pads (use a cell with protection PCB)")
part("M1", "Vibration motor", "SpitalulVirtual:MotorPads", "", "F", 0, 0, 0, {
    "1": VBAT, "2": "MOTOR-"}, "Coin vibration motor 8 mm")

# ---------------------------------------------------------------- bottom side (skin)
part("U2", "MAX30102EFD+T", "OptoDevice:Maxim_OLGA-14_3.3x5.6mm_P0.8mm", "C6454833", "B", 0.0, 0.0, 0, {
    "1": None, "2": "SCL", "3": "SDA", "4": GND, "5": None, "6": None, "7": None, "8": None,
    "9": V33, "10": V33, "11": V18, "12": GND, "13": "HR_INT", "14": None},
    "Pulse oximeter / heart-rate sensor")
part("U7", "TMP117AIDRVR", "Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm", "C699536", "B", -10.0, 0.0, 0, {
    "1": "SCL", "2": GND, "3": "TEMP_ALERT", "4": GND, "5": V33, "6": "SDA", "7": GND},
    "Skin temperature sensor +/-0.1 C (I2C 0x48)")
part("U3", "LIS3DHTR", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", "C15134", "B", 14.8, 0.0, 180, {
    "1": V33, "2": None, "3": None, "4": "SCL", "5": GND, "6": "SDA", "7": V33, "8": V33,
    "9": None, "10": GND, "11": "ACC_INT", "12": GND, "13": None, "14": V33, "15": None, "16": None},
    "3-axis accelerometer (step counter), I2C 0x19")
part("U6", "XC6206P182MR", "Package_TO_SOT_SMD:SOT-23", "C347373", "B", 9.8, 4.6, 0, {
    "1": GND, "2": V18, "3": V33}, "LDO 1.8 V")
part("D2", "Red LED", "LED_SMD:LED_0603_1608Metric", "C2286", "B", 10.0, -4.4, 0, {
    "1": "CHG_STAT", "2": "LED_A"}, "Charging indicator")
part("R5",  "1k",    R0402, "C11702", "B", 10.0, -6.0, 0,    {"1": VBUS, "2": "LED_A"}, "LED resistor")
part("C16", "100nF", C0402, "C1525",  "B", -10.0, -2.2, 0,  {"1": V33, "2": GND}, "TMP117 decoupling")
part("R1",  "10k",   R0402, "C25744", "B", -10.0, 2.8, 0,   {"1": V33, "2": "EN"}, "EN pull-up")
part("C1",  "1uF",   C0402, "C52923", "B", -10.0, 4.2, 0,   {"1": "EN", "2": GND}, "EN delay")
part("C2",  "10uF",  C0603, "C19702", "B", -7.6, 4.0, 90,   {"1": V33, "2": GND}, "MCU bulk")
part("C3",  "100nF", C0402, "C1525",  "B", -5.6, 4.0, 90,   {"1": V33, "2": GND}, "MCU decoupling")
part("R11", "10k",   R0402, "C25744", "B", -3.9, 4.0, 90,   {"1": V33, "2": "IO8"}, "GPIO8 strap pull-up")
part("R12", "10k",   R0402, "C25744", "B", 2.6, 5.0, 90,    {"1": V33, "2": "BTN"}, "Button / GPIO9 strap pull-up")
part("R10", "10k",   R0402, "C25744", "B", -10.0, -3.6, 0,  {"1": V33, "2": "IO2"}, "GPIO2 strap pull-up")
part("R8",  "100k",  R0402, "C25741", "B", -7.6, -4.0, 90,  {"1": VBAT, "2": "VBAT_SENSE"}, "Battery divider")
part("R9",  "100k",  R0402, "C25741", "B", -6.4, -4.0, 90,  {"1": "VBAT_SENSE", "2": GND}, "Battery divider")
part("C15", "100nF", C0402, "C1525",  "B", -5.2, -4.0, 90,  {"1": "VBAT_SENSE", "2": GND}, "ADC filter")
part("R6",  "4.7k",  R0402, "C25900", "B", -3.6, -4.0, 90,  {"1": V33, "2": "SCL"}, "I2C pull-up")
part("R7",  "4.7k",  R0402, "C25900", "B", -2.4, -4.0, 90,  {"1": V33, "2": "SDA"}, "I2C pull-up")
part("C10", "100nF", C0402, "C1525",  "B", -2.6, 3.6, 90,   {"1": V18, "2": GND}, "MAX30102 VDD")
part("C11", "10uF",  C0603, "C19702", "B", 0.2, -4.7, 0,    {"1": V33, "2": GND}, "MAX30102 VLED bulk")
part("C12", "100nF", C0402, "C1525",  "B", 2.6, -1.8, 90,   {"1": V33, "2": GND}, "MAX30102 VLED")
part("C8",  "1uF",   C0402, "C52923", "B", 9.8, 6.8, 0,    {"1": V18, "2": GND}, "1V8 out")
part("C9",  "1uF",   C0402, "C52923", "B", 7.2, 4.6, 90,     {"1": V33, "2": GND}, "1V8 in")
part("C13", "100nF", C0402, "C1525",  "B", 17.4, 1.2, 90,   {"1": V33, "2": GND}, "LIS3DH decoupling")
part("C14", "10uF",  C0603, "C19702", "B", 17.0, -2.5, 0,    {"1": V33, "2": GND}, "LIS3DH bulk")

# edge pads (hand-soldered wires, not assembled): positions relative to the board centre
BATT_PADS = [((14.0, -9.4), "B+"), ((17.0, -7.8), "B-")]
MOTOR_PADS = [((14.8, 9.4), "M+"), ((17.6, 6.6), "M-")]

# hand-placed copper: join the two USB-C VBUS pads with a bottom-layer bridge
_vx = USB_X - 4.04 - 1.35
FIXED_TRACKS = [("VBUS", 0, [(USB_X - 4.04 - 0.5, -2.45), (_vx, -2.45)], 0.3),
                ("VBUS", 0, [(USB_X - 4.04 - 0.5, 2.45), (_vx, 2.45)], 0.3),
                ("VBUS", 1, [(_vx, -2.45), (_vx, 2.45)], 0.3)]
FIXED_VIAS = [("VBUS", _vx, -2.45), ("VBUS", _vx, 2.45)]
# USB-C ground pins straight to the shell pads (shell = ground on both layers)
_px = USB_X - 4.04
FIXED_TRACKS += [("GND", 0, [(_px, 3.25), (_px + 0.9, 4.32)], 0.3), ("GND", 0, [(_px, -3.25), (_px + 0.9, -4.32)], 0.3)]
# bottom-layer ground frame joining the four shell legs (keeps the area under the USB-C one ground)
_s1, _s2 = USB_X - 3.13, USB_X + 1.05
FIXED_TRACKS += [("GND", 1, [(_s1, 4.32), (_s2, 4.32), (HL - 1.3, 3.0), (HL - 1.3, -3.0), (_s2, -4.32), (_s1, -4.32)], 0.3)]
# LIS3DH ground pin 5 and its capacitors straight onto that frame
FIXED_TRACKS += [("GND", 1, [(16.03, 1.0), (16.5, 1.0), (17.18, 1.68), (HL - 1.3, 1.68)], 0.2),
                 ("GND", 1, [(17.78, -2.5), (HL - 1.3, -2.5)], 0.3)]
POWER_FIRST = False
ANTENNA_KEEPOUT = [(-HL - 1, -HW - 1), (MOD_X - 6.7, -HW - 1), (MOD_X - 6.7, HW + 1), (-HL - 1, HW + 1)]

def nets():
    s = set()
    for p in P:
        for n in p["pins"].values():
            if n: s.add(n)
    order = [GND, V33, VBAT, VBUS, V18]
    return order + sorted(s - set(order))

if __name__ == "__main__":
    print(len(P), "parts,", len(nets()), "nets")
