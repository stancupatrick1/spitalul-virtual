// =====================================================================
//  SPITALUL VIRTUAL smartwatch - silicone case with integrated straps
//  made by Stancu Patrick
//
//  Render one part at a time:   openscad -D 'PART="case"' -o case.stl case.scad
//  PART = "case" | "keeper" | "mold_bottom" | "mold_top" | "mold_core" | "assembly"
//
//  Print the case directly in flexible TPU (85A-95A), or cast it in platinum
//  silicone (Shore 20A-30A, e.g. Dragon Skin 20) using the 3 mold parts.
// =====================================================================
PART = "assembly";
$fn = 96;

// ---------------- electronics stack (mm) - matches the KiCad board
PCB_R     = 21.0;   // board radius
PCB_FLAT  = 18.0;   // flat edge (USB-C side), in PCB coordinates (y down)
PCB_T     = 1.0;
PCB_Z     = 1.8;    // bottom face of the PCB above the case bottom
PARTS_TOP = 3.4;    // tallest top-side part (ESP32 module 3.2, USB-C 3.26)
BATT      = [30, 25, 4.0];   // 402530 Li-Po
BATT_GAP  = 0.2;
DISP_D    = 36.4;   // 1.28in GC9A01 round panel + clearance
DISP_T    = 2.2;
VIEW_D    = 33.2;   // visible window (active area is 32.4)

// ---------------- case
CLR    = 0.2;
WALL   = 2.2;
FLOOR  = 0.8;       // floor thickness
LIP    = 1.2;       // top lip over the display
IN_R   = PCB_R + CLR;
OUT_R  = IN_R + WALL;
Z_COMP = PCB_Z + PCB_T + PARTS_TOP;          // top of components
Z_BATT = Z_COMP + 0.2;                       // battery bottom
Z_DISP = Z_BATT + BATT[2] + BATT_GAP;        // display bottom
Z_TOP  = Z_DISP + DISP_T + LIP;              // overall height
echo(str("Case height = ", Z_TOP, " mm, diameter = ", 2 * OUT_R, " mm"));

// ---------------- straps
STRAP_W = 20; STRAP_T = 2.6; STRAP_Z = 0.6;
STRAP_LONG = 112; STRAP_SHORT = 78; HOLE_PITCH = 7; HOLE_D = 2.6;

// PCB coordinates (x right, y DOWN, as in KiCad) -> case frame.
// The board is turned 45 deg so the button sits at 2 o'clock, USB-C at 4 o'clock
// and the straps at 12 / 6 o'clock.
module pcb_frame() { rotate([0, 0, 45]) mirror([0, 1, 0]) children(); }

// features in PCB coordinates
SENSOR_XY = [0, 5.5];    SENSOR_WIN = [4.6, 6.6];
LED_XY    = [7.5, 13.2];
USB_X     = 0;           USB_W = 9.6; USB_H = 3.8;  // receptacle opening
USB_Z     = PCB_Z + PCB_T + 1.63;                   // receptacle centre height
BTN_XY    = [20.4, -4];  BTN_Z = PCB_Z + PCB_T + 1.75;
LIS_XY    = [-5.0, -6.4];  U6_XY = [-6.5, 5];

// -------------------------------------------------------------- shapes
module outer_body() {
    hull() {
        cylinder(r = OUT_R, h = Z_TOP - 3);
        translate([0, 0, Z_TOP - 0.01]) cylinder(r = OUT_R - 2.4, h = 0.01);
        translate([0, 0, Z_TOP - 1.2]) cylinder(r = OUT_R - 1.0, h = 0.01);
    }
    // strap roots blend into the body
    for (m = [0, 1]) mirror([0, m, 0]) hull() {
        translate([-STRAP_W / 2 - 1.5, OUT_R - 8, STRAP_Z]) cube([STRAP_W + 3, 2, STRAP_T + 2.4]);
        translate([-STRAP_W / 2, OUT_R + 2, STRAP_Z]) cube([STRAP_W, 2, STRAP_T]);
    }
}

