#!/bin/bash
# Rebuild the whole Spitalul Virtual hardware package from scripts/design.py
set -e
cd "$(dirname "$0")"
PCB=../hardware/kicad/spitalul_virtual_watch.kicad_pcb
T=$(mktemp -d)
python3 build_pcb.py                       # placement, outline, artwork, zones
# autoroute (2 layers); try a few hash seeds until every net is routed
for seed in 0 1 2 3 4 5 6 7 8 9; do
  PYTHONHASHSEED=$seed python3 router.py $PCB $T/routed.kicad_pcb | tee $T/route.log | grep -v "rip-up"
  grep -q "^saved .* failed: \[\]$" $T/route.log && { echo "routing complete with seed $seed"; break; }
done
python3 finish_pcb.py $T/routed.kicad_pcb $T/filled.kicad_pcb
python3 repair_gnd.py $T/filled.kicad_pcb $T/final.kicad_pcb
python3 finish_pcb.py $T/final.kicad_pcb $PCB
python3 project_settings.py
python3 drc.py $PCB ../hardware/kicad/drc_report.txt
python3 build_sch.py                       # schematic + symbol library
python3 export_jlc.py                      # gerbers, drill, BOM, CPL, STEP
./render.sh $PCB ../docs/img/_flat
python3 render_pretty.py $PCB ../docs/img
rm -rf $T ../docs/img/_flat ../docs/img/_layers
