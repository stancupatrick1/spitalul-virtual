// The whole sync: find band -> set clock -> download history -> save to the health store.
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'band_link.dart';
import 'health_store.dart';
import 'protocol.dart';
import 'samples.dart';

class DaySummary {
  int steps = 0;
  int hrSum = 0, hrN = 0, hrMin = 0, hrMax = 0;
  int? spo2;
  double? temp;
  int get hrAvg => hrN == 0 ? 0 : (hrSum / hrN).round();
}

class SyncService extends ChangeNotifier {
  final store = HealthStore();
  final _link = BandLink();
  SharedPreferences? _prefs;

  bool busy = false;
  String status = '';
  double? progress; // 0..1, null = unknown
  String? error;
  bool needsHealthConnect = false;

  String? deviceId;
  String? deviceName;
  DateTime? lastSync;
  int lastMinutes = 0;
  int? battery;
  BandInfo? info;
  final today = DaySummary();
  String _todayKey = '';

  bool get paired => deviceId != null;

  Future<void> load() async {
    final p = _prefs = await SharedPreferences.getInstance();
    deviceId = p.getString('deviceId');
    deviceName = p.getString('deviceName');
    final ls = p.getInt('lastSync');
    lastSync = ls == null ? null : DateTime.fromMillisecondsSinceEpoch(ls);
    lastMinutes = p.getInt('lastMinutes') ?? 0;
    _loadToday();
    notifyListeners();
  }

  String _dayKey(DateTime local) => '${local.year}-${local.month}-${local.day}';

  void _loadToday() {
    final p = _prefs!;
    _todayKey = _dayKey(DateTime.now());
    final k = 'day_$_todayKey';
    today
      ..steps = p.getInt('${k}_steps') ?? 0
      ..hrSum = p.getInt('${k}_hrSum') ?? 0
      ..hrN = p.getInt('${k}_hrN') ?? 0
      ..hrMin = p.getInt('${k}_hrMin') ?? 0
      ..hrMax = p.getInt('${k}_hrMax') ?? 0
      ..spo2 = p.getInt('${k}_spo2')
      ..temp = p.getDouble('${k}_temp');
  }

  Future<void> _addToToday(List<BandRecord> recs) async {
    if (_dayKey(DateTime.now()) != _todayKey) _loadToday();
    for (final r in recs) {
      if (_dayKey(r.time.toLocal()) != _todayKey) continue;
      today.steps += r.steps;
      if (r.hasHr) {
        today.hrSum += r.hr;
        today.hrN++;
        today.hrMin = today.hrMin == 0 ? r.hr : (r.hr < today.hrMin ? r.hr : today.hrMin);
        today.hrMax = r.hr > today.hrMax ? r.hr : today.hrMax;
      }
      if (r.hasSpo2) today.spo2 = r.spo2;
      if (r.hasTemp) today.temp = r.temp;
    }
    final p = _prefs!, k = 'day_$_todayKey';
    await p.setInt('${k}_steps', today.steps);
    await p.setInt('${k}_hrSum', today.hrSum);
    await p.setInt('${k}_hrN', today.hrN);
    await p.setInt('${k}_hrMin', today.hrMin);
    await p.setInt('${k}_hrMax', today.hrMax);
    if (today.spo2 != null) await p.setInt('${k}_spo2', today.spo2!);
    if (today.temp != null) await p.setDouble('${k}_temp', today.temp!);
  }

  void _set(String s, {double? p}) {
    status = s;
    progress = p;
    notifyListeners();
  }

  Future<void> sync() async {
    if (busy) return;
    busy = true;
    error = null;
    needsHealthConnect = false;
    _set('Pregătesc…');
    final p = _prefs ?? await SharedPreferences.getInstance();
    _prefs = p;
    try {
      if (!await store.available()) {
        needsHealthConnect = true;
        throw BandException('Instalează aplicația Health Connect de la Google, apoi încearcă din nou.');
      }
      if (!await store.authorize()) {
        throw BandException('Fără permisiune nu pot salva datele în ${store.name}. '
            'Permite scrierea pentru puls, oxigen, pași și temperatura pielii.');
      }

      _set(paired ? 'Caut brățara…' : 'Caut o brățară Spitalul Virtual…');
      final dev = await BandLink.find(savedId: deviceId);
      _set('Mă conectez…');
      await _link.connect(dev);
      if (deviceId != dev.remoteId.str) {
        deviceId = dev.remoteId.str;
        deviceName = dev.platformName.isEmpty ? 'Spitalul Virtual Band' : dev.platformName;
        await p.setString('deviceId', deviceId!);
        await p.setString('deviceName', deviceName!);
      }

      await _link.setClock();
      info = await _link.info();
      battery = _link.parser.battery;

      final sinceKey = 'since_$deviceId';
      var since = p.getInt(sinceKey) ?? 0;
      final i = info!;
      final from = since > i.oldest ? since : i.oldest - 60;
      final expected = i.newest > from ? (i.newest - from) ~/ 60 : 0;

      _set('Descarc datele din brățară…', p: expected > 0 ? 0 : null);
      final recs = await _link.history(since, progress: (n) {
        progress = expected > 0 ? (n / expected).clamp(0.0, 1.0) * 0.5 : null;
        status = 'Descarc datele din brățară… $n min';
        notifyListeners();
      });
      await _link.disconnect();

      final hours = byHour(recs);
      var done = 0;
      for (final h in hours) {
        _set('Salvez în ${store.name}… ${(done * 100 / recs.length).round()}%', p: 0.5 + 0.5 * done / recs.length);
        await store.write(buildSamples(h, includeSkinTemp: true));
        await _addToToday(h);
        since = h.last.epoch;
        await p.setInt(sinceKey, since); // progress is kept even if the app is closed
        done += h.length;
      }

      lastSync = DateTime.now();
      lastMinutes = recs.length;
      await p.setInt('lastSync', lastSync!.millisecondsSinceEpoch);
      await p.setInt('lastMinutes', lastMinutes);
      _set(recs.isEmpty ? 'Nu sunt date noi.' : 'Gata! ${recs.length} minute salvate în ${store.name}.');
    } catch (e) {
      error = e is BandException ? e.message : 'Eroare: $e';
      _set('');
    } finally {
      await _link.disconnect();
      busy = false;
      progress = null;
      notifyListeners();
    }
  }

  /// Makes the band vibrate so it can be found.
  Future<void> findBand() async {
    if (busy) return;
    busy = true;
    error = null;
    _set('Caut brățara…');
    try {
      final dev = await BandLink.find(savedId: deviceId);
      await _link.connect(dev);
      await _link.send('buzz');
      _set('Brățara a vibrat.');
    } catch (e) {
      error = e is BandException ? e.message : 'Eroare: $e';
      _set('');
    } finally {
      await _link.disconnect();
      busy = false;
      notifyListeners();
    }
  }

  Future<void> forget() async {
    final p = _prefs ?? await SharedPreferences.getInstance();
    await p.remove('deviceId');
    await p.remove('deviceName');
    deviceId = deviceName = null;
    info = null;
    battery = null;
    status = 'Brățara a fost uitată. Apasă „Sincronizează” ca să cauți alta.';
    notifyListeners();
  }
}
