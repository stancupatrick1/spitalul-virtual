// =====================================================================
//  SPITALUL VIRTUAL – companion app for the Spitalul Virtual Band
//  made by Stancu Patrick
//
//  The band saves one record per minute all day. This app downloads them
//  over Bluetooth and saves them to Apple Health (iPhone) or Health Connect
//  (Android). The Spitalul Virtual platform then imports them through ROOK
//  when you press "Preia din dispozitive".
// =====================================================================
import 'package:flutter/material.dart';

import 'src/sync_service.dart';

const red = Color(0xFFE8283C);
const bg = Color(0xFF0B0B0D);
const card = Color(0xFF16171B);
const line = Color(0xFF26282E);
const dim = Color(0xFF8B8E98);
const cyan = Color(0xFF28C8FF);
const amber = Color(0xFFFFB428);
const green = Color(0xFF28DC78);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SvApp());
}

class SvApp extends StatelessWidget {
  const SvApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Spitalul Virtual',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: bg,
        colorScheme: const ColorScheme.dark(primary: red, surface: card, onPrimary: Colors.white),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final sync = SyncService();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    sync.load().then((_) {
      if (sync.paired) sync.sync(); // sync by itself when the app opens
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final last = sync.lastSync;
    if (state == AppLifecycleState.resumed &&
        sync.paired &&
        (last == null || DateTime.now().difference(last) > const Duration(minutes: 15))) {
      sync.sync();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    sync.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListenableBuilder(
          listenable: sync,
          builder: (context, _) => ListView(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
            children: [
              const _Header(),
              const SizedBox(height: 20),
              _Today(sync),
              const SizedBox(height: 12),
              _BandCard(sync),
              const SizedBox(height: 16),
              _SyncButton(sync),
              if (sync.error != null) ...[const SizedBox(height: 12), _ErrorCard(sync)],
              const SizedBox(height: 20),
              Text(
                'Datele ajung în ${sync.store.name}. Pe platforma Spitalul Virtual apasă '
                '„Preia din dispozitive” ca să apară și acolo.',
                style: const TextStyle(color: dim, fontSize: 13, height: 1.4),
              ),
              const SizedBox(height: 8),
              Wrap(spacing: 4, children: [
                TextButton(
                  onPressed: sync.busy || !sync.paired ? null : sync.findBand,
                  child: const Text('Fă brățara să vibreze'),
                ),
                TextButton(
                  onPressed: sync.busy || !sync.paired ? null : sync.forget,
                  child: const Text('Folosește altă brățară'),
                ),
              ]),
              const SizedBox(height: 12),
              const Text(
                'Proiect hobby: valorile sunt estimări, nu sunt pentru uz medical. '
                'Temperatura este a pielii (de obicei 32–35 °C), nu a corpului.',
                style: TextStyle(color: dim, fontSize: 12, height: 1.4),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      SizedBox(
        width: 34,
        height: 34,
        child: Stack(children: [
          Positioned(left: 12, top: 2, child: _bar(10, 30)),
          Positioned(left: 2, top: 12, child: _bar(30, 10)),
        ]),
      ),
      const SizedBox(width: 12),
      const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('SPITALUL VIRTUAL', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, letterSpacing: 1.6)),
        Text('Brățară · made by Stancu Patrick', style: TextStyle(color: dim, fontSize: 13)),
      ]),
    ]);
  }

  static Widget _bar(double w, double h) =>
      Container(width: w, height: h, decoration: BoxDecoration(color: red, borderRadius: BorderRadius.circular(3)));
}

class _Box extends StatelessWidget {
  const _Box({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: card,
          border: Border.all(color: line),
          borderRadius: BorderRadius.circular(16),
        ),
        child: child,
      );
}

class _Today extends StatelessWidget {
  const _Today(this.s);
  final SyncService s;

  @override
  Widget build(BuildContext context) {
    final t = s.today;
    Widget tile(String label, String value, String unit, Color c, [String? sub]) => Expanded(
          child: _Box(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: const TextStyle(color: dim, fontSize: 13)),
              const SizedBox(height: 4),
              Text.rich(TextSpan(children: [
                TextSpan(text: value, style: TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: c)),
                TextSpan(text: ' $unit', style: const TextStyle(fontSize: 14, color: dim)),
              ])),
              if (sub != null) Text(sub, style: const TextStyle(color: dim, fontSize: 12)),
            ]),
          ),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Padding(
        padding: EdgeInsets.only(left: 4, bottom: 8),
        child: Text('Azi', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
      ),
      Row(children: [
        tile('Puls mediu', t.hrN == 0 ? '--' : '${t.hrAvg}', 'bpm', red,
            t.hrN == 0 ? null : 'între ${t.hrMin} și ${t.hrMax}'),
        const SizedBox(width: 12),
        tile('Pași', '${t.steps}', '', green),
      ]),
      const SizedBox(height: 12),
      Row(children: [
        tile('SpO2', t.spo2?.toString() ?? '--', '%', cyan),
        const SizedBox(width: 12),
        tile('Temp. piele', t.temp?.toStringAsFixed(1) ?? '--', '°C', amber),
      ]),
    ]);
  }
}

String _ago(DateTime t) {
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'chiar acum';
  if (d.inMinutes < 60) return 'acum ${d.inMinutes} min';
  if (d.inHours < 24) return 'acum ${d.inHours} h';
  return 'acum ${d.inDays} zile';
}

class _BandCard extends StatelessWidget {
  const _BandCard(this.s);
  final SyncService s;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    void row(String a, String b) => rows.add(Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(a, style: const TextStyle(color: dim)),
            Flexible(child: Text(b, textAlign: TextAlign.right)),
          ]),
        ));
    row('Brățara', s.deviceName ?? 'nu e asociată');
    if (s.battery != null) row('Baterie', '${s.battery}%');
    row('Ultima sincronizare', s.lastSync == null ? 'niciodată' : _ago(s.lastSync!));
    if (s.lastSync != null) row('Minute aduse atunci', '${s.lastMinutes}');
    if (s.info != null) {
      final i = s.info!;
      final days = i.count / 1440;
      row('Memorate în brățară', '${i.count} min (${days.toStringAsFixed(days < 10 ? 1 : 0)} zile)');
    }
    return _Box(child: Column(children: rows));
  }
}

class _SyncButton extends StatelessWidget {
  const _SyncButton(this.s);
  final SyncService s;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      FilledButton(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
        onPressed: s.busy ? null : s.sync,
        child: Text(s.busy ? 'Se sincronizează…' : (s.paired ? 'Sincronizează' : 'Conectează brățara')),
      ),
      if (s.busy) ...[
        const SizedBox(height: 12),
        LinearProgressIndicator(value: s.progress, color: red, backgroundColor: line, minHeight: 6,
            borderRadius: BorderRadius.circular(3)),
      ],
      if (s.status.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text(s.status, textAlign: TextAlign.center, style: const TextStyle(color: dim)),
      ],
    ]);
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard(this.s);
  final SyncService s;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF2A1416),
        border: Border.all(color: const Color(0xFF4A1D22)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(s.error!, style: const TextStyle(color: Color(0xFFFFB3BB), height: 1.4)),
        if (s.needsHealthConnect)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: OutlinedButton(onPressed: s.store.installHealthConnect, child: const Text('Instalează Health Connect')),
          ),
      ]),
    );
  }
}
