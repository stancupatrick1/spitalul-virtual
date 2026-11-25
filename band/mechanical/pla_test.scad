// =====================================================================
//  SPITALUL VIRTUAL BAND - PLA fit test (rigid, 2 parts, no straps)
//  Uses the exact geometry of band.scad, split at the top of the electronics
//  space so a rigid PCB + battery can drop in from above.
//
//  openscad -D 'TEST="tray"'  -o band_pla_tray.stl  pla_test.scad
//  openscad -D 'TEST="frame"' -o band_pla_frame.stl pla_test.scad
//  openscad -D 'TEST="cap"'   -o band_pla_cap.stl   pla_test.scad
//
//  Complete test band (lugs for a standard 20 mm strap; use with "frame" and "cap"):
//  openscad -D 'TEST="tray_complete"'  -o band_pla_complete_case.stl  pla_test.scad
//  The rim at the split is only ~1.4 mm wide, too thin for a locating lip: glue or tape the frame.
//
//  tray  : floor + walls, sensor windows, USB-C opening, button hole
//  frame : top part with the window; the cap goes in from below
//  cap   : the window cap with extra clearance for rigid PLA
// =====================================================================
include <band.scad>
PART = "none";
TEST = "tray";
CLR = 0.35;        // 0.2 in the silicone design; FDM holes come out smaller
BTN_HOLE = 3.0;    // the 0.9 mm membrane does not flex in PLA -> through hole

// pod without the strap roots (they start 0.5 mm above the bed and would print in the air)
module pod_shell() hull() {
    rr(OUT_L, OUT_W, OUT_RC, Z_TOP - 2.2);
    translate([0, 0, Z_TOP - 1.0]) rr(OUT_L - 1.6, OUT_W - 1.6, OUT_RC - 0.8, 0.01);
    translate([0, 0, Z_TOP - 0.01]) rr(OUT_L - 3.4, OUT_W - 3.4, OUT_RC - 1.7, 0.01);
    rr(OUT_L - 0.8, OUT_W - 0.8, OUT_RC - 0.4, 0.01);
}
module pod() union() { pod_shell(); button_bump(); }
module button_hole() pcb_frame()
    translate([BTN_XY[0], BTN_XY[1], BTN_Z]) rotate([-90, 0, 0]) cylinder(d = BTN_HOLE, h = 20, $fn = 32);

module tray() difference() {
    intersection() { pod(); translate([-100, -100, -1]) cube([200, 200, Z_IN + 1]); }
    cavity(); bottom_text(); button_hole();
}
// printed upside-up with the flat split face on the bed
module frame() translate([0, 0, -Z_IN]) difference() {
    intersection() { pod(); translate([-100, -100, Z_IN]) cube([200, 200, 50]); }
    cavity(); top_ring();
}
module cap_pla() {
    rr(CAP[0] - 0.5, CAP[1] - 0.5, OPEN_RC + 1.35, CAP_T);
    translate([0, 0, CAP_T - 0.01]) rr(OPEN[0] - 0.5, OPEN[1] - 0.5, OPEN_RC - 0.25, LIP);
}
// ---------------------------------------------------------------- complete test band
// Rigid PLA straps would snap, so the "complete" version gets lugs for a standard
// 20 mm watch strap with spring bars (same strap as the test watch). The strap is
// moved 2 mm further from the button than in the silicone band so the lug clears it.

LUG_X = -6;                // strap centre line
LUG_GAP = 20.4;            // between the lugs (20 mm strap)
LUG_T = 2.4;
LUG_Y = OUT_W / 2 + 2.8;   // spring-bar centre
LUG_Z = 3.6; LUG_H = 7.0; BAR_D = 1.2;

module lugs() for (my = [0, 1]) mirror([0, my, 0]) translate([LUG_X, 0, 0]) for (mx = [0, 1]) mirror([mx, 0, 0])
    difference() {
        hull() {
            translate([LUG_GAP / 2, OUT_W / 2 - 6, 0]) cube([LUG_T, 1, LUG_H]);
            translate([LUG_GAP / 2, LUG_Y, 0]) cube([LUG_T, 0.01, LUG_H]);
            translate([LUG_GAP / 2, LUG_Y + 0.4, 0]) rotate([0, 90, 0]) translate([-LUG_Z, 0, 0]) cylinder(r = 2.6, h = LUG_T);
            translate([LUG_GAP / 2, LUG_Y + 0.4, 0]) cube([LUG_T, 2.6, 0.01]);
        }
        translate([LUG_GAP / 2 - 1, LUG_Y, LUG_Z]) rotate([0, 90, 0]) cylinder(d = BAR_D, h = LUG_T + 2, $fn = 24);
    }

module tray_complete() difference() {
    union() {
        intersection() { pod(); translate([-100, -100, -1]) cube([200, 200, Z_IN + 1]); }
        lugs();
    }
    cavity(); bottom_text(); button_hole();
}

if (TEST == "tray") tray();
if (TEST == "tray_complete") tray_complete();
if (TEST == "frame") frame();
if (TEST == "cap") cap_pla();
