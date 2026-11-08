"""Simple 3D (STEP) models for the parts KiCad 7 has no model for, so the board STEP is complete.
Run directly to (re)build the models and patch the board + library:  python3 models3d.py"""
import os, sys, glob
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D3 = os.path.join(ROOT, "hardware", "kicad", "lib", "3d")
MODELS = {   # footprint name -> model file (KiCad: origin = footprint origin, z = 0 on the board)
    "ESP32-C3-WROOM-02": "ESP32-C3-WROOM-02.step",
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "USB-C_HRO_TYPE-C-31-M-12.step",
    "Maxim_OLGA-14_3.3x5.6mm_P0.8mm": "MAX30102_OLGA-14.step",
    "SW_SPST_EVQP7C": "EVQP7C_side_switch.step",
}

def build():
    import cadquery as cq
    os.makedirs(D3, exist_ok=True)
    def save(asm, name): asm.save(os.path.join(D3, name), "STEP")
    # KiCad footprint y is down, STEP y is up -> y_model = -y_footprint
    a = cq.Assembly()
    a.add(cq.Workplane().box(18, 20, 0.8, centered=(True, True, False)).translate((0, 3.1, 0)), color=cq.Color(0.05, 0.05, 0.08), name="pcb")
    a.add(cq.Workplane().box(16.6, 13.4, 2.4, centered=(True, True, False)).translate((0, 0.05, 0.8)), color=cq.Color(0.78, 0.78, 0.8), name="shield")
    save(a, MODELS["ESP32-C3-WROOM-02"])

    a = cq.Assembly()
    shell = (cq.Workplane("XZ").center(0, 1.63).rect(8.94, 3.26).extrude(7.2)
             .edges("|Y").fillet(1.4).translate((0, 3.03, 0)))
    hole = (cq.Workplane("XZ").center(0, 1.63).rect(8.34, 2.56).extrude(6.6)
            .edges("|Y").fillet(1.1).translate((0, 2.33, 0)))
    a.add(shell.cut(hole), color=cq.Color(0.8, 0.8, 0.82), name="shell")
    a.add(cq.Workplane("XZ").center(0, 1.63).rect(6.6, 0.7).extrude(5.5).translate((0, 1.9, 0)), color=cq.Color(0.1, 0.1, 0.1), name="tongue")
    save(a, MODELS["USB_C_Receptacle_HRO_TYPE-C-31-M-12"])

    a = cq.Assembly()
    a.add(cq.Workplane().box(3.3, 5.6, 1.45, centered=(True, True, False)), color=cq.Color(0.12, 0.12, 0.12), name="body")
    for y in (-1.3, 1.3):
        a.add(cq.Workplane().box(1.6, 1.6, 0.1, centered=(True, True, False)).translate((0, y, 1.45)), color=cq.Color(0.6, 0.1, 0.1), name=f"window{y}")
    save(a, MODELS["Maxim_OLGA-14_3.3x5.6mm_P0.8mm"])

    a = cq.Assembly()
    a.add(cq.Workplane().box(3.5, 2.9, 1.7, centered=(True, True, False)), color=cq.Color(0.85, 0.85, 0.87), name="body")
    a.add(cq.Workplane().box(1.2, 1.0, 0.8, centered=(True, True, False)).translate((0, -1.9, 0.45)), color=cq.Color(0.15, 0.15, 0.15), name="actuator")
    save(a, MODELS["SW_SPST_EVQP7C"])

def apply(fp):
    """point a footprint at our model (if we have one)"""
    import pcbnew
    name = fp.GetFPID().GetLibItemName().wx_str() if hasattr(fp.GetFPID().GetLibItemName(), "wx_str") else str(fp.GetFPID().GetLibItemName())
    if name not in MODELS: return
    ms = fp.Models()
    ms.clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/lib/3d/" + MODELS[name]
    ms.push_back(m)

if __name__ == "__main__":
    build()
    import pcbnew
    lib = os.path.join(ROOT, "hardware", "kicad", "lib", "SpitalulVirtual.pretty")
    for name in MODELS:
        fp = pcbnew.FootprintLoad(lib, name); apply(fp); pcbnew.FootprintSave(lib, fp)
    pcb = os.path.join(ROOT, "hardware", "kicad", "spitalul_virtual_band.kicad_pcb")
    b = pcbnew.LoadBoard(pcb)
    for fp in b.GetFootprints(): apply(fp)
    pcbnew.SaveBoard(pcb, b)
    print("models:", sorted(os.listdir(D3)))
