import 'package:flutter/material.dart';

void main() {
  runApp(const OmniverseApp());
}

class OmniverseApp extends StatelessWidget {
  const OmniverseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'The KickBack & Omniverse',
      theme: ThemeData.dark(useMaterial3: true),
      home: const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.hub, size: 64, color: Colors.cyanAccent),
              SizedBox(height: 16),
              Text(
                'The KickBack & Omniverse Core (v4.0)',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text('Serverless P2P Mesh Network Ready'),
            ],
          ),
        ),
      ),
    );
  }
}
