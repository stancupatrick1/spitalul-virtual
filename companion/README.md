# 📱 Spitalul Virtual – aplicația pentru telefon

Brățara salvează **un rând pe minut toată ziua**: puls, oxigen în sânge (SpO2), temperatura pielii și pași.
Aplicația descarcă datele prin Bluetooth și le pune în **Apple Health** (iPhone) sau **Health Connect** (Android).
De acolo, platforma Spitalul Virtual le preia prin ROOK când apeși **„Preia din dispozitive”**, la fel ca de la un Apple Watch.

```
brățara ──Bluetooth──▶ aplicația Spitalul Virtual ──▶ Apple Health / Health Connect ──ROOK──▶ platforma Spitalul Virtual
```

| Ce măsoară brățara | Apple Health | Health Connect |
|---|---|---|
| Puls (în fiecare minut) | ✅ Heart Rate | ✅ Heart rate |
| SpO2 (medie la 10 minute) | ✅ Blood Oxygen | ✅ Oxygen saturation |
| Pași (în fiecare minut) | ✅ Steps | ✅ Steps |
| Temperatura pielii (medie la 10 minute) | – (Apple nu are tip pentru asta; nu o salvăm greșit ca temperatură a corpului) | ✅ Skin temperature |

## Cum se folosește

1. Pornește brățara. Ceasul ei se setează singur prima dată când se conectează la aplicație.
   Din acel moment brățara memorează **ultimele ~40–45 de zile**.
2. Deschide aplicația și apasă **Conectează brățara**, apoi permite Bluetooth și scrierea în Apple Health / Health Connect.
3. După aceea aplicația se sincronizează **singură** de fiecare dată când o deschizi (sau apasă **Sincronizează**).
4. Pe platforma Spitalul Virtual: **Preia din dispozitive**.

## Instalare

### Android
Pe telefon deschide pagina **[app-latest](https://github.com/stancupatrick1/spitalul-virtual/releases/tag/app-latest)**,
descarcă `SpitalulVirtual.apk` și instalează-l.
Pe Android 13 sau mai vechi, instalează și [Health Connect](https://play.google.com/store/apps/details?id=com.google.android.apps.healthdata)
(de la Android 14 este deja în telefon). Aplicația te duce acolo dacă lipsește.

Fișierul `.apk` este construit automat de GitHub Actions la fiecare modificare ([`build.yml`](../.github/workflows/build.yml)).

### iPhone (de pe Mac)
Apple nu permite instalarea din fișier, deci aplicația se pune pe iPhone din Xcode:

```bash
git clone https://github.com/stancupatrick1/spitalul-virtual.git
bash spitalul-virtual/companion/setup_mac.sh
```

Scriptul pregătește proiectul, deschide Xcode și îți scrie pașii (alegi contul Apple, conectezi iPhone-ul, apeși ▶).
Ai nevoie de [Flutter](https://docs.flutter.dev/get-started/install/macos/mobile-ios), Xcode și CocoaPods.
Pentru iOS 15+ trebuie un Xcode destul de nou; dacă Mac-ul e prea vechi pentru Xcode-ul cerut de Flutter, scriptul îți arată versiunile.

Cu un cont Apple gratuit aplicația merge 7 zile, apoi o reinstalezi din Xcode.
Pentru TestFlight / App Store e nevoie de Apple Developer Program (99 $/an).

## Pentru dezvoltatori

```
companion/
├── lib/main.dart               ecranul aplicației
├── lib/src/protocol.dart       pachetele Bluetooth ale brățării
├── lib/src/band_link.dart      căutare, conectare, descărcarea istoricului
├── lib/src/samples.dart        minute -> mostre de sănătate (puls/min, SpO2 și temp. la 10 min)
├── lib/src/health_store.dart   scriere în Apple Health / Health Connect (pachetul `health`)
├── lib/src/sync_service.dart   tot procesul de sincronizare
├── test/                       teste pentru protocol
├── tool/setup_platforms.dart   adaugă permisiunile Bluetooth + HealthKit / Health Connect
└── setup_mac.sh                pregătire iPhone pe Mac
```

Folderele `android/` și `ios/` nu sunt în repo: le face `flutter create`, apoi `dart run tool/setup_platforms.dart` le configurează.

```bash
cd companion
flutter create --org ro.stancupatrick --project-name spitalul_virtual --platforms android,ios .
dart run tool/setup_platforms.dart
flutter test
flutter run
```

Protocolul Bluetooth este descris în [`band/docs/SYNC_PROTOCOL.md`](../band/docs/SYNC_PROTOCOL.md).

> Proiect hobby: valorile sunt estimări și **nu** sunt pentru uz medical.
