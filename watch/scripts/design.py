"""
Spitalul Virtual smartwatch - single source of truth for the circuit.
Both the schematic and the PCB are generated from this file, so they always match.

Coordinates are in mm relative to the board centre (y grows downwards, KiCad style).
side: "F" = top (battery side), "B" = bottom (skin side, sensor faces the wrist).
"""

PROJECT = "spitalul_virtual_watch"
BOARD_R = 21.0          # 42 mm round board
FLAT_Y = 18.0           # flat edge at the bottom for the USB-C connector
CENTER = (100.0, 100.0) # where the board sits on the KiCad page

# ---------------------------------------------------------------- nets
# Net names used everywhere
GND, VBUS, VBAT, V33, V18 = "GND", "VBUS", "VBAT", "+3V3", "+1V8"

# ---------------------------------------------------------------- parts
# (ref, value, footprint "lib:name", lcsc, side, x, y, rot, {pad: net}, description)
P = []
def part(ref, value, fp, lcsc, side, x, y, rot, pins, desc=""):
    P.append(dict(ref=ref, value=value, fp=fp, lcsc=lcsc, side=side, x=x, y=y,
                  rot=rot, pins=pins, desc=desc))

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"

# ---- MCU: ESP32-C3 (WiFi + Bluetooth LE), native USB for programming
part("U1", "ESP32-C3-WROOM-02-N4", "RF_Module:ESP32-C3-WROOM-02", "C2934560", "F", 0, -5, 0, {
    "1": V33, "2": "EN", "3": "SCL", "4": "SDA", "5": "LCD_SCK", "6": "LCD_MOSI",
    "7": "IO8", "8": "BTN", "9": GND, "10": "LCD_CS", "11": "HR_INT", "12": "ACC_INT",
    "13": "USB_D-", "14": "USB_D+", "15": "VBAT_SENSE", "16": "LCD_BLK", "17": "LCD_DC",
    "18": "MOTOR_EN", "19": GND}, "MCU module, WiFi/BLE, PCB antenna")

# ---- Heart rate + SpO2 sensor (on the skin side)
part("U2", "MAX30102EFD+T", "OptoDevice:Maxim_OLGA-14_3.3x5.6mm_P0.8mm", "C6454833", "B", 0, 5.5, 0, {
    "1": None, "2": "SCL", "3": "SDA", "4": GND, "5": None, "6": None, "7": None, "8": None,
    "9": V33, "10": V33, "11": V18, "12": GND, "13": "HR_INT", "14": None},
    "Pulse oximeter / heart-rate sensor")

# ---- Accelerometer for step counting
part("U3", "LIS3DHTR", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", "C15134", "B", -5.0, -6.4, 0, {
    "1": V33, "2": None, "3": None, "4": "SCL", "5": GND, "6": "SDA", "7": V33, "8": V33,
    "9": None, "10": GND, "11": "ACC_INT", "12": GND, "13": None, "14": V33, "15": None, "16": None},
    "3-axis accelerometer (step counter)")

# ---- Li-Po charger from USB-C (about 210 mA with R4 = 4.7k)
part("U4", "MCP73831T-2ACI/OT", "Package_TO_SOT_SMD:SOT-23-5", "C424093", "F", -10, 5, 0, {
    "1": "CHG_STAT", "2": GND, "3": VBAT, "4": VBUS, "5": "PROG"}, "Li-Po charger 4.2 V")

# ---- 3.3 V regulator (500 mA)
part("U5", "ME6211C33M5G-N", "Package_TO_SOT_SMD:SOT-23-5", "C82942", "F", 10, 5, 0, {
    "1": VBAT, "2": GND, "3": VBAT, "4": None, "5": V33}, "LDO 3.3 V 500 mA")

# ---- 1.8 V regulator for the MAX30102 core
part("U6", "XC6206P182MR", "Package_TO_SOT_SMD:SOT-23", "C347373", "B", -6.5, 5, 0, {
    "1": GND, "2": V18, "3": V33}, "LDO 1.8 V")

# ---- USB-C
part("J1", "USB-C 16P", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948", "F", 0, 13.83, 0, {
    "A1": GND, "B12": GND, "A12": GND, "B1": GND,
    "A4": VBUS, "B9": VBUS, "A9": VBUS, "B4": VBUS,
    "A5": "CC1", "B5": "CC2", "A6": "USB_D+", "B6": "USB_D+", "A7": "USB_D-", "B7": "USB_D-",
    "A8": None, "B8": None, "S1": GND}, "USB-C receptacle (charging + programming)")

# ---- Side button (BOOT / user button)
part("SW1", "EVQP7C01P", "Button_Switch_SMD:SW_SPST_EVQP7C", "C388883", "F", 18.0, -4, 90, {
    "1": "BTN", "2": GND}, "Side push button")

# ---- Vibration motor driver
part("Q1", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", "F", 14.0, 8.9, 0, {
    "1": "MOTOR_EN", "2": GND, "3": "MOTOR-"}, "N-MOSFET motor driver")
part("D1", "1N4148WS", "Diode_SMD:D_SOD-323", "C2128", "F", 9.6, 13.5, 0, {
    "1": VBAT, "2": "MOTOR-"}, "Motor flyback diode")

# ---- Charge LED (bottom side, visible through a pin-hole in the case)
part("D2", "Red LED", "LED_SMD:LED_0603_1608Metric", "C2286", "B", 7.5, 13.2, 0, {
    "1": "CHG_STAT", "2": "LED_A"}, "Charging indicator")

