#!/bin/bash
# quick 2D renders of the board: render.sh <pcb> <outdir>
PCB=$1; OUT=$2; mkdir -p $OUT
kicad-cli pcb export svg --page-size-mode 2 --exclude-drawing-sheet -l F.Cu,F.SilkS,F.Fab,Edge.Cuts -o $OUT/top.svg $PCB >/dev/null 2>&1
kicad-cli pcb export svg --page-size-mode 2 --exclude-drawing-sheet -m -l B.Cu,B.SilkS,B.Fab,Edge.Cuts -o $OUT/bottom.svg $PCB >/dev/null 2>&1
python3 -c "
import cairosvg,sys
for n in ['top','bottom']: cairosvg.svg2png(url='$OUT/%s.svg'%n, write_to='$OUT/%s.png'%n, output_width=1000, background_color='white')
"
