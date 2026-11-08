"""Export everything JLCPCB needs: Gerbers + drill (zip), BOM and CPL for assembly, STEP model.
Usage: python3 export_jlc.py"""
import csv, os, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(__file__))
from design import P, PROJECT

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PCB = os.path.join(ROOT, "hardware", "kicad", PROJECT + ".kicad_pcb")
OUT = os.path.join(ROOT, "hardware", "jlcpcb")
GDIR = os.path.join(OUT, "gerbers")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(GDIR)

def run(*a):
    r = subprocess.run(["kicad-cli", *a], capture_output=True, text=True)
    if r.returncode: print(r.stdout, r.stderr); raise SystemExit(1)

layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
run("pcb", "export", "gerbers", "-l", layers, "--subtract-soldermask", "--no-x2", "-o", GDIR + "/", PCB)
run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
    "--excellon-zeros-format", "decimal", "--excellon-oval-format", "alternate",
    "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", "-o", GDIR + "/", PCB)
zpath = os.path.join(OUT, "spitalul_virtual_gerbers.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(GDIR)): z.write(os.path.join(GDIR, f), f)
print("gerbers:", sorted(os.listdir(GDIR)))

# ---- position file -> JLC CPL
pos = os.path.join(OUT, "_pos.csv")
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", pos, PCB)
assembled = {p["ref"]: p for p in P if p["lcsc"]}
rows = []
with open(pos) as f:
    for r in csv.DictReader(f):
        if r["Ref"] not in assembled: continue
        rows.append([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                     "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]):.1f}'])
os.remove(pos)
rows.sort(key=lambda r: (r[0].rstrip("0123456789"), int("".join(c for c in r[0] if c.isdigit()) or 0)))
with open(os.path.join(OUT, "spitalul_virtual_CPL.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writerows(rows)
missing = set(assembled) - {r[0] for r in rows}
assert not missing, missing

# ---- BOM grouped by LCSC part
groups = {}
for p in P:
    if not p["lcsc"]: continue
    groups.setdefault((p["value"], p["fp"].split(":")[1], p["lcsc"]), []).append(p["ref"])
with open(os.path.join(OUT, "spitalul_virtual_BOM.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ",".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int(''.join(c for c in r if c.isdigit()))))), fp, lcsc])
print("BOM lines:", len(groups), " placed parts:", len(rows))

# ---- 3D model of the assembled board
run("pcb", "export", "step", "--subst-models", "-f", "-o", os.path.join(ROOT, "mechanical", "pcb_assembled.step"), PCB)
print("done ->", OUT)
