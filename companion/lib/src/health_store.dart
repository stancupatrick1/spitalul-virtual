// Writes samples to Health Connect (Android).
import 'package:health/health.dart';

import 'samples.dart';

class HealthStore {
  final _health = Health();
  bool _configured = false;

  String get name => 'Health Connect';

  static const _types = [
    HealthDataType.HEART_RATE,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.STEPS,
    HealthDataType.SKIN_TEMPERATURE,
  ];

  Future<void> _configure() async {
    if (_configured) return;
    await _health.configure();
    _configured = true;
  }

  /// Health Connect must be installed (it is built in from Android 14).
  Future<bool> available() async {
    await _configure();
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
    try {
      return await _health.requestAuthorization(_types,
          permissions: _types.map((_) => HealthDataAccess.WRITE).toList());
    } catch (_) {
      // an older Health Connect may not know skin temperature: try without it
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
        // one bad sample (or a type this phone doesn't support) must not stop the sync
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
        // Health Connect stores SpO2 as a percentage (98)
        return _health.writeBloodOxygen(saturation: s.value, startTime: s.start, endTime: s.end);
      case SampleKind.skinTemp:
        return _health.writeHealthData(
            value: s.value, type: HealthDataType.SKIN_TEMPERATURE, startTime: s.start, endTime: s.end, clientRecordId: s.id);
    }
  }
}
