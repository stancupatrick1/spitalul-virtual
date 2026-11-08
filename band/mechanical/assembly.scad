// Spitalul Virtual BAND - full preview (band + real PCB model + battery + motor + cap)
// EXPLODE = 0 assembled, e.g. 10 for an exploded view; CUT = true cuts the band open
include <band.scad>
PART = "none";        // after the include so band.scad draws nothing by itself
EXPLODE = 0;
CUT = false;

module pcb_model() pcb_frame() translate([-100, 100, 0]) import("stl/pcb_assembled.stl");

difference() {
    color("#34373c") band();
    if (CUT) translate([-60, 0, -1]) cube([120, 200, 40]);
}
translate([0, 0, PCB_Z - EXPLODE * 0.6]) pcb_model();
pcb_frame() {
    color("#b8bcc4") translate([BATT_X - BATT[0] / 2, -BATT[1] / 2, Z_BATT + EXPLODE]) cube(BATT);
    color("#c9a227") translate([MOTOR_X, 0, PCB_Z + PCB_T + 3.3 + EXPLODE]) cylinder(d = MOTOR_D - 0.2, h = MOTOR_T - 0.2);
}
color("#a9c4dc", 0.45) translate([0, 0, Z_IN + EXPLODE * 2]) cap();
