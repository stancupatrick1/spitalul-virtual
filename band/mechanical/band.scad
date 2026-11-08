// =====================================================================
//  SPITALUL VIRTUAL BAND - screenless wearable, silicone pod + straps
//  made by Stancu Patrick
//
//  Render one part at a time:   openscad -D 'PART="band"' -o band.stl band.scad
//  PART = "band" | "cap" | "keeper" | "mold_bottom" | "mold_top" | "mold_core" | "assembly"
//
//  band : one piece - pod + straps. Print in TPU 85A-95A or cast in silicone (mold parts).
//  cap  : rigid top window (print in clear/smoked PETG or clear resin). The status LED
//         shines through it. Stretch the pod opening, drop in the electronics, press the cap in.
// =====================================================================
PART = "assembly";
$fn = 64;

// ---------------- electronics (mm) - matches the KiCad board
PCB_L = 40; PCB_W = 24; PCB_RC = 5;   // rounded-rectangle board
PCB_T = 1.0;
FLOOR = 0.8;                          // silicone under the board (with sensor windows)
GAP_B = 1.2;                          // room for skin-side parts
PCB_Z = FLOOR + GAP_B;                // bottom face of the PCB
PARTS_TOP = 3.3;                      // ESP32 module 3.2, USB-C 3.26
BATT = [25, 20, 3.0];                 // Li-Po 302025 (use 202025 for a 1 mm thinner band)
BATT_X = -6.0;                        // battery centre (PCB x), sits on the ESP32 module
MOTOR_D = 8.2; MOTOR_T = 2.8; MOTOR_X = 15.3;   // coin motor, glued on the USB-C shell

// ---------------- case
CLR = 0.2; WALL = 2.0;
CAP_T = 0.8;                          // top window thickness
LIP = 0.6;                            // silicone lip that holds the cap
Z_BATT = PCB_Z + PCB_T + PARTS_TOP + 0.1;
Z_IN   = Z_BATT + BATT[2] + 0.2;      // top of the electronics space = bottom of the cap
Z_TOP  = Z_IN + CAP_T + LIP;
OUT_L = PCB_L + 2 * (CLR + WALL); OUT_W = PCB_W + 2 * (CLR + WALL); OUT_RC = PCB_RC + CLR + WALL;
OPEN = [30, 15]; OPEN_RC = 4;         // top opening (cap is 1.6 mm bigger all round)
CAP  = [OPEN[0] + 3.2, OPEN[1] + 3.2];
echo(str("Band pod = ", OUT_L, " x ", OUT_W, " x ", Z_TOP, " mm"));

// ---------------- straps (along y, attached to the long sides)
STRAP_W = 20; STRAP_X = -4;           // strap centre line (keeps the button free)
STRAP_T = 2.4; STRAP_Z = 0.5;
STRAP_LONG = 115; STRAP_SHORT = 80; HOLE_PITCH = 7; HOLE_D = 2.6;

// KiCad coordinates have y pointing down -> mirror into the case frame
module pcb_frame() mirror([0, 1, 0]) children();

// features in PCB coordinates (see scripts/design.py)
MAX_XY = [0, 0];       MAX_WIN = [4.6, 6.6];
TMP_XY = [-10, 0];     TMP_WIN = 3.0;        // fill with a thermal pad or a 3 mm copper disc
CHG_LED_XY = [10.0, -4.4];
USB_W = 9.6; USB_H = 3.8; USB_Z = PCB_Z + PCB_T + 1.63;
BTN_XY = [10.4, 12.0]; BTN_Z = PCB_Z + PCB_T + 1.75;

module rr(l, w, r, h) linear_extrude(h) offset(r = r) square([l - 2 * r, w - 2 * r], center = true);

// -------------------------------------------------------------- shapes
module outer_body() {
    hull() {
        rr(OUT_L, OUT_W, OUT_RC, Z_TOP - 2.2);
        translate([0, 0, Z_TOP - 1.0]) rr(OUT_L - 1.6, OUT_W - 1.6, OUT_RC - 0.8, 0.01);
        translate([0, 0, Z_TOP - 0.01]) rr(OUT_L - 3.4, OUT_W - 3.4, OUT_RC - 1.7, 0.01);
        translate([0, 0, 0]) rr(OUT_L - 0.8, OUT_W - 0.8, OUT_RC - 0.4, 0.01);
    }
    // strap roots
    for (m = [0, 1]) mirror([0, m, 0]) hull() {
        translate([STRAP_X - STRAP_W / 2 - 1.5, OUT_W / 2 - 6, STRAP_Z]) cube([STRAP_W + 3, 2, STRAP_T + 2.2]);
        translate([STRAP_X - STRAP_W / 2, OUT_W / 2 + 3, STRAP_Z]) cube([STRAP_W, 2, STRAP_T]);
    }
}

