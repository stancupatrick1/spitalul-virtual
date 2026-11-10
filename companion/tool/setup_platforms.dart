// Prepares the Android project made by `flutter create` for Bluetooth and
// Health Connect. Safe to run more than once.
//
//   flutter create --org ro.stancupatrick --project-name spitalul_virtual --platforms android .
//   dart run tool/setup_platforms.dart
import 'dart:io';

const marker = 'spitalul-virtual-setup';

void main() {
  if (Directory('android').existsSync()) _android();
  // `flutter create` adds a counter-app test that doesn't apply to this app
  final wt = File('test/widget_test.dart');
  if (wt.existsSync() && wt.readAsStringSync().contains('MyApp')) wt.deleteSync();
  stdout.writeln('Gata: proiectul Android este pregătit.');
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
    m = '''${m.substring(0, end)}
            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>${m.substring(end)}''';

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