module straps() {
    // 12 o'clock: short strap with peg
    translate([-STRAP_W / 2, OUT_R, STRAP_Z]) difference() {
        hull() {
            cube([STRAP_W, 1, STRAP_T]);
            translate([STRAP_W / 2, STRAP_SHORT - STRAP_W / 2, 0]) cylinder(d = STRAP_W - 2, h = STRAP_T);
        }
        // groove lines for a nicer look
        for (i = [1:6]) translate([2, 6 + i * 9, STRAP_T - 0.4]) cube([STRAP_W - 4, 0.8, 1]);
    }
    // peg (mushroom) near the end of the short strap
    translate([0, OUT_R + STRAP_SHORT - 14, STRAP_Z + STRAP_T - 0.01]) {
        cylinder(d = 2.4, h = 2.6);
        translate([0, 0, 2.2]) cylinder(d1 = 3.6, d2 = 2.4, h = 1.2);
    }
    // 6 o'clock: long strap with holes
    translate([-STRAP_W / 2, -OUT_R, STRAP_Z]) difference() {
        hull() {
            translate([0, -1, 0]) cube([STRAP_W, 1, STRAP_T]);
            translate([STRAP_W / 2, -(STRAP_LONG - STRAP_W / 2), 0]) cylinder(d = STRAP_W - 4, h = STRAP_T);
        }
        for (i = [0:10]) translate([STRAP_W / 2, -(38 + i * HOLE_PITCH), -1]) cylinder(d = HOLE_D, h = 10, $fn = 32);
    }
}

// everything that is hollow inside the case (also used as the mold core)
module cavity(extend_top = 0) {
    pcb_frame() {
        // PCB + components + battery space, flat on the USB side
        translate([0, 0, PCB_Z]) intersection() {
            cylinder(r = IN_R, h = Z_DISP - PCB_Z);
            translate([-50, -50, 0]) cube([100, 50 + PCB_FLAT + CLR, 50]);
        }
        // gap under the board for bottom-side parts, ring ledge holds the PCB
        translate([0, 0, FLOOR]) intersection() {
            cylinder(r = IN_R - 1.4, h = PCB_Z - FLOOR + 0.01);
            translate([-50, -50, 0]) cube([100, 50 + PCB_FLAT - 1.4, 50]);
        }
        // deeper pockets for the taller bottom parts (LIS3DH, 1.8 V LDO)
        for (p = [LIS_XY, U6_XY]) translate([p[0] - 2.4, p[1] - 2.4, FLOOR - 0.45]) cube([4.8, 4.8, 1]);
        // sensor window, charge LED pin-hole
        translate([SENSOR_XY[0] - SENSOR_WIN[0] / 2, SENSOR_XY[1] - SENSOR_WIN[1] / 2, -1])
            cube([SENSOR_WIN[0], SENSOR_WIN[1], FLOOR + 2]);
        translate([LED_XY[0], LED_XY[1], -1]) cylinder(d = 1.2, h = FLOOR + 2, $fn = 24);
        // USB-C opening through the flat wall + overmold recess outside
        translate([USB_X - USB_W / 2, PCB_FLAT - 1, USB_Z - USB_H / 2]) cube([USB_W, 10, USB_H]);
        translate([USB_X - 6.6, PCB_FLAT + CLR + 1.2, USB_Z - 3.5]) cube([13.2, 10, 7.0]);
        // button: thin membrane pocket from the inside (wall left = 0.9 mm)
        translate([BTN_XY[0], BTN_XY[1], BTN_Z]) rotate([0, 90, 0])
            difference() { cylinder(d = 6.0, h = OUT_R - BTN_XY[0] - 0.9 - 0.1); cylinder(d = 2.4, h = 50); }
    }
    // display recess + window through the lip
    translate([0, 0, Z_DISP - 0.01]) cylinder(d = DISP_D, h = DISP_T + 0.01);
    translate([0, 0, Z_DISP]) cylinder(d = VIEW_D, h = LIP + DISP_T + 1 + extend_top);
}

module button_bump() pcb_frame()
    translate([OUT_R - 0.4, BTN_XY[1], BTN_Z]) rotate([0, 90, 0]) {
        cylinder(d = 4.2, h = 1.2);
        translate([0, 0, 1.2]) cylinder(d1 = 4.2, d2 = 3.4, h = 0.4);
    }

