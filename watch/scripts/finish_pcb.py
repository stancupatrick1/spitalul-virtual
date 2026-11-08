"""Refill copper pours, apply final rules and save. Usage: finish_pcb.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
from pcbnew import FromMM
b = pcbnew.LoadBoard(sys.argv[1])
ds = b.GetDesignSettings()
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(FromMM(0.127)); nc.SetTrackWidth(FromMM(0.2))
ds.m_MinClearance = FromMM(0.127)
for z in b.Zones():
    if not z.GetIsRuleArea():
        z.SetLocalClearance(FromMM(0.2))
        z.SetMinThickness(FromMM(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[2], b)
print("saved", sys.argv[2])

# 1.0 mm board, black solder mask, white silk, ENIG: written as a stackup so KiCad's 3D view,
# STEP export and fab notes all agree
STACKUP = '''  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 0.91) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
'''
t = open(sys.argv[2]).read()
if "(stackup" not in t:
    t = t.replace("  (setup\n", STACKUP, 1)
    open(sys.argv[2], "w").write(t)
