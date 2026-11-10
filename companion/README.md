# 📱 Spitalul Virtual – aplicația pentru Android

Brățara salvează **un rând pe minut toată ziua**: puls, oxigen în sânge (SpO2), temperatura pielii și pași.
Aplicația descarcă datele prin Bluetooth și le pune în **Health Connect**, locul unde Android ține datele de sănătate.
De acolo, platforma Spitalul Virtual le preia prin ROOK când apeși **„Preia din dispozitive”**.

```
brățara ──Bluetooth──▶ aplicația Spitalul Virtual ──▶ Health Connect ──ROOK──▶ platforma Spitalul Virtual
```

| Ce măsoară brățara | Cum ajunge în Health Connect |
|---|---|
| Puls | o valoare pe minut (Heart rate) |
| Oxigen în sânge (SpO2) | media la 10 minute (Oxygen saturation) |
| Pași | pașii din fiecare minut (Steps) |
| Temperatura pielii | media la 10 minute (Skin temperature – nu e temperatura corpului) |

## Ce îți trebuie

- un telefon cu **Android 8 sau mai nou** și Bluetooth
- **Health Connect**: e deja în telefon de la **Android 14**. Pe Android 8–13 se instalează gratuit din
  [Google Play](https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata) (aplicația te duce acolo dacă lipsește)
- brățara Spitalul Virtual cu firmware-ul nou (versiunea 2)

## Instalare (o singură dată)

1. **Descarcă aplicația.** Pe telefon deschide
   **[github.com/stancupatrick1/spitalul-virtual/releases/tag/app-latest](https://github.com/stancupatrick1/spitalul-virtual/releases/tag/app-latest)**
   și apasă pe **`SpitalulVirtual.apk`**.
2. **Instalează.** Deschide fișierul descărcat. Dacă Android spune că nu are voie să instaleze aplicații din această sursă,
   apasă **Setări** → pornește **Permite din această sursă** → înapoi → **Instalează**.
   Dacă apare Google Play Protect („aplicație necunoscută”), alege **Instalează oricum** – aplicația nu e în Magazin Play, de aceea întreabă.
3. **Pune firmware-ul nou pe brățară** (dacă nu e deja): conectează brățara la calculator cu USB-C și rulează
   `cd band/firmware && pio run -t upload`. Fișierul gata compilat este pe aceeași pagină: `spitalul-virtual-band-firmware.bin`.

## Prima conectare

1. Pornește brățara și ține-o lângă telefon.
2. Deschide **Spitalul Virtual** și apasă **Conectează brățara**.
3. Android întreabă de **Dispozitive din apropiere** (Bluetooth) → **Permite**.
4. Se deschide **Health Connect** → pornește **Permite tot** (puls, saturație oxigen, pași, temperatura pielii) → **Permite**.
5. Aplicația găsește brățara, îi setează ceasul și descarcă ce are. Gata – brățara e asociată.

Din momentul în care ceasul e setat, brățara memorează singură toată ziua (păstrează **ultimele ~40–45 de zile**),
chiar dacă telefonul nu e lângă ea.

## În fiecare zi

1. Deschide aplicația **Spitalul Virtual** – se sincronizează singură (sau apasă **Sincronizează**).
   Brățara trebuie să fie pornită și la câțiva metri de telefon.
2. Pe platforma Spitalul Virtual apasă **Preia din dispozitive**.

Prima sincronizare după multe zile poate dura câteva minute – lasă aplicația deschisă până scrie „Gata!”.
Dacă o închizi la jumătate nu se pierde nimic: data viitoare continuă de unde a rămas.

## Dacă ceva nu merge

| Problema | Ce faci |
|---|---|
| „Nu găsesc brățara” | Pornește Bluetooth-ul, apropie brățara, apasă scurt butonul ei și încearcă iar. |
| „Brățara are un program vechi” | Pune firmware-ul nou (pasul 3 de la instalare). |
| „Instalează Health Connect” | Apasă butonul din aplicație și instalează-l din Magazin Play. |
| „Fără permisiune…” | Setări → Aplicații → Health Connect → Permisiuni aplicații → **Spitalul Virtual** → pornește tot. |
| Datele nu apar pe platformă | În Health Connect → Permisiuni aplicații, aplicația folosită de platformă (ROOK) trebuie să aibă voie să **citească** puls, saturație oxigen, pași. |
| Ai brățară nouă | În aplicație: **Folosește altă brățară**, apoi **Conectează brățara**. |
| Nu știi unde e brățara | **Fă brățara să vibreze**. |

Poți vedea datele salvate în **Health Connect → Date și acces → Activitate / Vitale**, sursa fiind „Spitalul Virtual”.

---

## Pentru dezvoltatori

```
companion/
├── lib/main.dart               ecranul aplicației
├── lib/src/protocol.dart       pachetele Bluetooth ale brățării
├── lib/src/band_link.dart      căutare, conectare, descărcarea istoricului
├── lib/src/samples.dart        minute -> mostre (puls/min, SpO2 și temperatură la 10 min)
├── lib/src/health_store.dart   scriere în Health Connect (pachetul `health`)
├── lib/src/sync_service.dart   tot procesul de sincronizare
├── test/                       teste pentru protocol
└── tool/setup_platforms.dart   adaugă permisiunile Bluetooth + Health Connect în proiectul Android
```

Folderul `android/` nu e în repo: îl face `flutter create`, iar `tool/setup_platforms.dart` îl configurează
(permisiuni, Health Connect, `FlutterFragmentActivity`, minSdk 26).
GitHub Actions ([`build.yml`](../.github/workflows/build.yml)) construiește `.apk`-ul și firmware-ul la fiecare modificare
și le pune pe pagina [app-latest](https://github.com/stancupatrick1/spitalul-virtual/releases/tag/app-latest).

```bash
cd companion
flutter create --org ro.stancupatrick --project-name spitalul_virtual --platforms android .
dart run tool/setup_platforms.dart
flutter test
flutter run            # cu telefonul conectat prin USB (depanare USB pornită)
```

Protocolul Bluetooth: [`band/docs/SYNC_PROTOCOL.md`](../band/docs/SYNC_PROTOCOL.md).

> Proiect hobby: valorile sunt estimări și **nu** sunt pentru uz medical.
