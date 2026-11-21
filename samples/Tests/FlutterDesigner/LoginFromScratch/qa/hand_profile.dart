import 'package:flutter/material.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});
  static const routeName = '/profile';

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  int _taps = 0;

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: Colors.amber, borderRadius: BorderRadius.circular(20)),
      child: Text(text),
    );
  }

  @override
  Widget build(BuildContext context) {
    final greeting = 'Hello #$_taps';
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const CircleAvatar(radius: 40, backgroundColor: Colors.indigo),
            const SizedBox(height: 16),
            Text(greeting, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            _badge('PRO'),
            ElevatedButton(
              onPressed: () => setState(() => _taps++),
              child: const Text('Tap me'),
            ),
          ],
        ),
      ),
    );
  }
}