module straps() {
    // +y: short strap with the peg
    translate([STRAP_X - STRAP_W / 2, OUT_W / 2, STRAP_Z]) difference() {
        hull() {
            cube([STRAP_W, 1, STRAP_T]);
            translate([STRAP_W / 2, STRAP_SHORT - STRAP_W / 2, 0]) cylinder(d = STRAP_W - 2, h = STRAP_T);
        }
        for (i = [1:6]) translate([2, 6 + i * 9, STRAP_T - 0.4]) cube([STRAP_W - 4, 0.8, 1]);
    }
    translate([STRAP_X, OUT_W / 2 + STRAP_SHORT - 14, STRAP_Z + STRAP_T - 0.01]) {
        cylinder(d = 2.4, h = 2.6);
        translate([0, 0, 2.2]) cylinder(d1 = 3.6, d2 = 2.4, h = 1.2);
    }
    // -y: long strap with holes
    translate([STRAP_X - STRAP_W / 2, -OUT_W / 2, STRAP_Z]) difference() {
        hull() {
            translate([0, -1, 0]) cube([STRAP_W, 1, STRAP_T]);
            translate([STRAP_W / 2, -(STRAP_LONG - STRAP_W / 2), 0]) cylinder(d = STRAP_W - 4, h = STRAP_T);
        }
        for (i = [0:10]) translate([STRAP_W / 2, -(40 + i * HOLE_PITCH), -1]) cylinder(d = HOLE_D, h = 10, $fn = 32);
    }
}

module cavity() {
    // board + parts + battery space
    translate([0, 0, PCB_Z]) rr(PCB_L + 2 * CLR, PCB_W + 2 * CLR, PCB_RC + CLR, Z_IN - PCB_Z);
    // space for skin-side parts; the ledge (1.2 mm) carries the board
    translate([0, 0, FLOOR]) rr(PCB_L - 2.4, PCB_W - 2.4, PCB_RC - 1.2, GAP_B + 0.01);
    // cap seat + opening through the lip
    translate([0, 0, Z_IN - 0.01]) rr(CAP[0], CAP[1], OPEN_RC + 1.6, CAP_T + 0.01);
    translate([0, 0, Z_IN]) rr(OPEN[0], OPEN[1], OPEN_RC, CAP_T + LIP + 1);
    pcb_frame() {
        // heart-rate / SpO2 window, temperature window, charge-LED pin hole
        translate([MAX_XY[0] - MAX_WIN[0] / 2, MAX_XY[1] - MAX_WIN[1] / 2, -1]) cube([MAX_WIN[0], MAX_WIN[1], FLOOR + 2]);
        translate([TMP_XY[0], TMP_XY[1], -1]) cylinder(d = TMP_WIN, h = FLOOR + 2);
        translate([CHG_LED_XY[0], CHG_LED_XY[1], -1]) cylinder(d = 1.2, h = FLOOR + 2, $fn = 24);
        // USB-C through the +x end wall, with a recess for the plug overmold
        translate([PCB_L / 2 - 1, -USB_W / 2, USB_Z - USB_H / 2]) cube([10, USB_W, USB_H]);
        translate([PCB_L / 2 + CLR + 1.0, -6.6, USB_Z - 3.5]) cube([10, 13.2, 7.0]);
        // side button: thin membrane (0.9 mm) in the wall
        translate([BTN_XY[0], BTN_XY[1], BTN_Z]) rotate([-90, 0, 0])
            difference() { cylinder(d = 6.0, h = OUT_W / 2 - BTN_XY[1] - 0.9); cylinder(d = 2.4, h = 50); }
    }
}

module button_bump() pcb_frame()
    translate([BTN_XY[0], OUT_W / 2 - 0.4, BTN_Z]) rotate([-90, 0, 0]) {
        cylinder(d = 4.2, h = 1.2);
        translate([0, 0, 1.2]) cylinder(d1 = 4.2, d2 = 3.4, h = 0.4);
    }