# ---- Edge pads (hand soldered, no assembly)
part("J2", "Display GC9A01 1.28in", "SpitalulVirtual:DisplayPads_Arc", "", "F", 0, 0, 0, {
    "1": GND, "2": V33, "3": "LCD_SCK", "4": "LCD_MOSI", "5": "EN", "6": "LCD_DC",
    "7": "LCD_CS", "8": "LCD_BLK"}, "Wire pads to round 240x240 GC9A01 display")
part("BT1", "LiPo 402530 3.7V", "SpitalulVirtual:BatteryPads_Arc", "", "F", 0, 0, 0, {
    "1": VBAT, "2": GND}, "Battery pads (use a cell with protection PCB)")
part("M1", "Vibration motor", "SpitalulVirtual:MotorPads_Arc", "", "F", 0, 0, 0, {
    "1": VBAT, "2": "MOTOR-"}, "Coin vibration motor 8-10 mm")

# ---- Passives                ref   value    fp     lcsc     side  x      y     rot  pins
part("R1",  "10k",   R0402, "C25744", "F", -11.2, -9.8, 0,  {"1": V33, "2": "EN"}, "EN pull-up")
part("C1",  "1uF",   C0402, "C52923", "F", -11.2, -11.0, 0,  {"1": "EN", "2": GND}, "EN delay")
part("C2",  "10uF",  C0603, "C19702", "F", -13.4, -10.0, 90, {"1": V33, "2": GND}, "MCU bulk")
part("C3",  "100nF", C0402, "C1525",  "F", -11.2, -8.6,  0,  {"1": V33, "2": GND}, "MCU decoupling")
part("R2",  "5.1k",  R0402, "C25905", "F", -4.2, 7.6, 90,    {"1": "CC1", "2": GND}, "USB-C CC1")
part("R3",  "5.1k",  R0402, "C25905", "F", 4.2, 7.6, 90,     {"1": "CC2", "2": GND}, "USB-C CC2")
part("C4",  "10uF",  C0603, "C19702", "F", -7.2, 10.2, 90,   {"1": VBUS, "2": GND}, "VBUS bulk")
part("R4",  "4.7k",  R0402, "C25900", "F", -10.0, 7.8, 0,    {"1": "PROG", "2": GND}, "Charge current ~210mA")
part("C5",  "10uF",  C0603, "C19702", "F", -13.6, 5.0, 90,   {"1": VBAT, "2": GND}, "Charger out")
part("R5",  "1k",    R0402, "C11702", "B", 7.5, 11.4, 0,       {"1": VBUS, "2": "LED_A"}, "LED resistor")
part("C6",  "10uF",  C0603, "C19702", "F", 13.6, 5.0, 90,    {"1": VBAT, "2": GND}, "LDO in")
part("C7",  "10uF",  C0603, "C19702", "F", 10.0, 8.5, 0,     {"1": V33, "2": GND}, "LDO out")
part("C8",  "1uF",   C0402, "C52923", "B", -6.5, 2.6, 0,     {"1": V18, "2": GND}, "1V8 out")
part("C9",  "1uF",   C0402, "C52923", "B", -9.0, 5.0, 90,    {"1": V33, "2": GND}, "1V8 in")
part("C10", "100nF", C0402, "C1525",  "B", -3.2, 3.0, 90,    {"1": V18, "2": GND}, "MAX30102 VDD")
part("C11", "10uF",  C0603, "C19702", "B", 3.4, 3.2, 90,     {"1": V33, "2": GND}, "MAX30102 VLED bulk")
part("C12", "100nF", C0402, "C1525",  "B", 3.2, 7.2, 90,     {"1": V33, "2": GND}, "MAX30102 VLED")
part("R6",  "4.7k",  R0402, "C25900", "F", -11.2, 0.4, 0,    {"1": V33, "2": "SCL"}, "I2C pull-up")
part("R7",  "4.7k",  R0402, "C25900", "F", -11.2, 1.7, 0,    {"1": V33, "2": "SDA"}, "I2C pull-up")
part("C13", "100nF", C0402, "C1525",  "B", -5.0, -3.8, 0,  {"1": V33, "2": GND}, "LIS3DH decoupling")
part("C14", "10uF",  C0603, "C19702", "B", -8.1, -6.4, 90,   {"1": V33, "2": GND}, "LIS3DH bulk")
part("R8",  "100k",  R0402, "C25741", "F", 12.0, -8.6, 0,    {"1": VBAT, "2": "VBAT_SENSE"}, "Battery divider")
part("R9",  "100k",  R0402, "C25741", "F", 12.0, -9.9, 0,   {"1": "VBAT_SENSE", "2": GND}, "Battery divider")
part("C15", "100nF", C0402, "C1525",  "F", 14.2, -9.25, 90,   {"1": "VBAT_SENSE", "2": GND}, "ADC filter")
part("R10", "10k",   R0402, "C25744", "F", 12.0, -11.2, 0,   {"1": V33, "2": "LCD_BLK"}, "Backlight on by default / strap")
part("R11", "10k",   R0402, "C25744", "F", -11.2, -1.6, 0,   {"1": V33, "2": "IO8"}, "GPIO8 strap pull-up")
part("R12", "10k",   R0402, "C25744", "F", 13.6, -2.0, 90,   {"1": V33, "2": "BTN"}, "Button / GPIO9 strap pull-up")
part("R13", "100k",  R0402, "C25741", "F", 11.9, 11.2, 0,    {"1": "MOTOR_EN", "2": GND}, "Motor gate pull-down")

def nets():
    s = set()
    for p in P:
        for n in p["pins"].values():
            if n: s.add(n)
    order = [GND, V33, VBAT, VBUS, V18]
    return order + sorted(s - set(order))

if __name__ == "__main__":
    print(len(P), "parts,", len(nets()), "nets")