module bottom_text() {
    // debossed lettering on the wrist side (reads correctly when the watch is flipped)
    mirror([1, 0, 0]) {
        r = OUT_R - 3.2;
        msg = "SPITALUL VIRTUAL";
        for (i = [0:len(msg) - 1]) {
            a = 90 + (len(msg) / 2 - i - 0.5) * 9.4;
            translate([r * cos(a), r * sin(a), -0.01]) rotate([0, 0, a - 90])
                linear_extrude(0.45) text(msg[i], size = 2.2, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
        }
        msg2 = "made by Stancu Patrick";
        for (i = [0:len(msg2) - 1]) {
            a = 270 - (len(msg2) / 2 - i - 0.5) * 6.4;
            translate([r * cos(a), r * sin(a), -0.01]) rotate([0, 0, a + 90])
                linear_extrude(0.45) text(msg2[i], size = 1.6, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
        }
    }
}

module bezel_ticks() for (i = [0:11])
    rotate([0, 0, i * 30]) translate([0, OUT_R - 1.7, Z_TOP - 0.35])
        cube([i % 3 == 0 ? 1.0 : 0.5, i % 3 == 0 ? 1.4 : 0.9, 1], center = true);

module case() {
    difference() {
        union() { outer_body(); straps(); button_bump(); }
        cavity();
        bottom_text();
        bezel_ticks();
    }
}

module keeper() difference() {   // loose loop that holds the strap tail
    hull() for (x = [-1, 1]) translate([x * (STRAP_W / 2 + 1.6 - 1.5), 0, 0]) cylinder(r = 1.5 + 1.4, h = 6);
    hull() for (x = [-1, 1]) translate([x * (STRAP_W / 2 + 0.4 - 1.5), 0, -1]) cylinder(r = 1.5, h = 8);
}

// -------------------------------------------------------------- mold (3 parts)
M_MARGIN = 8; M_X = 2 * OUT_R + 2 * M_MARGIN; M_Y = STRAP_LONG + STRAP_SHORT + 2 * OUT_R + 2 * M_MARGIN;
M_Y0 = -(OUT_R + STRAP_LONG + M_MARGIN);
M_TOP = Z_TOP + 6;
module mold_block(z0, z1) translate([-M_X / 2, M_Y0, z0]) cube([M_X, M_Y, z1 - z0]);
module keys(d) for (p = [[-M_X / 2 + 4, M_Y0 + 4], [M_X / 2 - 4, M_Y0 + M_Y - 4], [M_X / 2 - 4, M_Y0 + 4]])
    translate([p[0], p[1], -3]) cylinder(d = d, h = 6, $fn = 32);

module mold_bottom() difference() {            // flat plate, forms the wrist side
    union() { mold_block(-6, 0); keys(4); }
    bottom_text_relief();
}
module bottom_text_relief() {}                 // text is formed by the plate (raised letters)
module mold_bottom_with_text() union() { mold_block(-6, 0); keys(4); bottom_text(); }

module mold_top() difference() {               // forms the outside, pour hole + vents
    mold_block(0, M_TOP);
    outer_body(); straps(); button_bump();
    keys(4.4);
    translate([0, 0, Z_TOP - 1]) cylinder(d = VIEW_D + 6.4, h = 20);    // core seat
    translate([0, OUT_R + 30, 0]) cylinder(d = 6, h = 50);              // pour spout (short strap)
    for (y = [-(OUT_R + STRAP_LONG - 4), OUT_R + STRAP_SHORT - 4]) translate([0, y, 0]) cylinder(d = 1.6, h = 50); // vents
}

module mold_core() {                            // hangs from the top opening, forms the inside
    intersection() {
        cavity(extend_top = 0);
        outer_body();               // stays inside the part; floor holes end on the bottom plate
    }
    translate([0, 0, Z_TOP - 1.01]) cylinder(d = VIEW_D, h = 1.02);
    translate([0, 0, Z_TOP - 1]) cylinder(d = VIEW_D + 6, h = 7);        // flange / handle
}

// -------------------------------------------------------------- assembly preview
module pcb_preview() pcb_frame() {
    color("#111") translate([0, 0, PCB_Z]) intersection() {
        cylinder(r = PCB_R, h = PCB_T);
        translate([-50, -50, 0]) cube([100, 50 + PCB_FLAT, 5]);
    }
    color("#ddd") translate([-9, -18.1, PCB_Z + PCB_T]) cube([18, 20, 3.2]);           // ESP32 module
    color("#bbb") translate([-4.47, 18 - 7.35, PCB_Z + PCB_T]) cube([8.94, 7.35, 3.26]); // USB-C
    color("#222") translate([SENSOR_XY[0] - 1.65, SENSOR_XY[1] - 2.8, PCB_Z - 1.55]) cube([3.3, 5.6, 1.55]);
}

if (PART == "case") case();
if (PART == "keeper") keeper();
if (PART == "mold_bottom") mold_bottom_with_text();
if (PART == "mold_top") mold_top();
if (PART == "mold_core") mold_core();
if (PART == "assembly") {
    color("#1a1a1a", 0.92) case();
    pcb_preview();
    color("silver") translate([-BATT[0] / 2, -BATT[1] / 2, Z_BATT]) cube(BATT);
    color("#0b2a4a") translate([0, 0, Z_DISP]) cylinder(d = DISP_D - 0.4, h = DISP_T);
}
