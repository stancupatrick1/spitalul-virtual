"""Write sensible JLCPCB rules into the KiCad project file."""
import json, os
pro = os.path.join(os.path.dirname(__file__), "..", "hardware", "kicad", "spitalul_virtual_watch.kicad_pro")
p = json.load(open(pro))
ds = p["board"]["design_settings"]
sev = ds.setdefault("rule_severities", {})
sev.update({"starved_thermal": "warning", "silk_overlap": "ignore", "lib_footprint_mismatch": "ignore",
            "lib_footprint_issues": "ignore", "silk_over_copper": "warning", "text_height": "warning"})
r = ds.setdefault("rules", {})
r.update({"min_clearance": 0.127, "min_track_width": 0.15, "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3,
          "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0,
          "min_text_height": 0.8, "min_text_thickness": 0.15})
for nc in p["net_settings"]["classes"]:
    if nc["name"] == "Default":
        nc.update({"clearance": 0.127, "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3})
p["meta"]["filename"] = "spitalul_virtual_watch.kicad_pro"
p.setdefault("text_variables", {})["AUTHOR"] = "Stancu Patrick"
json.dump(p, open(pro, "w"), indent=2)
print("project rules written")
