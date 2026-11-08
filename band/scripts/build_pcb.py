"""Generate the KiCad PCB (placement, outline, artwork, zones). Routing is done by
router.py afterwards and zones are refilled in finish_pcb.py."""
import math, os, shutil, sys
import pcbnew
from pcbnew import FromMM, VECTOR2I
sys.path.insert(0, os.path.dirname(__file__))
from design import *
import models3d

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KDIR = os.path.join(ROOT, "hardware", "kicad")
LIBDIR = os.path.join(KDIR, "lib", "SpitalulVirtual.pretty")
SYSFP = "/usr/share/kicad/footprints"
os.makedirs(LIBDIR, exist_ok=True)

CX, CY = CENTER
def V(x, y): return VECTOR2I(FromMM(CX + x), FromMM(CY + y))
def ang(d): return pcbnew.EDA_ANGLE(d, pcbnew.DEGREES_T)

# ------------------------------------------------------------ custom footprints
LABEL_AT = {"M+": (14.8, 7.8)}

def pads_fp(name, pads, size, desc):
    """wire pads at absolute board positions (footprint placed at the board centre)"""
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("SpitalulVirtual", name))
    fp.SetDescription(desc)
    fp.SetAttributes(pcbnew.FP_SMD | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for i, ((x, y), label) in enumerate(pads):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i + 1))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT); pad.SetRoundRectRadiusRatio(0.3)
        pad.SetLayerSet(pad.SMDMask())
        pad.SetSize(VECTOR2I(FromMM(size[0]), FromMM(size[1])))
        pp = VECTOR2I(FromMM(x), FromMM(y)); pad.SetPos0(pp); pad.SetPosition(pp)
        fp.Add(pad)
        t = pcbnew.FP_TEXT(fp, pcbnew.FP_TEXT.TEXT_is_DIVERS)
        t.SetText(label); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8))); t.SetTextThickness(FromMM(0.15))
        lx, ly = LABEL_AT.get(label, (x - size[0] / 2 - 1.1, y))
        tp = VECTOR2I(FromMM(lx), FromMM(ly)); t.SetPos0(tp); t.SetPosition(tp)
        fp.Add(t)
    fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetLayer(pcbnew.F_Fab)
    pcbnew.FootprintSave(LIBDIR, fp)

pads_fp("BatteryPads", BATT_PADS, (2.0, 1.6), "Li-Po battery pads")
pads_fp("MotorPads", MOTOR_PADS, (2.0, 1.6), "Vibration motor pads")

# ------------------------------------------------------------ board
board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(FromMM(0.2)); nc.SetClearance(FromMM(0.127))
nc.SetViaDiameter(FromMM(0.6)); nc.SetViaDrill(FromMM(0.3))
ds.m_TrackMinWidth = FromMM(0.15); ds.m_ViasMinSize = FromMM(0.5); ds.m_MinThroughDrill = FromMM(0.3)
ds.m_CopperEdgeClearance = FromMM(0.3); ds.m_HoleToHoleMin = FromMM(0.25)
ds.SetBoardThickness(FromMM(1.0))
ds.m_MinSilkTextHeight = FromMM(0.8); ds.m_MinSilkTextThickness = FromMM(0.15)
tb = board.GetTitleBlock()
tb.SetTitle(TITLE); tb.SetRevision("1.0"); tb.SetDate("2026-10-27")
tb.SetCompany("made by Stancu Patrick")

# outline: rounded rectangle (lines + arcs)
r = CORNER_R
segs = [((-HL + r, -HW), (HL - r, -HW)), ((HL, -HW + r), (HL, HW - r)),
        ((HL - r, HW), (-HL + r, HW)), ((-HL, HW - r), (-HL, -HW + r))]
for a_, b_ in segs:
    ln = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    ln.SetStart(V(*a_)); ln.SetEnd(V(*b_)); ln.SetLayer(pcbnew.Edge_Cuts); ln.SetWidth(FromMM(0.1)); board.Add(ln)
k = r * (1 - math.sqrt(0.5))
for (sx, sy) in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
    arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
    # start, mid, end going clockwise around the board
    if (sx, sy) == (1, -1):   pts = ((HL - r, -HW), (HL - k, -HW + k), (HL, -HW + r))
    elif (sx, sy) == (1, 1):  pts = ((HL, HW - r), (HL - k, HW - k), (HL - r, HW))
    elif (sx, sy) == (-1, 1): pts = ((-HL + r, HW), (-HL + k, HW - k), (-HL, HW - r))
    else:                     pts = ((-HL, -HW + r), (-HL + k, -HW + k), (-HL + r, -HW))
    arc.SetArcGeometry(V(*pts[0]), V(*pts[1]), V(*pts[2]))
    arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(FromMM(0.1)); board.Add(arc)

# nets
netmap = {}
for n in nets():
    ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); netmap[n] = ni

