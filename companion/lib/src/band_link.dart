// Bluetooth connection to the Spitalul Virtual Band.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import 'protocol.dart';

class BandException implements Exception {
  BandException(this.message);
  final String message;
  @override
  String toString() => message;
}

class BandLink {
  BluetoothDevice? device;
  BluetoothCharacteristic? _cmd;
  BluetoothCharacteristic? _hist;
  StreamSubscription<List<int>>? _sub;
  final parser = HistoryParser();
  void Function()? _onPacket;

  static final _service = Guid(BandUuids.service);

  bool get connected => device?.isConnected ?? false;

  /// Finds a band. If [savedId] is given, only that band is accepted.
  static Future<BluetoothDevice> find({String? savedId, Duration timeout = const Duration(seconds: 12)}) async {
    if (await FlutterBluePlus.isSupported == false) {
      throw BandException('Telefonul nu are Bluetooth Low Energy.');
    }
    final state = await FlutterBluePlus.adapterState
        .where((s) => s != BluetoothAdapterState.unknown)
        .first
        .timeout(const Duration(seconds: 5), onTimeout: () => BluetoothAdapterState.unknown);
    if (state != BluetoothAdapterState.on) {
      throw BandException('Pornește Bluetooth-ul și încearcă din nou.');
    }

    final found = Completer<BluetoothDevice>();
    final sub = FlutterBluePlus.onScanResults.listen((results) {
      for (final r in results) {
        final ok = savedId == null || r.device.remoteId.str == savedId;
        if (ok && !found.isCompleted) found.complete(r.device);
      }
    });
    try {
      await FlutterBluePlus.startScan(withServices: [_service], timeout: timeout);
      return await found.future.timeout(timeout + const Duration(seconds: 1));
    } on TimeoutException {
      throw BandException(savedId == null
          ? 'Nu am găsit nicio brățară. Ține-o aproape de telefon și apasă scurt butonul ei.'
          : 'Nu găsesc brățara. Verifică să fie pornită și aproape de telefon.');
    } finally {
      await sub.cancel();
      await FlutterBluePlus.stopScan();
    }
  }

  Future<void> connect(BluetoothDevice d) async {
    device = d;
    await d.connect(timeout: const Duration(seconds: 15)); // Android asks for a large MTU by itself
    final services = await d.discoverServices();
    final sv = services.where((s) => s.uuid == _service).firstOrNull;
    if (sv == null) throw BandException('Dispozitivul nu este o brățară Spitalul Virtual.');
    BluetoothCharacteristic? ch(String uuid) => sv.characteristics.where((c) => c.uuid == Guid(uuid)).firstOrNull;
    _cmd = ch(BandUuids.command);
    _hist = ch(BandUuids.history);
    if (_cmd == null || _hist == null) {
      throw BandException('Brățara are un program vechi. Încarcă firmware-ul nou (versiunea 2).');
    }
    _sub = _hist!.onValueReceived.listen((v) {
      parser.add(v);
      _onPacket?.call();
    });
    d.cancelWhenDisconnected(_sub!);
    await _hist!.setNotifyValue(true);
  }

  Future<void> send(String command) async {
    final c = _cmd;
    if (c == null) throw BandException('Brățara nu este conectată.');
    await c.write(utf8.encode(command));
  }

  /// Sets the band's clock (UTC) and time zone.
  Future<void> setClock() async {
    final now = DateTime.now();
    await send('time=${now.millisecondsSinceEpoch ~/ 1000}');
    await send('tz=${now.timeZoneOffset.inMinutes}');
  }

  Future<BandInfo> info() async {
    parser.info = null;
    await _waitFor(() => parser.info != null, () => send('info'), const Duration(seconds: 5));
    // the battery packet follows right after
    await Future.delayed(const Duration(milliseconds: 300));
    return parser.info!;
  }

  /// Downloads every record newer than [since] (unix seconds).
  Future<List<BandRecord>> history(int since, {void Function(int received)? progress}) async {
    parser.reset();
    var last = DateTime.now();
    _onPacket = () {
      last = DateTime.now();
      progress?.call(parser.records.length);
    };
    try {
      await send('sync=$since');
      // wait until the end packet; give up if nothing arrives for 10 s
      while (!parser.done) {
        await Future.delayed(const Duration(milliseconds: 100));
        if (!connected) throw BandException('Brățara s-a deconectat în timpul descărcării.');
        if (DateTime.now().difference(last) > const Duration(seconds: 10)) {
          throw BandException('Brățara nu mai răspunde. Încearcă din nou.');
        }
      }
    } finally {
      _onPacket = null;
    }
    final recs = List<BandRecord>.of(parser.records)..sort((a, b) => a.time.compareTo(b.time));
    return recs;
  }

  Future<void> _waitFor(bool Function() cond, Future<void> Function() start, Duration timeout) async {
    await start();
    final end = DateTime.now().add(timeout);
    while (!cond()) {
      if (DateTime.now().isAfter(end)) throw BandException('Brățara nu răspunde.');
      await Future.delayed(const Duration(milliseconds: 50));
    }
  }

  Future<void> disconnect() async {
    await _sub?.cancel();
    _sub = null;
    _cmd = _hist = null;
    try {
      await device?.disconnect();
    } catch (_) {}
  }
}
