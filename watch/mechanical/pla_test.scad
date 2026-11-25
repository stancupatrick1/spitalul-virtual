// =====================================================================
//  SPITALUL VIRTUAL WATCH - PLA fit test (rigid, 2 parts, no straps)
//  Uses the exact geometry of case.scad, split at the bottom of the display
//  so a rigid PCB + battery drop into the tray and the display goes into
//  the bezel from below.
//
//  openscad -D 'TEST="tray"'  -o watch_pla_tray.stl  pla_test.scad
//  openscad -D 'TEST="bezel"' -o watch_pla_bezel.stl pla_test.scad
// =====================================================================
include <case.scad>
PART = "none";
TEST = "tray";
CLR = 0.35;        // 0.2 in the silicone design; FDM holes come out smaller
BTN_HOLE = 3.0;    // the 0.9 mm membrane does not flex in PLA -> through hole

// body without the strap roots (they start 0.6 mm above the bed and would print in the air)
module body_shell() hull() {
    cylinder(r = OUT_R, h = Z_TOP - 3);
    translate([0, 0, Z_TOP - 0.01]) cylinder(r = OUT_R - 2.4, h = 0.01);
    translate([0, 0, Z_TOP - 1.2]) cylinder(r = OUT_R - 1.0, h = 0.01);
}
module body() union() { body_shell(); button_bump(); }
module button_hole() pcb_frame()
    translate([BTN_XY[0], BTN_XY[1], BTN_Z]) rotate([0, 90, 0]) cylinder(d = BTN_HOLE, h = 20, $fn = 32);

module tray() difference() {
    intersection() { body(); translate([-100, -100, -1]) cube([200, 200, Z_DISP + 1]); }
    cavity(); bottom_text(); button_hole();
}
module bezel() translate([0, 0, -Z_DISP]) difference() {
    intersection() { body(); translate([-100, -100, Z_DISP]) cube([200, 200, 50]); }
    cavity(); bezel_ticks();
}
if (TEST == "tray") tray();
if (TEST == "bezel") bezel();
