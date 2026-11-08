"""
Small 2-layer grid autorouter for the Spitalul Virtual boards.

- 0.1 mm grid, 8-direction moves, through vias
- obstacles = other nets' copper inflated by (clearance + half track width)
- multi-pin nets are routed as a growing tree (nearest pin first)
- nets that fail are moved to the front and everything is re-routed (up to N passes)
Usage: python3 router.py in.kicad_pcb out.kicad_pcb
"""
import heapq, math, sys, time
import numpy as np
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I
from shapely.geometry import Polygon, Point, LineString, box
from shapely import contains_xy
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import design
from design import CENTER, BOARD_R

RES = 0.1                    # grid (mm)
CLR = 0.15                   # clearance used while routing (DRC rule is 0.127 = JLC 5 mil; extra covers grid error)
HALF = 0.10                  # signal track half width used for obstacle inflation
SIG_W, PWR_W = 0.2, 0.3
VIA_D, VIA_DRILL = 0.6, 0.3
POWER = {"VBUS", "VBAT", "+3V3", "GND"}
EDGE_CLR = 0.35
VIA_COST, TURN_COST = float(__import__("os").environ.get("VIA_COST", 22.0)), 0.25

CX, CY = CENTER
N = int(round(2 * (BOARD_R + 0.6) / RES)) + 1
X0 = -(BOARD_R + 0.6)
xs = X0 + np.arange(N) * RES
GX, GY = np.meshgrid(xs, xs)          # GX[j,i] = x of column i, GY[j,i] = y of row j

def to_cell(x, y): return int(round((y - X0) / RES)), int(round((x - X0) / RES))
def to_xy(j, i): return float(X0 + i * RES), float(X0 + j * RES)

def raster(geom):
    """indices (rows, cols) of grid points inside a shapely geometry"""
    minx, miny, maxx, maxy = geom.bounds
    i0 = max(0, int((minx - X0) / RES)); i1 = min(N - 1, int((maxx - X0) / RES) + 1)
    j0 = max(0, int((miny - X0) / RES)); j1 = min(N - 1, int((maxy - X0) / RES) + 1)
    sx = GX[j0:j1 + 1, i0:i1 + 1]; sy = GY[j0:j1 + 1, i0:i1 + 1]
    m = contains_xy(geom, sx, sy)
    jj, ii = np.nonzero(m)
    return jj + j0, ii + i0

def pad_poly(pad):
    ps = pad.GetEffectivePolygon()
    o = ps.Outline(0)
    pts = [(ToMM(o.CPoint(k).x) - CX, ToMM(o.CPoint(k).y) - CY) for k in range(o.PointCount())]
    poly = Polygon(pts)
    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
        d = ToMM(pad.GetDrillSize().x)
        p = pad.GetPosition()
        poly = Point(ToMM(p.x) - CX, ToMM(p.y) - CY).buffer(d / 2 + 0.12)
    return poly

