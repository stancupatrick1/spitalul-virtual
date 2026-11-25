// =====================================================================
//  SPITALUL VIRTUAL WATCH - PLA fit test (rigid, 2 parts, no straps)
//  Uses the exact geometry of case.scad, split at the bottom of the display
//  so a rigid PCB + battery drop into the tray and the display goes into
//  the bezel from below.
//
//  openscad -D 'TEST="tray"'  -o watch_pla_tray.stl  pla_test.scad
//  openscad -D 'TEST="bezel"' -o watch_pla_bezel.stl pla_test.scad
//
//  Complete test watch (lugs for a standard 20 mm strap + bezel that locates on the tray):
//  openscad -D 'TEST="tray_complete"'  -o watch_pla_complete_case.stl    pla_test.scad
//  openscad -D 'TEST="bezel_complete"' -o watch_pla_complete_bezel.stl   pla_test.scad
//  openscad -D 'TEST="display"'        -o watch_pla_complete_display.stl pla_test.scad
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
// ---------------------------------------------------------------- complete test watch
// Rigid PLA straps would snap, so the "complete" version gets lugs for any standard
// 20 mm watch strap with spring bars. The bezel locates on a lip of the tray.
LUG_GAP = 20.4;            // between the lugs (20 mm strap)
LUG_T = 2.4;               // lug thickness
LUG_Y = OUT_R + 2.8;       // spring-bar centre (room for the strap round the bar)
LUG_Z = 3.6;               // spring-bar height
LUG_H = 7.0;               // lug height
BAR_D = 1.2;               // spring-bar tip hole (drill 1.2 mm if it closes up)
LIP_W = 1.0; LIP_H = 1.0; LIP_CLR = 0.2;

module lugs() for (my = [0, 1]) mirror([0, my, 0]) for (mx = [0, 1]) mirror([mx, 0, 0])
    difference() {
        hull() {
            translate([LUG_GAP / 2, OUT_R - 6, 0]) cube([LUG_T, 1, LUG_H]);
            translate([LUG_GAP / 2, LUG_Y, 0]) cube([LUG_T, 0.01, LUG_H]);
            translate([LUG_GAP / 2, LUG_Y + 0.4, 0]) rotate([0, 90, 0]) translate([-LUG_Z, 0, 0]) cylinder(r = 2.6, h = LUG_T);
            translate([LUG_GAP / 2, LUG_Y + 0.4, 0]) cube([LUG_T, 2.6, 0.01]);
        }
        translate([LUG_GAP / 2 - 1, LUG_Y, LUG_Z]) rotate([0, 90, 0]) cylinder(d = BAR_D, h = LUG_T + 2, $fn = 24);
    }

module tray_complete() difference() {
    union() {
        intersection() { body(); translate([-100, -100, -1]) cube([200, 200, Z_DISP + 1]); }
        lugs();
        translate([0, 0, Z_DISP - 0.5]) cylinder(r = IN_R + LIP_W, h = LIP_H + 0.5);
    }
    translate([0, 0, Z_DISP - 0.3]) cylinder(r = IN_R, h = 5);
    cavity(); bottom_text(); button_hole();
}
module bezel_complete() difference() {
    bezel();
    translate([0, 0, -0.01]) difference() {
        cylinder(r = IN_R + LIP_W + LIP_CLR, h = LIP_H + 0.2);
        cylinder(r = IN_R - LIP_CLR, h = 5);
    }
}
// stand-in for the round display: print in black, the face text in a second colour
module display_dummy() {
    cylinder(d = DISP_D - 0.6, h = DISP_T - 0.4);
    translate([0, 0, DISP_T - 0.41]) linear_extrude(0.4) {
        translate([0, 5]) text("SPITALUL VIRTUAL", size = 1.9, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
        translate([0, -1]) text("10:09", size = 6, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
        translate([0, -7.5]) text("72 bpm  98%", size = 1.8, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
        difference() { circle(d = VIEW_D - 1.0); circle(d = VIEW_D - 2.4); }
    }
}

if (TEST == "tray") tray();
if (TEST == "tray_complete") tray_complete();
if (TEST == "bezel_complete") bezel_complete();
if (TEST == "display") display_dummy();
if (TEST == "bezel") bezel();
