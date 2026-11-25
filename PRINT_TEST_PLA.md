# Test print PLA – carcase Spitalul Virtual

Presupunere: imprimantă FDM obișnuită, duză 0.4 mm, PLA, pat de cel puțin 220 × 220 mm.
Dacă ai altă duză sau alt pat, spune-mi și refac fișierele.

## De ce nu printezi direct carcasele din repo în PLA

`band_silicone_with_straps.stl` și `case_silicone_with_straps.stl` sunt gândite pentru silicon
sau TPU: curelele trebuie să se îndoaie, iar placa intră prin deschiderea de sus doar pentru că
siliconul se întinde (deschiderea e 30 × 15 mm, placa e 40 × 24 mm). În PLA rigid placa nu ar
intra deloc, curelele s-ar rupe, iar membrana butonului (0.9 mm) nu s-ar apăsa.

De aceea am făcut **variante de test PLA** din aceleași fișiere `.scad` (aceleași cote interioare),
tăiate în două ca să poți pune placa și bateria înăuntru:

Fișierele sunt în `band/mechanical/stl/pla_test/` și `watch/mechanical/stl/pla_test/`,
generate din `pla_test.scad` din fiecare folder `mechanical/`.

| Fișier | Ce e | Timp aprox. | PLA |
|---|---|---|---|
| `band_pla_tray.stl` | brățara: fundul + pereții, ferestre senzori, USB-C, gaura butonului | ~40 min | 4 g |
| `band_pla_frame.stl` | brățara: partea de sus cu fereastra | ~10 min | 1 g |
| `band_pla_cap.stl` | capacul ferestrei (intră în ramă de dedesubt) | ~8 min | 1 g |
| `watch_pla_tray.stl` | ceasul: fundul + pereții | ~50 min | 6 g |
| `watch_pla_bezel.stl` | ceasul: rama de sus cu fereastra ecranului | ~20 min | 3 g |

Toate sunt deja orientate corect: le pui pe pat așa cum se deschid, fără rotire.

Ce am schimbat față de varianta din silicon (doar în testul PLA):
- jocul în jurul plăcii e 0.35 mm pe parte în loc de 0.2 (găurile la FDM ies mai mici);
- butonul are o gaură de 3 mm prin perete (îl apeși cu o scobitoare);
- fără curele și fără "rădăcinile" lor (ar fi plutit în aer la 0.5 mm deasupra patului);
- capacul are 0.25 mm joc pe parte în plus, pentru că PLA nu se întinde.

## Setări recomandate în slicer (Cura / PrusaSlicer / OrcaSlicer)

- **Înălțime strat:** 0.16 mm (0.12 mm pentru `frame`, `bezel`, `cap` dacă vrei margini curate)
- **Pereți (perimetre):** 3 · **Straturi sus/jos:** 4
- **Umplere (infill):** 20 % gyroid (piesele sunt aproape pline oricum)
- **Suporturi:** NU. Gaura de USB-C e o punte de ~10 mm, iese bine fără suport.
- **Brim:** nu e nevoie; pune 3 mm doar la `frame`/`bezel`/`cap` dacă se dezlipesc colțurile.
- **Temperatură:** 205–210 °C duză, 60 °C pat · **Ventilator:** 100 % după primul strat
- **Viteză pereți exteriori:** max 40 mm/s
- **Elephant foot compensation:** 0.1–0.15 mm (altfel textul de pe spate și ferestrele
  senzorilor se închid la primul strat)
- Poți pune toate 5 piesele pe același pat: în total ~15 g și cam 2 ore.

## Ce verifici după print

1. Placa (sau o machetă) stă pe treapta din interior, fără să forțezi.
2. Mufa USB-C se aliniază cu deschiderea din perete.
3. Gaura butonului cade exact peste butonul de pe margine.
4. Fereastra senzorului de puls este sub MAX30102, iar cercul mic e sub senzorul de temperatură.
5. Bateria (și motorul la brățară) încap sub ramă; rama stă plat pe tavă.
6. Ceas: ecranul intră în rama de sus de dedesubt și cercul vizibil e centrat.

Dacă n-ai încă placa: `band/mechanical/stl/pcb_assembled.stl` și
`watch/mechanical/stl/pcb_assembled.stl` sunt machetele plăcilor asamblate; le poți printa
în PLA (cu suporturi doar de pe pat) ca să verifici potrivirea. Bateria: un cub 25 × 20 × 3 mm
(brățară) sau 30 × 25 × 4 mm (ceas). Ține cele două părți cu bandă adezivă – e doar un test.

Spune-mi ce cote nu se potrivesc (cu șubler, în mm) și le corectez în `.scad`.

## Pasul 2 (după test): matrițele pentru silicon, tot în PLA

Matrițele sunt în `band/mechanical/stl/mold/` și `watch/mechanical/stl/mold/`. În slicer întoarce
`mold_top` și `mold_core` cu 180° (cavitatea în sus, respectiv mânerul pe pat); `mold_bottom` rămâne așa.

| Fișier | Dimensiune | PLA aprox. |
|---|---|---|
| `band mold_top` | 60 × 239 × 17 mm | ~100 g |
| `band mold_bottom` | 60 × 239 × 9 mm | ~55 g |
| `band mold_core` | 42 × 26 × 17 mm | ~8 g |
| `watch mold_top` | 63 × 253 × 20 mm | ~115 g |
| `watch mold_bottom` | 63 × 253 × 9 mm | ~60 g |
| `watch mold_core` | 42 × 42 × 20 mm | ~12 g |

Atenție la pat: brățara (239 mm) încape pe 220 × 220 doar pusă pe diagonală; ceasul (253 mm)
are nevoie de pat ≥ 256 mm (Bambu, Prusa MK4 pe lungime). Dacă nu încape, ți le împart în două
bucăți cu știfturi.

Setări matrițe: strat 0.12–0.16 mm (suprafața cavității devine suprafața siliconului), 4 pereți,
5 straturi sus, 15 % infill, **ironing** pe `mold_bottom`. Fără suporturi, cu excepția lui
`mold_core`: acolo pune suporturi „doar de pe pat” pentru proeminențele mici de USB-C și buton.
Înainte de turnare: o pensulă de vaselină subțire sau spray de demulare; fă întâi o turnare mică
de probă ca să vezi că siliconul se întărește bine pe PLA-ul tău.
