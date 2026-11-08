// Spitalul Virtual - full watch preview (case + real PCB model + battery + display)
// EXPLODE = 0 for the assembled watch, e.g. 12 for an exploded view
include <case.scad>
PART = "none";      // after the include so case.scad draws nothing by itself
EXPLODE = 0;
CUT = false;          // true = cut away half of the case to see inside

module pcb_model() rotate([0, 0, 45]) translate([-100, 100, 0]) import("stl/pcb_assembled.stl");

difference() {
    color("#34373c") case();
    if (CUT) translate([0, -150, -1]) cube([100, 300, 40]);
}
color("#2b2b2b") translate([0, 0, PCB_Z - EXPLODE * 0.5]) pcb_model();
color("#b8bcc4") translate([-BATT[0] / 2, -BATT[1] / 2, Z_BATT + EXPLODE]) cube(BATT);
translate([0, 0, Z_DISP + EXPLODE * 2]) {
    color("#0d0d12") cylinder(d = DISP_D - 0.4, h = DISP_T - 0.3);
    face_z = DISP_T - 0.3;
    color("#e8283c") translate([0, 4.5, face_z]) linear_extrude(0.06)
        text("SPITALUL VIRTUAL", size = 1.7, font = "DejaVu Sans:style=Bold", halign = "center");
    color("white") translate([0, -3.5, face_z]) linear_extrude(0.06)
        text("10:09", size = 6, font = "DejaVu Sans:style=Bold", halign = "center");
    color("#ffb428") translate([0, -8.5, face_z]) linear_extrude(0.06)
        text("72 bpm   98%   5230", size = 1.5, font = "DejaVu Sans", halign = "center");
    color("#28dc78") translate([0, 0, face_z]) linear_extrude(0.06) difference() {
        circle(d = VIEW_D - 0.8);
        circle(d = VIEW_D - 2.2);
        polygon([[0, 0], [0, 30], [-30, 30], [-30, -30], [-12, -30]]);
    }
}