module bottom_text() mirror([1, 0, 0]) translate([0, 0, -0.01]) linear_extrude(0.45) {
    translate([0, 7.6]) text("SPITALUL VIRTUAL", size = 2.6, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
    translate([0, -7.8]) text("made by Stancu Patrick", size = 1.9, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
}

module top_ring() translate([0, 0, Z_TOP - 0.3]) difference() {   // decorative groove round the window
    rr(OPEN[0] + 5.4, OPEN[1] + 5.4, OPEN_RC + 2.7, 1);
    translate([0, 0, -1]) rr(OPEN[0] + 4.4, OPEN[1] + 4.4, OPEN_RC + 2.2, 3);
}

module band() difference() {
    union() { outer_body(); straps(); button_bump(); }
    cavity();
    bottom_text();
    top_ring();
}

module cap() {
    difference() {
        rr(CAP[0] - 0.2, CAP[1] - 0.2, OPEN_RC + 1.5, CAP_T);
        // small "SV" logo engraved on the inside face
        translate([-OPEN[0] / 2 + 4, 0, -0.01]) mirror([1, 0, 0]) linear_extrude(0.3)
            text("SV", size = 3, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
    }
    translate([0, 0, CAP_T - 0.01]) rr(OPEN[0] - 0.3, OPEN[1] - 0.3, OPEN_RC - 0.15, LIP);
}

module keeper() difference() {
    hull() for (x = [-1, 1]) translate([x * (STRAP_W / 2 + 1.6 - 1.5), 0, 0]) cylinder(r = 1.5 + 1.4, h = 6);
    hull() for (x = [-1, 1]) translate([x * (STRAP_W / 2 + 0.4 - 1.5), 0, -1]) cylinder(r = 1.5, h = 8);
}

// -------------------------------------------------------------- mold (3 parts)
M_MARGIN = 8;
M_X0 = -OUT_L / 2 - M_MARGIN; M_X = OUT_L + 2 * M_MARGIN;
M_Y0 = -(OUT_W / 2 + STRAP_LONG + M_MARGIN); M_Y = STRAP_LONG + STRAP_SHORT + OUT_W + 2 * M_MARGIN;
M_TOP = Z_TOP + 6;
module mold_block(z0, z1) translate([M_X0, M_Y0, z0]) cube([M_X, M_Y, z1 - z0]);
module keys(d) for (p = [[M_X0 + 4, M_Y0 + 4], [M_X0 + M_X - 4, M_Y0 + M_Y - 4], [M_X0 + M_X - 4, M_Y0 + 4]])
    translate([p[0], p[1], -3]) cylinder(d = d, h = 6, $fn = 32);
module mold_bottom() union() { mold_block(-6, 0); keys(4); bottom_text(); }
module mold_top() difference() {
    mold_block(0, M_TOP);
    outer_body(); straps(); button_bump(); top_ring_negative();
    keys(4.4);
    translate([0, 0, Z_TOP - 1]) rr(OPEN[0] + 0.4, OPEN[1] + 0.4, OPEN_RC + 0.2, 20);   // core seat
    translate([STRAP_X, OUT_W / 2 + 30, 0]) cylinder(d = 6, h = 50);                    // pour spout
    for (y = [-(OUT_W / 2 + STRAP_LONG - 4), OUT_W / 2 + STRAP_SHORT - 4]) translate([STRAP_X, y, 0]) cylinder(d = 1.6, h = 50);
}
module top_ring_negative() {}
module mold_core() {
    intersection() { cavity(); outer_body(); }
    translate([0, 0, Z_TOP - 1.01]) rr(OPEN[0], OPEN[1], OPEN_RC, 1.02);
    translate([0, 0, Z_TOP - 1]) rr(OPEN[0] + 6, OPEN[1] + 6, OPEN_RC + 3, 7);   // handle
}

if (PART == "band") band();
if (PART == "cap") cap();
if (PART == "keeper") keeper();
if (PART == "mold_bottom") mold_bottom();
if (PART == "mold_top") mold_top();
if (PART == "mold_core") mold_core();
if (PART == "assembly") {
    color("#2a2c30") band();
    color("#9fb4c8", 0.35) translate([0, 0, Z_IN]) cap();
    pcb_frame() color("#111") translate([0, 0, PCB_Z]) rr(PCB_L, PCB_W, PCB_RC, PCB_T);
}
