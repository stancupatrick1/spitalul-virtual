// Spitalul Virtual Band – Bluetooth history protocol (see band/docs/SYNC_PROTOCOL.md)
import 'dart:typed_data';

class BandUuids {
  static const service = '5b7e0001-5356-4261-6e64-537461636e75';
  static const live = '5b7e0002-5356-4261-6e64-537461636e75';
  static const command = '5b7e0003-5356-4261-6e64-537461636e75';
  static const history = '5b7e0004-5356-4261-6e64-537461636e75';
}

/// One minute of data saved by the band.
class BandRecord {
  BandRecord({
    required this.time,
    required this.hr,
    required this.spo2,
    required this.temp,
    required this.steps,
    required this.flags,
  });

  static const size = 12;

  /// Start of the minute (UTC).
  final DateTime time;
  final int hr; // bpm, 0 = none
  final int spo2; // %, 0 = none
  final double? temp; // skin temperature in °C
  final int steps; // steps during this minute
  final int flags;

  int get epoch => time.millisecondsSinceEpoch ~/ 1000;
  bool get onWrist => flags & 0x01 != 0;
  bool get hasHr => flags & 0x02 != 0 && hr >= 30 && hr <= 230;
  bool get hasSpo2 => flags & 0x04 != 0 && spo2 >= 70 && spo2 <= 100;
  bool get hasTemp => flags & 0x08 != 0 && temp != null;

  static BandRecord parse(ByteData d, int o) {
    final t = d.getUint32(o, Endian.little);
    final rawTemp = d.getInt16(o + 6, Endian.little);
    return BandRecord(
      time: DateTime.fromMillisecondsSinceEpoch(t * 1000, isUtc: true),
      hr: d.getUint8(o + 4),
      spo2: d.getUint8(o + 5),
      temp: rawTemp == -32768 ? null : rawTemp / 100.0,
      steps: d.getUint16(o + 8, Endian.little),
      flags: d.getUint8(o + 10),
    );
  }
}

/// Answer to the "info" command.
class BandInfo {
  BandInfo({
    required this.count,
    required this.oldest,
    required this.newest,
    required this.clockSet,
    required this.tzMinutes,
    required this.firmware,
  });

  final int count; // minutes saved on the band
  final int oldest; // unix seconds, 0 = none
  final int newest;
  final bool clockSet;
  final int tzMinutes;
  final int firmware;
}

/// Collects History notifications until the end-of-sync packet arrives.
class HistoryParser {
  final records = <BandRecord>[];
  bool done = false;
  int endCount = 0;
  int endNewest = 0;
  BandInfo? info;
  int? battery;

  void reset() {
    records.clear();
    done = false;
    endCount = 0;
    endNewest = 0;
  }

  /// Returns true if the packet was understood.
  bool add(List<int> packet) {
    if (packet.isEmpty) return false;
    final d = ByteData.sublistView(Uint8List.fromList(packet));
    switch (packet[0]) {
      case 0x01:
        final n = (packet.length - 1) ~/ BandRecord.size;
        for (var i = 0; i < n; i++) {
          records.add(BandRecord.parse(d, 1 + i * BandRecord.size));
        }
        return n > 0;
      case 0x02:
        if (packet.length < 9) return false;
        endCount = d.getUint32(1, Endian.little);
        endNewest = d.getUint32(5, Endian.little);
        done = true;
        return true;
      case 0x03:
        if (packet.length < 20) return false;
        info = BandInfo(
          count: d.getUint32(1, Endian.little),
          oldest: d.getUint32(5, Endian.little),
          newest: d.getUint32(9, Endian.little),
          clockSet: d.getUint32(13, Endian.little) != 0,
          tzMinutes: d.getInt16(17, Endian.little),
          firmware: d.getUint8(19),
        );
        return true;
      case 0x04:
        if (packet.length < 2) return false;
        battery = packet[1];
        return true;
    }
    return false;
  }
}