class Router:
    def __init__(self, board):
        self.b = board
        self.nets = {}
        self.pads = []   # (netname, layers, poly)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetname() or None
                layers = [l for l, L in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(L)]
                if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                    layers = [0, 1]
                self.pads.append(dict(net=net, layers=layers, poly=pad_poly(pad),
                                      smd=pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD,
                                      ref=fp.GetReference(), num=pad.GetNumber()))
        # static obstacles: board edge + keep-outs
        shape = design.outline_poly(EDGE_CLR + HALF)
        self.inside = np.zeros((N, N), bool)
        jj, ii = raster(shape); self.inside[jj, ii] = True
        self.keepout = np.zeros((N, N), bool)
        for z in board.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                o = z.Outline().Outline(0)
                pts = [(ToMM(o.CPoint(k).x) - CX, ToMM(o.CPoint(k).y) - CY) for k in range(o.PointCount())]
                jj, ii = raster(Polygon(pts).buffer(HALF)); self.keepout[jj, ii] = True
        self.ownpad = np.zeros((N, N), bool)
        for p in self.pads:
            jj, ii = raster(p["poly"]); self.ownpad[jj, ii] = True
        # cells where vias are not allowed (inside SMD pads -> no via-in-pad)
        self.novia = np.zeros((N, N), bool)
        for p in self.pads:
            if p["smd"]:
                jj, ii = raster(p["poly"].buffer(VIA_D / 2)); self.novia[jj, ii] = True

    # ---------------------------------------------------------------- claims
    def reset(self):
        self.cnt = np.zeros((2, N, N), np.uint8)
        self.who = np.full((2, N, N), -1, np.int32)
        self.netid = {}
        self.tracks = []   # (net, layer, [(x,y)...], width)
        self.vias = []     # (net, x, y)
        self.gnd_fail = []
        self.holes = np.zeros((N, N), bool)
        for p in self.pads:
            if len(p["layers"]) == 2:   # drilled pad
                c = p["poly"].centroid
                rh = math.sqrt(p["poly"].area / math.pi)
                jj, ii = raster(Point(c.x, c.y).buffer(min(rh, 0.6) + VIA_DRILL / 2 + 0.3)); self.holes[jj, ii] = True
        for p in self.pads:
            g = p["poly"].buffer(CLR + HALF, 8)
            for l in p["layers"]:
                self.claim(l, raster(g), p["net"])

    def nid(self, net):
        if net is None: return -5   # unconnected pads block everyone
        return self.netid.setdefault(net, len(self.netid))

    def claim(self, l, idx, net):
        jj, ii = idx
        if getattr(self, "rec", None) is not None: self.rec.append(("C", l, jj, ii, net))
        n = self.nid(net)
        c = self.cnt[l, jj, ii]; w = self.who[l, jj, ii]
        new_c = np.where(c == 0, 1, np.where(w == n, c, 2)).astype(np.uint8)
        if n == -5: new_c[:] = 2
        self.cnt[l, jj, ii] = new_c
        self.who[l, jj, ii] = np.where(c == 0, n, w)

    def allowed(self, net):
        n = self.nid(net)
        a = (self.cnt == 0) | ((self.cnt == 1) & (self.who == n))
        a &= self.inside[None] & ~self.keepout[None]
        if net in POWER:   # wider track -> stay one more cell away from foreign copper
            a2 = a.copy()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a2 &= np.roll(a, d, axis=(1, 2))
            # keep own pads reachable
            a = a2 | (a & (self.who == n) & (self.cnt == 1) & self.ownpad[None])
        return a

    # ---------------------------------------------------------------- A*
    def astar(self, allow, via_ok, sources, targets, tgt_xy, goal_layer=None, pen=None):
        """sources/targets: sets of flat state ids (l*N*N + j*N + i)"""
        NN = N * N
        tx, ty = to_cell(*tgt_xy)
        dirs = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
        def h(j, i):
            if goal_layer is not None: return 0.0
            dj, di = abs(j - tx), abs(i - ty)
            return (max(dj, di) + 0.4142 * min(dj, di))
        g = {}; parent = {}; pq = []
        for s in sources:
            g[s] = 0.0; parent[s] = None
            l, r = divmod(s, NN); j, i = divmod(r, N)
            heapq.heappush(pq, (h(j, i), 0.0, s, -1))
        closed = set()
        allow_flat = allow.reshape(-1)
        pops = 0
        while pq:
            f, gc, s, d0 = heapq.heappop(pq)
            if s in closed: continue
            closed.add(s); pops += 1
            if pops > 400000: return None
            if (s in targets) or (goal_layer is not None and s // NN == goal_layer and parent[s] is not None and parent[s] // NN != goal_layer):
                path = []
                while s is not None:
                    path.append(s); s = parent[s]
                return path[::-1]
            l, r = divmod(s, NN); j, i = divmod(r, N)
            for k, (dj, di, c) in enumerate(dirs):
                jn, inn = j + dj, i + di
                if not (0 <= jn < N and 0 <= inn < N): continue
                ns = l * NN + jn * N + inn
                if not allow_flat[ns] or ns in closed: continue
                if dj and di:  # no corner cutting
                    if not allow_flat[l * NN + jn * N + i] or not allow_flat[l * NN + j * N + inn]:
                        continue
                cost = gc + c + (TURN_COST if d0 not in (-1, k) else 0) + (pen[ns] if pen is not None else 0)
                if cost < g.get(ns, 1e18):
                    g[ns] = cost; parent[ns] = s
                    heapq.heappush(pq, (cost + h(jn, inn), cost, ns, k))
            # via
            if via_ok[j, i]:
                ns = (1 - l) * NN + r
                if ns not in closed and allow_flat[ns]:
                    cost = gc + VIA_COST + (pen[ns] if pen is not None else 0)
                    if cost < g.get(ns, 1e18):
                        g[ns] = cost; parent[ns] = s
                        heapq.heappush(pq, (cost + h(j, i), cost, ns, -1))
        return None

    def via_map(self, allow):
        both = allow[0] & allow[1] & ~self.novia
        rad = int(math.ceil(0.25 / RES))
        via_ok = both.copy()
        for dj in range(-rad, rad + 1):
            for di in range(-rad, rad + 1):
                if dj * dj + di * di <= rad * rad:
                    via_ok &= np.roll(np.roll(both, dj, 0), di, 1)
        return via_ok & ~self.holes

    def route_net(self, net, pads, dry=False, pen=None):
        allow = self.allowed(net)
        via_ok = self.via_map(allow)
        NN = N * N
        def pad_states(p):
            jj, ii = raster(p["poly"].buffer(-0.04))
            if len(jj) == 0:
                c = p["poly"].centroid; j, i = to_cell(c.x, c.y); jj, ii = np.array([j]), np.array([i])
            st = set()
            for l in p["layers"]:
                for j, i in zip(jj, ii):
                    if allow[l, j, i]: st.add(l * NN + j * N + i)
            return st
        pstates = [pad_states(p) for p in pads]
        if any(len(s) == 0 for s in pstates):
            return False, "pad blocked"
        if net == "GND":   # each SMD pad gets a short stub to a via into the ground pours
            retry, gnd_cells = [], set()
            tht = set()
            for q, st in zip(pads, pstates):
                if not q["smd"]: tht |= st
            fxg = getattr(self, "fixed_cells", {}).get("GND")
            if fxg: tht |= {s for s in fxg if allow.reshape(-1)[s]}
            for k, p in enumerate(pads):
                if not p["smd"]: continue
                c = p["poly"].centroid
                path = self.astar(allow, via_ok, pstates[k], tht, (c.x, c.y), goal_layer=1 - p["layers"][0])
                if path is None:
                    retry.append(k); continue
                self.commit(net, path, SIG_W + 0.05)
                gnd_cells.update(path)
                allow = self.allowed(net); via_ok = self.via_map(allow)
            for k in retry:   # connect to any ground copper already placed
                p = pads[k]; c = p["poly"].centroid
                tgt = set(gnd_cells)
                for q, st in zip(pads, pstates):
                    if q is not p and not q["smd"]: tgt |= st
                path = self.astar(allow, via_ok, pstates[k], tgt, (c.x, c.y))
                if path is None:
                    self.gnd_fail.append(f"{p['ref']}.{p['num']}"); continue
                self.commit(net, path, SIG_W)
                gnd_cells.update(path); allow = self.allowed(net); via_ok = self.via_map(allow)
            return True, None
        tree = set(pstates[0])
        todo = list(range(1, len(pads)))
        fx = getattr(self, "fixed_cells", {}).get(net)
        if fx:
            fxa = {s for s in fx if allow.reshape(-1)[s]}
            touching = [k for k in range(len(pads)) if pstates[k] & fx]
            if touching:
                tree = set(fxa)
                for k in touching: tree |= pstates[k]
                todo = [k for k in range(len(pads)) if k not in touching]
        paths = []
        while todo:
            # nearest remaining pad to the tree (centroid distance)
            tc = np.array([[ (s % NN) % N, (s % NN) // N] for s in list(tree)[:: max(1, len(tree) // 200)]])
            def dist(k):
                c = pads[k]["poly"].centroid; ci, cj = (c.x - X0) / RES, (c.y - X0) / RES
                return np.min(np.hypot(tc[:, 0] - ci, tc[:, 1] - cj))
            todo.sort(key=dist)
            k = todo.pop(0)
            c = pads[k]["poly"].centroid
            path = self.astar(allow, via_ok, tree, pstates[k], (c.x, c.y), pen=pen)
            if path is None:
                return False, f"{pads[k]['ref']}.{pads[k]['num']}"
            paths.append(path)
            tree |= set(path) | pstates[k]
        if dry: return True, paths
        # commit
        w = PWR_W if net in POWER else SIG_W
        for path in paths:
            self.commit(net, path, w)
        return True, None

    def commit(self, net, path, w):
        NN = N * N
        pts = []
        for s in path:
            l, r = divmod(s, NN); j, i = divmod(r, N)
            pts.append((l, j, i))
        # split on layer changes -> vias
        runs, cur = [], [pts[0]]
        for p in pts[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur); x, y = to_xy(p[1], p[2])
                self.vias.append((net, x, y))
                jj, ii = raster(Point(x, y).buffer(VIA_DRILL + 0.3)); self.holes[jj, ii] = True
                if getattr(self, "rec", None) is not None: self.rec.append(("H", 0, jj, ii, net))
                g = Point(x, y).buffer(VIA_D / 2 + CLR + HALF, 12)
                for l in (0, 1): self.claim(l, raster(g), net)
                cur = [p]
            else:
                cur.append(p)
        runs.append(cur)
        for run in runs:
            if len(run) < 2: continue
            l = run[0][0]
            # simplify collinear points
            simp = [run[0]]
            for a, b, c in zip(run, run[1:], run[2:]):
                if (b[1] - a[1], b[2] - a[2]) != (c[1] - b[1], c[2] - b[2]):
                    simp.append(b)
            simp.append(run[-1])
            xy = [to_xy(p[1], p[2]) for p in simp]
            self.tracks.append((net, l, xy, w))
            g = LineString(xy).buffer(w / 2 + CLR + HALF, 8)
            self.claim(l, raster(g), net)

    def run(self, order, passes=6, seed=1):
        import random
        rnd = random.Random(seed)
        groups = {}
        for p in self.pads:
            if p["net"]: groups.setdefault(p["net"], []).append(p)
        order = [n for n in order if n in groups and len(groups[n]) > 1]
        best = None
        for ps in range(passes):
            t0 = time.time()
            self.reset()
            failed = []
            for net in order:
                ok, why = self.route_net(net, groups[net])
                if not ok: failed.append((net, why))
            score = len(failed) * 100 + len(self.gnd_fail) * 10 + len(self.vias) * 0.01
            print(f"pass {ps}: {len(order) - len(failed)}/{len(order)} nets, {len(self.vias)} vias, "
                  f"gnd_fail={len(self.gnd_fail)} {time.time() - t0:.0f}s failed={failed}", flush=True)
            if best is None or score < best[0]:
                best = (score, list(self.tracks), list(self.vias), list(failed), list(self.gnd_fail),
                        self.cnt.copy(), self.who.copy(), dict(self.netid))
            if not failed and not self.gnd_fail: break
            fn = [f[0] for f in failed]
            rest = [n for n in order if n not in fn and n != "GND"]
            # small random perturbation of the remaining order
            for _ in range(3):
                a, c = rnd.randrange(len(rest)), rnd.randrange(len(rest))
                rest[a], rest[c] = rest[c], rest[a]
            order = fn + rest + (["GND"] if "GND" not in fn else [])
            order = [n for n in order if n != "GND"] + ["GND"]
        _, self.tracks, self.vias, failed, self.gnd_fail, self.cnt, self.who, self.netid = best
        return failed

    def snapshot_pads(self):
        self.reset(); self.rec = None
        self.fixed_cells = {}
        NN = N * N
        for net, l, xy, w in getattr(self, "fixed_tracks", []):
            g = LineString(xy).buffer(w / 2 + CLR + HALF, 8)
            self.claim(l, raster(g), net)
            jj, ii = raster(LineString(xy).buffer(w / 2))
            self.fixed_cells.setdefault(net, set()).update((l * NN + jj * N + ii).tolist())
        for net, x, y in getattr(self, "fixed_vias", []):
            g = Point(x, y).buffer(VIA_D / 2 + CLR + HALF, 12)
            for l in (0, 1): self.claim(l, raster(g), net)
            jj, ii = raster(Point(x, y).buffer(VIA_DRILL + 0.3)); self.holes[jj, ii] = True
            jj, ii = raster(Point(x, y).buffer(VIA_D / 2))
            for l in (0, 1): self.fixed_cells.setdefault(net, set()).update((l * NN + jj * N + ii).tolist())
        self.base = (self.cnt.copy(), self.who.copy(), self.holes.copy())

    def rebuild(self, routed, nets=None):
        self.cnt, self.who, self.holes = (a.copy() for a in self.base)
        self.tracks, self.vias = [], []
        self.rec = None
        for n, (tr, vi, rec) in routed.items():
            if nets is not None and n not in nets: continue
            self.tracks += tr; self.vias += vi
            for kind, l, jj, ii, net in rec:
                if kind == "C": self.claim(l, (jj, ii), net)
                else: self.holes[jj, ii] = True

    def run_ripup(self, order, max_iter=900, max_rips=20):
        groups = {}
        for p in self.pads:
            if p["net"]: groups.setdefault(p["net"], []).append(p)
        order = [n for n in order if n in groups and len(groups[n]) > 1 and n != "GND"]
        self.snapshot_pads()
        routed, rips, failed = {}, {}, []
        hist = np.zeros((2, N, N), np.float32)
        queue = list(order)
        NN = N * N
        it = 0
        # USB pairs first on an empty board, then fixed
        for net in ["USB_D+", "USB_D-", "CC1", "CC2"]:
            self.rebuild(routed)
            self.rec = []; t0, v0 = len(self.tracks), len(self.vias)
            ok, why = self.route_net(net, groups[net])
            if ok:
                routed[net] = (self.tracks[t0:], self.vias[v0:], self.rec); rips[net] = max_rips
                queue.remove(net)
            self.rec = None
        # ground first: every SMD ground pad gets a short stub + via, then stays fixed
        self.rebuild(routed); self.gnd_fail = []
        self.rec = []; t0, v0 = len(self.tracks), len(self.vias)
        self.route_net("GND", groups["GND"])
        routed["GND"] = (self.tracks[t0:], self.vias[v0:], self.rec); self.rec = None
        rips["GND"] = max_rips
        gnd_fail = list(self.gnd_fail)
        print("ground stubs placed, failed:", gnd_fail, flush=True)
        while queue and it < max_iter:
            it += 1
            net = queue.pop(0)
            self.rebuild(routed)
            self.rec = []; t0, v0 = len(self.tracks), len(self.vias)
            ok, why = self.route_net(net, groups[net])
            if ok:
                routed[net] = (self.tracks[t0:], self.vias[v0:], self.rec); self.rec = None
                continue
            self.rec = None
            # dry run ignoring every net that may still be ripped up
            protected = {n for n in routed if rips.get(n, 0) >= max_rips}
            occ = np.zeros((2, N, N), np.float32)
            for n, (tr, vi, rec) in routed.items():
                if n in protected: continue
                m = np.zeros((2, N, N), bool)
                for kind, l, jj, ii, _ in rec:
                    if kind == "C": m[l, jj, ii] = True
                occ += m
            pen = (6.0 * occ + hist).reshape(-1).tolist()
            self.rebuild(routed, nets=protected)
            ok, paths = self.route_net(net, groups[net], dry=True, pen=pen)
            if not ok:
                failed.append((net, why)); continue
            cells = np.array(sorted({s for p in paths for s in p}), dtype=np.int64)
            victims = []
            for n, (tr, vi, rec) in routed.items():
                if n in protected: continue
                hit = False
                for kind, l, jj, ii, _ in rec:
                    if kind != "C": continue
                    if np.isin(l * NN + jj.astype(np.int64) * N + ii, cells, assume_unique=False).any():
                        hit = True; break
                if hit: victims.append(n)
            for n in victims:
                del routed[n]; rips[n] = rips.get(n, 0) + 1
            cl, cr = np.divmod(cells, NN)
            hist.reshape(2, -1)[cl, cr] += 1.5
            queue = [net] + queue + victims
            print(f"  rip-up for {net}: removed {victims}", flush=True)
        for n in queue: failed.append((n, "not routed (iteration limit)"))
        # final state + ground stubs
        self.rebuild(routed)
        self.gnd_fail = gnd_fail
        print(f"routed {len(routed)}/{len(order)} signal/power nets, {len(self.vias)} vias, "
              f"ground stubs failed: {self.gnd_fail}, failed: {failed}", flush=True)
        return failed

    def stitch(self, pitch=2.4, net="GND"):
        allow = self.allowed(net)
        both = allow[0] & allow[1] & ~self.novia
        rad = int(math.ceil((VIA_D / 2 + CLR + 0.15) / RES))
        ok = both.copy()
        for dj in range(-rad, rad + 1):
            for di in range(-rad, rad + 1):
                if dj * dj + di * di <= rad * rad:
                    ok &= np.roll(np.roll(both, dj, 0), di, 1)
        n = 0
        step = int(pitch / RES)
        for j in range(0, N, step):
            for i in range(0, N, step):
                if ok[j, i] and not self.holes[j, i]:
                    x, y = to_xy(j, i)
                    if not design.outline_poly(1.2).contains(Point(x, y)): continue
                    self.vias.append((net, x, y)); n += 1
                    jj, ii = raster(Point(x, y).buffer(VIA_DRILL + 0.3)); self.holes[jj, ii] = True
        return n

    def write(self, board):
        nets = board.GetNetsByName()
        for net, l, xy, w in self.tracks + getattr(self, "fixed_tracks", []):
            for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(VECTOR2I(FromMM(CX + x1), FromMM(CY + y1)))
                t.SetEnd(VECTOR2I(FromMM(CX + x2), FromMM(CY + y2)))
                t.SetWidth(FromMM(w)); t.SetLayer(pcbnew.F_Cu if l == 0 else pcbnew.B_Cu)
                t.SetNet(nets[net]); board.Add(t)
        for net, x, y in self.vias + getattr(self, "fixed_vias", []):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(VECTOR2I(FromMM(CX + x), FromMM(CY + y)))
            v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(VIA_DRILL))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNet(nets[net]); board.Add(v)

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(src)
    for t in list(b.GetTracks()): b.Remove(t)
    r = Router(b)
    r.fixed_tracks = list(getattr(design, "FIXED_TRACKS", []))
    r.fixed_vias = list(getattr(design, "FIXED_VIAS", []))
    allnets = sorted({p["net"] for p in r.pads if p["net"]})
    groups = {}
    for p in r.pads:
        if p["net"]: groups.setdefault(p["net"], []).append(p)
    def spread(n):
        c = [p["poly"].centroid for p in groups[n]]
        return (max(q.x for q in c) - min(q.x for q in c)) + (max(q.y for q in c) - min(q.y for q in c))
    first = ["VBUS", "USB_D+", "USB_D-", "CC1", "CC2"]
    power = ["VBAT", "+3V3", "+1V8"]
    sig = sorted([n for n in allnets if n not in first + power + ["GND"]], key=spread)
    if getattr(design, "POWER_FIRST", False):     # route the 3.3 V net before the signals
        order = first + ["+3V3"] + sig + [p for p in power if p != "+3V3"] + ["GND"]
    else:
        order = first + sig + power + ["GND"]
    failed = r.run_ripup(order)
    print("GND pads without stub:", r.gnd_fail)
    print("stitching vias:", r.stitch())
    r.write(b)
    pcbnew.SaveBoard(dst, b)
    print("saved", dst, "failed:", failed)
