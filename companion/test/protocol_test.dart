import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:spitalul_virtual/src/protocol.dart';
import 'package:spitalul_virtual/src/samples.dart';

/// Builds a 12-byte record exactly like the band firmware (little-endian).
List<int> rec(int t, {int hr = 0, int spo2 = 0, int? temp100, int steps = 0, int flags = 0}) {
  final b = ByteData(12)
    ..setUint32(0, t, Endian.little)
    ..setUint8(4, hr)
    ..setUint8(5, spo2)
    ..setInt16(6, temp100 ?? -32768, Endian.little)
    ..setUint16(8, steps, Endian.little)
    ..setUint8(10, flags)
    ..setUint8(11, 0);
  return b.buffer.asUint8List();
}

const t0 = 1767225600; // 2026-01-01 00:00 UTC

void main() {
  test('parses a records packet', () {
    final p = HistoryParser();
    expect(p.add([0x01, ...rec(t0, hr: 72, spo2: 97, temp100: 3345, steps: 12, flags: 0x0F), ...rec(t0 + 60)]), isTrue);
    expect(p.records, hasLength(2));
    final r = p.records.first;
    expect(r.time, DateTime.utc(2026, 1, 1));
    expect(r.hr, 72);
    expect(r.spo2, 97);
    expect(r.temp, closeTo(33.45, 1e-9));
    expect(r.steps, 12);
    expect(r.onWrist && r.hasHr && r.hasSpo2 && r.hasTemp, isTrue);
    expect(p.records[1].temp, isNull);
    expect(p.records[1].hasHr, isFalse);
  });

  test('end and info packets', () {
    final p = HistoryParser();
    final end = ByteData(9)
      ..setUint8(0, 0x02)
      ..setUint32(1, 1440, Endian.little)
      ..setUint32(5, t0 + 86340, Endian.little);
    p.add(end.buffer.asUint8List());
    expect(p.done, isTrue);
    expect(p.endCount, 1440);
    expect(p.endNewest, t0 + 86340);

    final info = ByteData(20)
      ..setUint8(0, 0x03)
      ..setUint32(1, 500, Endian.little)
      ..setUint32(5, t0, Endian.little)
      ..setUint32(9, t0 + 499 * 60, Endian.little)
      ..setUint32(13, t0 + 30000, Endian.little)
      ..setInt16(17, 120, Endian.little)
      ..setUint8(19, 2);
    p.add(info.buffer.asUint8List());
    expect(p.info!.count, 500);
    expect(p.info!.tzMinutes, 120);
    expect(p.info!.clockSet, isTrue);
    expect(p.info!.firmware, 2);
    p.add([0x04, 87]);
    expect(p.battery, 87);
  });

  test('builds health samples', () {
    final p = HistoryParser();
    final bytes = <int>[0x01];
    for (var i = 0; i < 20; i++) {
      bytes.addAll(rec(t0 + i * 60, hr: 60 + i, spo2: i < 10 ? 96 : 0, temp100: 3300 + i, steps: i.isEven ? 10 : 0,
          flags: 0x01 | 0x02 | (i < 10 ? 0x04 : 0) | 0x08));
    }
    p.add(bytes);
    final s = buildSamples(p.records, includeSkinTemp: true);
    int count(SampleKind k) => s.where((x) => x.kind == k).length;
    expect(count(SampleKind.heartRate), 20);
    expect(count(SampleKind.steps), 10);
    expect(count(SampleKind.spo2), 1); // only the first 10 minutes have SpO2
    expect(s.firstWhere((x) => x.kind == SampleKind.spo2).value, 96);
    expect(count(SampleKind.skinTemp), 2); // two 10-minute buckets
    expect(buildSamples(p.records, includeSkinTemp: false).where((x) => x.kind == SampleKind.skinTemp), isEmpty);
    // samples are in time order and ids are unique
    expect(s.map((x) => x.id).toSet(), hasLength(s.length));
    for (var i = 1; i < s.length; i++) {
      expect(s[i].start.isBefore(s[i - 1].start), isFalse);
    }
  });

  test('groups by hour', () {
    final p = HistoryParser();
    final bytes = <int>[0x01];
    for (var i = 0; i < 20; i++) {
      bytes.addAll(rec(t0 + 3000 + i * 60));
    }
    p.add(bytes);
    final g = byHour(p.records);
    expect(g.map((x) => x.length), [10, 10]);
  });
}
