#!/bin/bash
# Rebuild the whole Spitalul Virtual hardware package from scripts/design.py
set -e
cd "$(dirname "$0")"
PCB=../hardware/kicad/spitalul_virtual_band.kicad_pcb
T=$(mktemp -d)
python3 build_pcb.py                       # placement, outline, artwork, zones
# autoroute (2 layers); try a few via costs until every net is routed
for vc in 12 14 10 16 8 18 20; do
  VIA_COST=$vc python3 router.py $PCB $T/routed.kicad_pcb | tee $T/route.log | grep -v "rip-up"
  grep -q "^saved .* failed: \[\]$" $T/route.log && { echo "routing complete with via cost $vc"; break; }
done
python3 finish_pcb.py $T/routed.kicad_pcb $T/filled.kicad_pcb
python3 repair_gnd.py $T/filled.kicad_pcb $T/final.kicad_pcb
python3 finish_pcb.py $T/final.kicad_pcb $PCB
python3 project_settings.py
python3 drc.py $PCB ../hardware/kicad/drc_report.txt
python3 build_sch.py                       # schematic + symbol library
python3 export_jlc.py                      # gerbers, drill, BOM, CPL, STEP
python3 models3d.py > /dev/null            # our STEP models for parts KiCad lacks
./render.sh $PCB ../docs/img/_flat
python3 render_pretty.py $PCB ../docs/img
rm -rf $T ../docs/img/_flat ../docs/img/_layers
