// Writes samples to Apple Health (iPhone) or Health Connect (Android).
import 'dart:io';

import 'package:health/health.dart';

import 'samples.dart';

class HealthStore {
  final _health = Health();
  bool _configured = false;

  bool get isAndroid => Platform.isAndroid;
  String get name => isAndroid ? 'Health Connect' : 'Apple Health';

  List<HealthDataType> get _types => [
        HealthDataType.HEART_RATE,
        HealthDataType.BLOOD_OXYGEN,
        HealthDataType.STEPS,
        if (isAndroid) HealthDataType.SKIN_TEMPERATURE,
      ];

  Future<void> _configure() async {
    if (_configured) return;
    await _health.configure();
    _configured = true;
  }

  /// On Android, Health Connect must be installed (it is built in from Android 14).
  Future<bool> available() async {
    await _configure();
    if (!isAndroid) return true;
    final s = await _health.getHealthConnectSdkStatus();
    return s == HealthConnectSdkStatus.sdkAvailable;
  }

  Future<void> installHealthConnect() async {
    await _configure();
    await _health.installHealthConnect();
  }

  /// Asks for permission to write. Returns false if the user said no.
  Future<bool> authorize() async {
    await _configure();
    final perms = _types.map((_) => HealthDataAccess.WRITE).toList();
    try {
      return await _health.requestAuthorization(_types, permissions: perms);
    } catch (_) {
      // e.g. skin temperature not supported by an older Health Connect: try without it
      if (!isAndroid) rethrow;
      final t = _types.where((x) => x != HealthDataType.SKIN_TEMPERATURE).toList();
      return _health.requestAuthorization(t, permissions: t.map((_) => HealthDataAccess.WRITE).toList());
    }
  }

  /// Writes the samples; returns how many were saved.
  Future<int> write(List<HealthSample> samples) async {
    await _configure();
    var ok = 0;
    for (final s in samples) {
      try {
        if (await _writeOne(s)) ok++;
      } catch (_) {
        // one bad sample (or an unsupported type on this phone) must not stop the sync
      }
    }
    return ok;
  }

  Future<bool> _writeOne(HealthSample s) {
    switch (s.kind) {
      case SampleKind.heartRate:
        return _health.writeHealthData(
            value: s.value, type: HealthDataType.HEART_RATE, startTime: s.start, endTime: s.end, clientRecordId: s.id);
      case SampleKind.steps:
        return _health.writeHealthData(
            value: s.value, type: HealthDataType.STEPS, startTime: s.start, endTime: s.end, clientRecordId: s.id);
      case SampleKind.spo2:
        // Apple Health stores SpO2 as a fraction (0.98), Health Connect as a percentage (98).
        return _health.writeBloodOxygen(
            saturation: isAndroid ? s.value : s.value / 100, startTime: s.start, endTime: s.end);
      case SampleKind.skinTemp:
        if (!isAndroid) return Future.value(false);
        return _health.writeHealthData(
            value: s.value, type: HealthDataType.SKIN_TEMPERATURE, startTime: s.start, endTime: s.end, clientRecordId: s.id);
    }
  }
}
