"""After the GND pours are filled, find ground copper that is not connected to the main
ground body and route a short track/via to join it. Repeats until one ground net remains.
Usage: repair_gnd.py in.kicad_pcb out.kicad_pcb"""
import sys, math
import numpy as np
import pcbnew
from pcbnew import ToMM
from shapely.geometry import Polygon, Point, LineString
from shapely.strtree import STRtree
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import router as R
from router import Router, raster, CX, CY, N

def poly_from_outline(o):
    return Polygon([(ToMM(o.CPoint(k).x) - CX, ToMM(o.CPoint(k).y) - CY) for k in range(o.PointCount())])

def gnd_items(b, r):
    items = []   # (geom, layers)
    for p in r.pads:
        if p["net"] == "GND": items.append((p["poly"], tuple(p["layers"])))
    for t in b.GetTracks():
        if t.GetNetname() != "GND": continue
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            items.append((Point(ToMM(c.x) - CX, ToMM(c.y) - CY).buffer(ToMM(t.GetWidth()) / 2), (0, 1)))
        else:
            s, e = t.GetStart(), t.GetEnd()
            ls = LineString([(ToMM(s.x) - CX, ToMM(s.y) - CY), (ToMM(e.x) - CX, ToMM(e.y) - CY)])
            items.append((ls.buffer(ToMM(t.GetWidth()) / 2), (0 if t.GetLayer() == pcbnew.F_Cu else 1,)))
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "GND": continue
        for L, li in ((pcbnew.F_Cu, 0), (pcbnew.B_Cu, 1)):
            if not z.IsOnLayer(L): continue
            fp = z.GetFilledPolysList(L)
            for k in range(fp.OutlineCount()):
                pg = poly_from_outline(fp.Outline(k))
                holes = [poly_from_outline(fp.Hole(k, h)) for h in range(fp.HoleCount(k))]
                pg = Polygon(pg.exterior, [h.exterior for h in holes]).buffer(0)
                items.append((pg, (li,)))
    return items

def clusters(items):
    par = list(range(len(items)))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for L in (0, 1):
        idx = [i for i, (_, ls) in enumerate(items) if L in ls]
        geoms = [items[i][0] for i in idx]
        tree = STRtree(geoms)
        for a, g in zip(idx, geoms):
            for k in tree.query(g):
                bi = idx[k]
                if bi != a and g.intersects(items[bi][0]):
                    par[f(a)] = f(bi)
    groups = {}
    for i in range(len(items)): groups.setdefault(f(i), []).append(i)
    return sorted(groups.values(), key=lambda g: -sum(items[i][0].area for i in g))

def claim_existing(b, r):
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition(); x, y = ToMM(c.x) - CX, ToMM(c.y) - CY
            g = Point(x, y).buffer(ToMM(t.GetWidth()) / 2 + R.CLR + R.HALF, 12)
            for l in (0, 1): r.claim(l, raster(g), net)
            jj, ii = raster(Point(x, y).buffer(R.VIA_DRILL + 0.3)); r.holes[jj, ii] = True
        else:
            s, e = t.GetStart(), t.GetEnd()
            ls = LineString([(ToMM(s.x) - CX, ToMM(s.y) - CY), (ToMM(e.x) - CX, ToMM(e.y) - CY)])
            g = ls.buffer(ToMM(t.GetWidth()) / 2 + R.CLR + R.HALF, 8)
            r.claim(0 if t.GetLayer() == pcbnew.F_Cu else 1, raster(g), net)

def states(items, idxs, allow):
    NN = N * N; st = set()
    for i in idxs:
        g, ls = items[i]
        jj, ii = raster(g.buffer(-0.05) if g.area > 0.05 else g)
        for l in ls:
            ok = allow[l, jj, ii]
            st.update((l * NN + jj[ok] * N + ii[ok]).tolist())
    return st

src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
for it in range(8):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    r = Router(b); r.reset(); claim_existing(b, r)
    items = gnd_items(b, r)
    cl = clusters(items)
    print(f"iteration {it}: {len(cl)} ground islands")
    if len(cl) == 1: break
    allow = r.allowed("GND"); via_ok = r.via_map(allow)
    main = states(items, cl[0], allow)
    for g in cl[1:]:
        s = states(items, g, allow)
        if not s: print("  island with no reachable cell"); continue
        from shapely.ops import nearest_points, unary_union
        isl = unary_union([items[i][0] for i in g])
        mg = unary_union([items[i][0] for i in cl[0]])
        c = nearest_points(isl, mg)[1]
        path = r.astar(allow, via_ok, s, main, (c.x, c.y))
        if path is None: print("  could not join island at", round(c.x, 1), round(c.y, 1)); continue
        r.commit("GND", path, R.SIG_W)
        main |= set(path)
        allow = r.allowed("GND"); via_ok = r.via_map(allow)
    r.write(b)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(dst, b)
print("saved", dst)
