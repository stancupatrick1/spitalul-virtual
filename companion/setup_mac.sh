#!/bin/bash
# Spitalul Virtual – pregătește aplicația pentru iPhone pe Mac.
# Rulează din Terminal:   bash companion/setup_mac.sh
set -e
cd "$(dirname "$0")"

if ! command -v flutter >/dev/null; then
  echo "Lipsește Flutter. Instalează-l de aici: https://docs.flutter.dev/get-started/install/macos/mobile-ios"
  exit 1
fi
if ! command -v pod >/dev/null; then
  echo "Lipsește CocoaPods. Rulează:  sudo gem install cocoapods   (sau: brew install cocoapods)"
  exit 1
fi

echo "== Versiuni =="
sw_vers -productVersion | sed 's/^/macOS /'
xcodebuild -version | head -1 || true
flutter --version | head -1

flutter create --org ro.stancupatrick --project-name spitalul_virtual --platforms android,ios .
dart run tool/setup_platforms.dart
flutter pub get
(cd ios && pod install)

cat <<'EOF'

Gata! Acum:
 1. Se deschide Xcode. Stânga sus: click pe „Runner” (iconița albastră).
 2. Tab-ul „Signing & Capabilities” -> Team: alege contul tău Apple
    (Add Account… dacă nu apare). Dacă cere, schimbă Bundle Identifier
    în ceva unic, de ex. ro.stancupatrick.spitalulvirtual
 3. Verifică să apară „HealthKit” în listă (dacă nu: + Capability -> HealthKit).
 4. Conectează iPhone-ul cu cablu, alege-l sus în Xcode și apasă ▶ (Run).
 5. Pe iPhone: Setări -> General -> VPN și gestionare dispozitive -> ai încredere în contul tău.
    (cu cont Apple gratuit aplicația trebuie reinstalată din Xcode o dată la 7 zile)
EOF
open ios/Runner.xcworkspace
