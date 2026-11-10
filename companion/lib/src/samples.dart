// Turns the band's per-minute records into health samples.
//
//  heart rate   one sample per minute (like a watch in workout mode)
//  steps        one sample per minute with steps
//  SpO2         one sample per 10 minutes (average, needs 3+ good minutes)
//  skin temp.   one sample per 10 minutes (saved as skin temperature,
//               never as body temperature)
import 'protocol.dart';

enum SampleKind { heartRate, steps, spo2, skinTemp }

class HealthSample {
  HealthSample(this.kind, this.value, this.start, this.end);
  final SampleKind kind;
  final double value;
  final DateTime start;
  final DateTime end;

  /// Stable id, so Health Connect replaces instead of duplicating on a retry.
  String get id => 'sv-band-${kind.name}-${start.millisecondsSinceEpoch ~/ 1000}';
}

const _bucket = 600; // seconds

List<HealthSample> buildSamples(List<BandRecord> records, {required bool includeSkinTemp}) {
  final out = <HealthSample>[];
  const minute = Duration(minutes: 1);

  for (final r in records) {
    if (r.hasHr) out.add(HealthSample(SampleKind.heartRate, r.hr.toDouble(), r.time, r.time));
    if (r.steps > 0) out.add(HealthSample(SampleKind.steps, r.steps.toDouble(), r.time, r.time.add(minute)));
  }

  // 10-minute averages
  final spo2 = <int, List<int>>{};
  final temp = <int, List<double>>{};
  final lastTime = <int, DateTime>{};
  for (final r in records) {
    final b = r.epoch ~/ _bucket;
    if (r.hasSpo2) spo2.putIfAbsent(b, () => []).add(r.spo2);
    if (includeSkinTemp && r.hasTemp) temp.putIfAbsent(b, () => []).add(r.temp!);
    if (r.hasSpo2 || r.hasTemp) lastTime[b] = r.time;
  }
  for (final e in spo2.entries) {
    if (e.value.length < 3) continue;
    final avg = e.value.reduce((a, b) => a + b) / e.value.length;
    final t = lastTime[e.key]!;
    out.add(HealthSample(SampleKind.spo2, avg.roundToDouble(), t, t));
  }
  for (final e in temp.entries) {
    if (e.value.length < 3) continue;
    final avg = e.value.reduce((a, b) => a + b) / e.value.length;
    final t = lastTime[e.key]!;
    out.add(HealthSample(SampleKind.skinTemp, (avg * 100).round() / 100, t, t));
  }

  out.sort((a, b) => a.start.compareTo(b.start));
  return out;
}

/// Splits records into groups of one hour, so progress can be saved after each hour.
List<List<BandRecord>> byHour(List<BandRecord> records) {
  final groups = <List<BandRecord>>[];
  int? hour;
  for (final r in records) {
    final h = r.epoch ~/ 3600;
    if (h != hour) {
      groups.add([]);
      hour = h;
    }
    groups.last.add(r);
  }
  return groups;
}
