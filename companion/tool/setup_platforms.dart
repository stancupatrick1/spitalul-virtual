// Prepares the Android + iOS projects made by `flutter create` for Bluetooth and
// Apple Health / Health Connect. Safe to run more than once.
//
//   flutter create --org ro.stancupatrick --project-name spitalul_virtual --platforms android,ios .
//   dart run tool/setup_platforms.dart
import 'dart:io';

const marker = 'spitalul-virtual-setup';

void main() {
  if (Directory('android').existsSync()) _android();
  if (Directory('ios').existsSync()) _ios();
  // `flutter create` adds a counter-app test that doesn't apply to this app
  final wt = File('test/widget_test.dart');
  if (wt.existsSync() && wt.readAsStringSync().contains('MyApp')) wt.deleteSync();
  stdout.writeln('Gata: proiectele Android/iOS sunt pregătite.');
}

String _read(String p) => File(p).readAsStringSync();
void _write(String p, String s) => File(p).writeAsStringSync(s);

String _insertBefore(String s, String anchor, String text, String file) {
  final i = s.indexOf(anchor);
  if (i < 0) throw StateError('$file: nu găsesc "$anchor"');
  return s.substring(0, i) + text + s.substring(i);
}

// ------------------------------------------------------------------ Android
void _android() {
  // 1. AndroidManifest.xml
  const mf = 'android/app/src/main/AndroidManifest.xml';
  var m = _read(mf);
  if (!m.contains(marker)) {
    m = _insertBefore(m, '<application', '''<!-- $marker -->
    <uses-feature android:name="android.hardware.bluetooth_le" android:required="false" />
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    <uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.health.WRITE_HEART_RATE" />
    <uses-permission android:name="android.permission.health.WRITE_OXYGEN_SATURATION" />
    <uses-permission android:name="android.permission.health.WRITE_STEPS" />
    <uses-permission android:name="android.permission.health.WRITE_SKIN_TEMPERATURE" />
    <queries>
        <package android:name="com.google.android.apps.healthdata" />
        <intent>
            <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
        </intent>
    </queries>

    ''', mf);
    m = m.replaceFirst(RegExp(r'android:label="[^"]*"'), 'android:label="Spitalul Virtual"');

    // Health Connect opens MainActivity to explain why we need the permissions
    final act = m.indexOf('android:name=".MainActivity"');
    final end = m.indexOf('</intent-filter>', act) + '</intent-filter>'.length;
    m = '${m.substring(0, end)}
            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>${m.substring(end)}';

    // Android 14+: privacy screen in Health Connect settings
    m = _insertBefore(m, '</application>', '''    <activity-alias
            android:name="ViewPermissionUsageActivity"
            android:exported="true"
            android:targetActivity=".MainActivity"
            android:permission="android.permission.START_VIEW_PERMISSION_USAGE">
            <intent-filter>
                <action android:name="android.intent.action.VIEW_PERMISSION_USAGE" />
                <category android:name="android.intent.category.HEALTH_PERMISSIONS" />
            </intent-filter>
        </activity-alias>
    ''', mf);
    _write(mf, m);
  }

  // 2. MainActivity must be a FlutterFragmentActivity for Health Connect permissions
  final kt = Directory('android/app/src/main')
      .listSync(recursive: true)
      .whereType<File>()
      .firstWhere((f) => f.path.endsWith('MainActivity.kt') || f.path.endsWith('MainActivity.java'));
  final k = kt.readAsStringSync()
      .replaceAll('io.flutter.embedding.android.FlutterActivity', 'io.flutter.embedding.android.FlutterFragmentActivity')
      .replaceAll(RegExp(r'\bFlutterActivity\(\)'), 'FlutterFragmentActivity()')
      .replaceAll(RegExp(r'extends FlutterActivity\b'), 'extends FlutterFragmentActivity');
  kt.writeAsStringSync(k);

  // 3. minSdk 26 (Health Connect)
  for (final g in ['android/app/build.gradle.kts', 'android/app/build.gradle']) {
    if (!File(g).existsSync()) continue;
    var s = _read(g);
    s = s
        .replaceAll(RegExp(r'minSdk\s*=\s*flutter\.minSdkVersion'), 'minSdk = 26')
        .replaceAll(RegExp(r'minSdkVersion\s+flutter\.minSdkVersion'), 'minSdkVersion 26');
    _write(g, s);
  }

  // 4. gradle.properties
  const gp = 'android/gradle.properties';
  var p = File(gp).existsSync() ? _read(gp) : '';
  if (!p.contains('android.useAndroidX')) p += '\nandroid.useAndroidX=true';
  if (!p.contains('android.enableJetifier')) p += '\nandroid.enableJetifier=true';
  _write(gp, '${p.trimRight()}\n');
  stdout.writeln('Android: manifest, MainActivity, minSdk 26 – OK');
}

// ------------------------------------------------------------------ iOS
void _ios() {
  // 1. Info.plist
  const pl = 'ios/Runner/Info.plist';
  var s = _read(pl);
  if (!s.contains('NSHealthUpdateUsageDescription')) {
    s = s.replaceFirstMapped(
        RegExp(r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*'), (m) => '${m[1]}Spitalul Virtual');
    final close = s.lastIndexOf('</dict>');
    s = '${s.substring(0, close)}	<key>NSBluetoothAlwaysUsageDescription</key>
	<string>Aplicația se conectează prin Bluetooth la brățara Spitalul Virtual ca să îi descarce datele.</string>
	<key>NSHealthUpdateUsageDescription</key>
	<string>Pulsul, oxigenul din sânge și pașii măsurați de brățară sunt salvați în Apple Health, ca platforma Spitalul Virtual să îi poată prelua.</string>
	<key>NSHealthShareUsageDescription</key>
	<string>Aplicația doar scrie în Apple Health datele măsurate de brățara Spitalul Virtual.</string>
	<key>UIBackgroundModes</key>
	<array>
		<string>bluetooth-central</string>
	</array>
${s.substring(close)}';
    _write(pl, s);
  }
  // 2. HealthKit entitlement
  const ent = 'ios/Runner/Runner.entitlements';
  _write(ent, '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.developer.healthkit</key>
	<true/>
	<key>com.apple.developer.healthkit.access</key>
	<array/>
</dict>
</plist>
''');

  // 3. Xcode project: iOS 15, entitlements, HealthKit framework
  const pbx = 'ios/Runner.xcodeproj/project.pbxproj';
  var x = _read(pbx);
  x = x.replaceAll(RegExp(r'IPHONEOS_DEPLOYMENT_TARGET = \d+(\.\d+)?;'), 'IPHONEOS_DEPLOYMENT_TARGET = 15.0;');
  if (!x.contains('CODE_SIGN_ENTITLEMENTS')) {
    // only the app target (its bundle id has no "RunnerTests")
    x = x.replaceAllMapped(RegExp(r'(\n(\s*)PRODUCT_BUNDLE_IDENTIFIER = (?![^;]*RunnerTests)[^;]+;)'),
        (m) => '\n${m[2]}CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements;${m[1]}');
  }
  _write(pbx, x);

  // 4. Podfile: iOS 15
  const pod = 'ios/Podfile';
  if (File(pod).existsSync()) {
    var p = _read(pod);
    p = p.replaceFirst(RegExp(r"^#?\s*platform :ios, '[\d.]+'", multiLine: true), "platform :ios, '15.0'");
    _write(pod, p);
  }
  stdout.writeln('iOS: Info.plist, HealthKit, iOS 15 – OK');
}
