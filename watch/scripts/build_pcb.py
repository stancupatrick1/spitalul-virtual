"""Generate the KiCad PCB (placement, outline, artwork, zones). Routing is done by
Freerouting afterwards (see route.sh) and zones are refilled in finish_pcb.py."""
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
PAD_R = 19.4  # radius of the edge pads

def arc_pads_fp(name, angles, size, labels, desc):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("SpitalulVirtual", name))
    fp.SetDescription(desc)
    fp.SetAttributes(pcbnew.FP_SMD | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for i, a in enumerate(angles):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i + 1))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
        pad.SetRoundRectRadiusRatio(0.3)
        pad.SetLayerSet(pad.SMDMask())
        pad.SetSize(VECTOR2I(FromMM(size[0]), FromMM(size[1])))
        r = math.radians(a)
        pp = VECTOR2I(FromMM(PAD_R * math.cos(r)), FromMM(PAD_R * math.sin(r))); pad.SetPos0(pp); pad.SetPosition(pp)
        pad.SetOrientation(ang(-a))  # long side radial
        fp.Add(pad)
        # silkscreen label just inside the pad
        t = pcbnew.FP_TEXT(fp, pcbnew.FP_TEXT.TEXT_is_DIVERS) if hasattr(pcbnew, "FP_TEXT") else None
        rr = PAD_R - size[0] / 2 - 0.25 - 0.62 * len(labels[i]) * 0.5
        t.SetText(labels[i]); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8))); t.SetTextThickness(FromMM(0.15))
        tp = VECTOR2I(FromMM(rr * math.cos(r)), FromMM(rr * math.sin(r))); t.SetPos0(tp); t.SetPosition(tp)
        ta = -a
        if 90 < a % 360 < 270: ta = 180 - a
        t.SetTextAngle(ang(ta))
        fp.Add(t)
    fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetLayer(pcbnew.F_Fab)
    pcbnew.FootprintSave(LIBDIR, fp)

def spread(center, n, pitch_mm):
    step = math.degrees(pitch_mm / PAD_R)
    return [center + (i - (n - 1) / 2) * step for i in range(n)]

arc_pads_fp("DisplayPads_Arc", spread(180, 8, 1.55), (2.0, 0.9),
            ["GND", "VCC", "SCL", "SDA", "RES", "DC", "CS", "BLK"],
            "8 wire pads for a GC9A01 1.28in round display")
arc_pads_fp("BatteryPads_Arc", spread(148, 2, 3.2), (2.4, 2.0), ["B+", "B-"], "Li-Po battery pads")
arc_pads_fp("MotorPads_Arc", spread(20, 2, 2.6), (2.0, 1.6), ["M+", "M-"], "Vibration motor pads")

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
tb.SetTitle("Spitalul Virtual Smartwatch"); tb.SetRevision("1.0"); tb.SetDate("2026-10-26")
tb.SetCompany("made by Stancu Patrick")

# outline: circle with a flat for USB-C
hx = math.sqrt(BOARD_R**2 - FLAT_Y**2)
arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
arc.SetArcGeometry(V(hx, FLAT_Y), V(0, -BOARD_R), V(-hx, FLAT_Y))
arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(FromMM(0.1)); board.Add(arc)
ln = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
ln.SetStart(V(-hx, FLAT_Y)); ln.SetEnd(V(hx, FLAT_Y))
ln.SetLayer(pcbnew.Edge_Cuts); ln.SetWidth(FromMM(0.1)); board.Add(ln)

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

# --- Bottom (skin side): the side people see when they flip the watch
BS = pcbnew.B_SilkS
arc_text("SPITALUL VIRTUAL", 17.2, 90, 2.0, BS, top=True, bottom_view=True)
arc_text("made by Stancu Patrick", 17.15, 270, 1.0, BS, top=False, spacing=0.8, bottom_view=True)
poly(circle_poly(20.25, 180, flat=FLAT_Y - 0.6) + [circle_poly(20.25, 180, flat=FLAT_Y - 0.6)[0]], BS, 0.25)
_r = 15.2; _a0 = math.asin(6.5 / _r)
poly([(_r * math.cos(t), _r * math.sin(t)) for t in [math.pi - _a0 + i * (math.pi + 2 * _a0) / 100 for i in range(101)]], BS, 0.12)
# sensor window ring + "pulse" line through the middle
ecg = [(-13.5, -3.2), (-7.5, -3.2), (-6.4, -4.6), (-5.4, -3.2), (-4.2, -3.2), (-3.4, -1.6),
       (-2.4, -9.6), (-1.2, 0.4), (-0.4, -3.2), (1.6, -3.2), (2.8, -5.0), (4.2, -3.2), (13.5, -3.2)]
poly([(-x, y) for x, y in ecg], BS, 0.3)
# medical cross
cx0, cy0, a, b = 0, -10.2, 1.1, 0.35
cross = [(-b, -a), (b, -a), (b, -b), (a, -b), (a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b), (-a, -b), (-b, -b), (-b, -a)]
poly([(cx0 + x, cy0 + y) for x, y in cross], BS, 0.2)
text("HR - SpO2 - STEPS", 0, -12.6, 0.85, BS, thick=0.15)
text("v1.0  2026", 0, -14.3, 0.8, BS, thick=0.15)

# --- Top side (under the battery): smaller branding + labels
FS = pcbnew.F_SilkS
text("SPITALUL VIRTUAL", 0, 4.0, 1.0, FS, thick=0.17, bold=True)
text("made by Stancu Patrick", 0, 5.7, 0.8, FS, thick=0.15)
text("JLCJLCJLCJLC", -9.6, 15.5, 0.8, FS, thick=0.15)
text("BTN", 17.4, 0.4, 0.8, FS, thick=0.15)
text("USB-C", 7.6, 16.4, 0.8, FS, thick=0.15)

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

zone(circle_poly(BOARD_R + 1, flat=FLAT_Y + 1), pcbnew.F_Cu, GND)
zone(circle_poly(BOARD_R + 1, flat=FLAT_Y + 1), pcbnew.B_Cu, GND)
# antenna keep-out (module antenna sits at the top edge)
zone([(-14.3, -22), (14.3, -22), (14.3, -11.85), (-14.3, -11.85)], pcbnew.F_Cu, keepout=True)

out = os.path.join(KDIR, PROJECT + ".kicad_pcb")
pcbnew.SaveBoard(out, board)
print("saved", out)