# footprints
for p in P:
    lib, name = p["fp"].split(":")
    path = LIBDIR if lib == "SpitalulVirtual" else os.path.join(SYSFP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    # keep a copy in the project library so the repo is self-contained
    if lib != "SpitalulVirtual":
        pcbnew.FootprintSave(LIBDIR, fp)
    if name == "ESP32-C3-WROOM-02":
        for pd in fp.Pads():
            if pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                pd.SetDrillSize(VECTOR2I(FromMM(0.3), FromMM(0.3)))
        pcbnew.FootprintSave(LIBDIR, fp)
    fp.SetFPID(pcbnew.LIB_ID("SpitalulVirtual", name))
    if name in models3d.MODELS:          # our own simple STEP models for parts KiCad has none for
        models3d.apply(fp); pcbnew.FootprintSave(LIBDIR, fp)
    fp.SetReference(p["ref"]); fp.SetValue(p["value"])
    if p["lcsc"]:
        fp.SetProperty("LCSC", p["lcsc"])
    fp.SetPosition(V(p["x"], p["y"]))
    fp.SetOrientationDegrees(p["rot"])
    board.Add(fp)
    if p["side"] == "B":
        fp.Flip(fp.GetPosition(), False)
    for pad in fp.Pads():
        n = p["pins"].get(pad.GetNumber())
        if n: pad.SetNet(netmap[n])
    # clean silkscreen: references on the fab layer only
    fab = pcbnew.B_Fab if p["side"] == "B" else pcbnew.F_Fab
    fp.Reference().SetLayer(fab); fp.Value().SetLayer(fab)
    fp.Reference().SetTextSize(VECTOR2I(FromMM(0.5), FromMM(0.5)))
    fp.Reference().SetTextThickness(FromMM(0.08))

def circle_poly(r, n=96, flat=None):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = r * math.cos(t), r * math.sin(t)
        if flat is not None and y > flat: y = flat
        pts.append((x, y))
    return pts

# ------------------------------------------------------------ artwork
def text(s, x, y, size, layer, angle=0, thick=None, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(thick or size * 0.15))
    t.SetBold(bold)
    t.SetPosition(V(x, y)); t.SetTextAngle(ang(angle))
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu, pcbnew.B_Mask):
        t.SetMirrored(True)
    board.Add(t)

def poly(points, layer, width=0.2):
    for (a, b) in zip(points[:-1], points[1:]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(FromMM(width))
        board.Add(s)

def circle(x, y, r, layer, width=0.2):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(V(x, y)); s.SetEnd(V(x + r, y)); s.SetLayer(layer); s.SetWidth(FromMM(width))
    board.Add(s)

def arc_text(s, r, center_deg, size, layer, top=True, spacing=0.78, bottom_view=False):
    """Lay characters along a circle. top=True reads clockwise over the top,
    top=False reads left-to-right along the bottom. bottom_view mirrors for the B side."""
    step = math.degrees(size * spacing / r)
    n = len(s)
    for i, ch in enumerate(s):
        if ch == " ": continue
        if top:
            a = center_deg - (i - (n - 1) / 2) * step     # math angle, y up
            rot = a - 90
        else:
            a = center_deg + (i - (n - 1) / 2) * step
            rot = a + 90
        x = r * math.cos(math.radians(a)); y = -r * math.sin(math.radians(a))
        if bottom_view:  # seen from below everything is mirrored left/right
            x = -x; rot = -rot
        text(ch, x, y, size, layer, angle=rot, thick=size * 0.18, bold=True)

# --- Bottom (skin side): seen from below, so x is mirrored (bx = -x)
BS = pcbnew.B_SilkS
def bt(s, x, y, size, bold=False, thick=None):   # bottom text at "as seen from below" coordinates
    text(s, -x, y, size, BS, thick=thick or size * 0.18, bold=bold)
bt("SPITALUL VIRTUAL", 0.0, -8.3, 2.0, bold=True)
bt("made by Stancu Patrick", 0.0, 8.6, 1.2, bold=True)
bt("HR - SpO2 - TEMP - STEPS", 0.0, -10.6, 0.8, thick=0.15)
bt("v1.0  2026", 0.0, 10.6, 0.8, thick=0.15)
loop = outline_pts(0.7) + [outline_pts(0.7)[0]]
poly([(x, y) for x, y in loop], BS, 0.25)
# heartbeat line across the board, between the title and the sensors
ecg = [(-17.0, -6.0), (-6.0, -6.0), (-5.2, -6.6), (-4.4, -6.0), (-2.6, -6.0), (-2.0, -5.5),
       (-1.0, -7.2), (0.0, -5.4), (0.6, -6.0), (2.4, -6.0), (3.4, -6.7), (4.4, -6.0), (17.0, -6.0)]
poly([(-x, y) for x, y in ecg], BS, 0.25)
# medical cross next to the title
cx0, cy0, a, b2 = 15.6, -8.3, 1.0, 0.33
cross = [(-b2, -a), (b2, -a), (b2, -b2), (a, -b2), (a, b2), (b2, b2), (b2, a), (-b2, a), (-b2, b2), (-a, b2), (-a, -b2), (-b2, -b2), (-b2, -a)]
poly([(-(cx0 + x), cy0 + y) for x, y in cross], BS, 0.2)
poly([(-(-cx0 + x), cy0 + y) for x, y in cross], BS, 0.2)
# sensor labels
bt("TEMP", 13.1, 0.0, 0.8, thick=0.15)


# --- Top side (under the battery)
FS = pcbnew.F_SilkS
text("BTN", 10.4, 7.4, 0.8, FS, thick=0.15)

# ------------------------------------------------------------ zones
def zone(pts, layer, net=None, keepout=False, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts: ol.Append(FromMM(CX + x), FromMM(CY + y))
    if keepout:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET(pcbnew.F_Cu).AddLayer(pcbnew.B_Cu))
    else:
        z.SetNet(netmap[net]); z.SetAssignedPriority(prio)
        z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FromMM(0.25)); z.SetThermalReliefSpokeWidth(FromMM(0.3))
    board.Add(z)
    return z

big = outline_pts(-1.0)
zone(big, pcbnew.F_Cu, GND)
zone(big, pcbnew.B_Cu, GND)
zone(ANTENNA_KEEPOUT, pcbnew.F_Cu, keepout=True)   # antenna: no copper on either layer

out = os.path.join(KDIR, PROJECT + ".kicad_pcb")
pcbnew.SaveBoard(out, board)
print("saved", out)
