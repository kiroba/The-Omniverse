import 'package:flutter/material.dart';

class OmniCastApp extends StatelessWidget {
  const OmniCastApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmniCast P2P Video Chat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6366F1),
          secondary: Color(0xFF10B981),
          surface: Color(0xFF1E293B),
        ),
      ),
      home: const StargateAuthLoginScreen(),
    );
  }
}

class StargateAuthLoginScreen extends StatefulWidget {
  const StargateAuthLoginScreen({super.key});

  @override
  State<StargateAuthLoginScreen> createState() => _StargateAuthLoginScreenState();
}

class _StargateAuthLoginScreenState extends State<StargateAuthLoginScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF6366F1).withValues(alpha: 0.15),
                  border: Border.all(color: const Color(0xFF6366F1), width: 2),
                ),
                child: const Icon(Icons.videocam_rounded, size: 64, color: Color(0xFF6366F1)),
              ),
              const SizedBox(height: 24),
              const Text(
                'OmniCast P2P',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 8),
              const Text(
                'Zero-Server WebRTC Video & Encrypted Mesh Chat',
                style: TextStyle(fontSize: 14, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.security_rounded),
                label: const Text('Connect Stargate Key'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
