// kickback_storefront_mini_app_ui.dart
// Production-Grade Flutter Mini-App Scaffold for OmniMarket Storefront & Merchant Studio
// Ecosystem: The Omniverse / KickBack Universe (com.kickback)

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import 'dart:convert';
import 'package:crypto/crypto.dart' as crypto;

class OmniMarketStorefrontMiniApp extends StatefulWidget {
  const OmniMarketStorefrontMiniApp({Key? key}) : super(key: key);

  @override
  _OmniMarketStorefrontMiniAppState createState() =>
      _OmniMarketStorefrontMiniAppState();
}

class _OmniMarketStorefrontMiniAppState
    extends State<OmniMarketStorefrontMiniApp>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  Database? _db;

  int _userCreditBalance = 0;
  bool _isLicensedMerchant = false;
  bool _isLoading = true;
  String _userPubkey = "";

  List<Map<String, dynamic>> _cosmeticsCatalog = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _initializeDatabaseAndState();
  }

  Future<void> _initializeDatabaseAndState() async {
    final databasesPath = await getDatabasesPath();
    final dbPath = p.join(databasesPath, 'omni_hub_immutable.db');

    _db = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (Database db, int version) async {
        await db.execute('''
          CREATE TABLE IF NOT EXISTS citizen_identity (
            pubkey TEXT PRIMARY KEY,
            handle TEXT,
            credits INTEGER,
            merchant_licensed INTEGER
          )
        ''');
        await db.execute('''
          CREATE TABLE IF NOT EXISTS event_log (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            timestamp_ns INTEGER,
            payload_json TEXT
          )
        ''');
        await db.execute('''
          CREATE TABLE IF NOT EXISTS store_catalog (
            item_id TEXT PRIMARY KEY,
            name TEXT,
            socket TEXT,
            price INTEGER,
            merchant_handle TEXT,
            equipped INTEGER
          )
        ''');
      },
    );

    // Read or initialize user identity
    final identities = await _db!.query('citizen_identity', limit: 1);
    if (identities.isNotEmpty) {
      final user = identities.first;
      _userPubkey = user['pubkey'] as String;
      _userCreditBalance = (user['credits'] as int?) ?? 1000;
      _isLicensedMerchant = (user['merchant_licensed'] as int?) == 1;
    } else {
      _userPubkey =
          "0x${DateTime.now().millisecondsSinceEpoch.toRadixString(16)}";
      _userCreditBalance = 1000;
      _isLicensedMerchant = false;
      await _db!.insert('citizen_identity', {
        'pubkey': _userPubkey,
        'handle': '@citizen',
        'credits': _userCreditBalance,
        'merchant_licensed': 0,
      });
    }

    // Load items from local database catalog
    await _loadCatalogItems();

    setState(() {
      _isLoading = false;
    });
  }

  Future<void> _loadCatalogItems() async {
    final items = await _db!.query('store_catalog');
    if (items.isNotEmpty) {
      _cosmeticsCatalog = items
          .map((i) => {
                "id": i["item_id"],
                "name": i["name"],
                "socket": i["socket"],
                "price": i["price"],
                "merchant": i["merchant_handle"],
                "equipped": (i["equipped"] as int) == 1,
                "icon": Icons.style_outlined,
                "color": Colors.cyanAccent,
              })
          .toList();
    } else {
      // Initialize base catalog if empty
      final defaultItems = [
        {
          "item_id": "item_01",
          "name": "Cyber Visor",
          "socket": "head_socket",
          "price": 100,
          "merchant_handle": "@P2PMerchant",
          "equipped": 0
        },
        {
          "item_id": "item_02",
          "name": "Plasma Wings",
          "socket": "torso_bone",
          "price": 250,
          "merchant_handle": "@P2PMerchant",
          "equipped": 0
        },
      ];
      for (var item in defaultItems) {
        await _db!.insert('store_catalog', item);
      }
      await _loadCatalogItems();
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _db?.close();
    super.dispose();
  }

  Future<void> _purchaseItem(Map<String, dynamic> item) async {
    int price = item["price"];
    if (_userCreditBalance < price) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Insufficient OmniCredits balance in SQLite ledger!"),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    final newBalance = _userCreditBalance - price;

    // Update local database
    await _db!.update(
      'citizen_identity',
      {'credits': newBalance},
      where: 'pubkey = ?',
      whereArgs: [_userPubkey],
    );

    await _db!.update(
      'store_catalog',
      {'equipped': 1},
      where: 'item_id = ?',
      whereArgs: [item["id"]],
    );

    // Record immutable purchase event in event_log table
    final timestamp = DateTime.now().microsecondsSinceEpoch * 1000;
    final payloadJson = jsonEncode({
      "item_id": item["id"],
      "price": price,
      "buyer_pubkey": _userPubkey,
    });
    final eventHash = crypto.sha256
        .convert(utf8.encode("$timestamp:$payloadJson"))
        .toString()
        .substring(0, 16);

    await _db!.insert('event_log', {
      'event_id': "evt_$eventHash",
      'event_type': "ITEM_PURCHASED",
      'timestamp_ns': timestamp,
      'payload_json': payloadJson,
    });

    setState(() {
      _userCreditBalance = newBalance;
      item["equipped"] = true;
    });

    int merchantShare = (price * 0.80).round();
    int platformShare = price - merchantShare;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E2C),
        title: Row(
          children: const [
            Icon(Icons.check_circle_outline, color: Colors.greenAccent),
            SizedBox(width: 8),
            Text("Purchased & Logged to WAL",
                style: TextStyle(color: Colors.white, fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Item: ${item['name']}",
                style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 6),
            Text("Settled Price: $price OmniCredits",
                style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.bold)),
            const Divider(color: Colors.white24, height: 20),
            Text("• Merchant (80%): $merchantShare Credits",
                style:
                    const TextStyle(color: Colors.greenAccent, fontSize: 13)),
            Text("• Platform Fee (20%): $platformShare Credits",
                style: const TextStyle(color: Colors.cyanAccent, fontSize: 13)),
            const SizedBox(height: 8),
            Text("Event Hash: evt_$eventHash",
                style: const TextStyle(
                    color: Colors.white38,
                    fontSize: 10,
                    fontFamily: 'monospace')),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Equip to Avatar",
                style: TextStyle(color: Colors.cyanAccent)),
          ),
        ],
      ),
    );
  }

  Future<void> _applyMerchantLicense() async {
    await _db!.update(
      'citizen_identity',
      {'merchant_licensed': 1},
      where: 'pubkey = ?',
      whereArgs: [_userPubkey],
    );

    setState(() {
      _isLicensedMerchant = true;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text("🎉 Merchant License Activated in SQLite Ledger!"),
        backgroundColor: Colors.greenAccent,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F0F1A),
        body:
            Center(child: CircularProgressIndicator(color: Colors.cyanAccent)),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF181824),
        elevation: 0,
        title: Row(
          children: const [
            Icon(Icons.shopping_bag_outlined, color: Colors.cyanAccent),
            SizedBox(width: 8),
            Text("OmniMarket Boutique",
                style: TextStyle(
                    color: Colors.white, fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.cyan.withOpacity(0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.bolt, color: Colors.amberAccent, size: 16),
                const SizedBox(width: 4),
                Text(
                  "$_userCreditBalance",
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.cyanAccent,
          labelColor: Colors.cyanAccent,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(
                icon: Icon(Icons.dry_cleaning_rounded),
                text: "Avatar Boutique"),
            Tab(icon: Icon(Icons.storefront_rounded), text: "Merchant Studio"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildAvatarBoutiqueTab(),
          _buildMerchantStudioTab(),
        ],
      ),
    );
  }

  Widget _buildAvatarBoutiqueTab() {
    return Column(
      children: [
        Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.purple.shade900.withOpacity(0.5),
                Colors.blue.shade900.withOpacity(0.5)
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.purpleAccent.withOpacity(0.3)),
          ),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: Colors.black38,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.cyanAccent, width: 2),
                ),
                child: const Icon(Icons.person_pin_rounded,
                    color: Colors.cyanAccent, size: 36),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text("LPE Live Dressing Room",
                        style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 15)),
                    SizedBox(height: 4),
                    Text("SQLite WAL Synchronized Ledger Active",
                        style: TextStyle(color: Colors.white60, fontSize: 12)),
                  ],
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 0.8,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: _cosmeticsCatalog.length,
            itemBuilder: (context, index) {
              final item = _cosmeticsCatalog[index];
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF181824),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color:
                        item["equipped"] ? Colors.greenAccent : Colors.white10,
                    width: item["equipped"] ? 2 : 1,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: (item["color"] as Color).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Center(
                          child: Icon(item["icon"] as IconData,
                              color: item["color"] as Color, size: 40),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(item["name"],
                        style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13)),
                    Text("Socket: ${item['socket']}",
                        style: const TextStyle(
                            color: Colors.white38, fontSize: 10)),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("${item['price']} CR",
                            style: const TextStyle(
                                color: Colors.amberAccent,
                                fontWeight: FontWeight.bold)),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: item["equipped"]
                                ? Colors.green.withOpacity(0.2)
                                : Colors.cyan,
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                          ),
                          onPressed: () => _purchaseItem(item),
                          child: Text(
                            item["equipped"] ? "Equipped" : "Buy",
                            style: TextStyle(
                              color: item["equipped"]
                                  ? Colors.greenAccent
                                  : Colors.black,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildMerchantStudioTab() {
    if (!_isLicensedMerchant) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.storefront_rounded,
                  color: Colors.cyanAccent, size: 70),
              const SizedBox(height: 16),
              const Text(
                "Open Your Avatar Boutique",
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                "Publish avatar cosmetics directly to the decentralized SQLite WAL store catalog.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white60, fontSize: 13),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                ),
                onPressed: _applyMerchantLicense,
                icon: const Icon(Icons.verified_sharp, color: Colors.black),
                label: const Text("Activate Merchant License",
                    style: TextStyle(
                        color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF181824),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(
                  children: const [
                    Text("Licensed Status",
                        style: TextStyle(color: Colors.white54, fontSize: 12)),
                    SizedBox(height: 4),
                    Text("ACTIVE",
                        style: TextStyle(
                            color: Colors.greenAccent,
                            fontWeight: FontWeight.bold,
                            fontSize: 16)),
                  ],
                ),
                Column(
                  children: [
                    const Text("Identity Pubkey",
                        style: TextStyle(color: Colors.white54, fontSize: 12)),
                    const SizedBox(height: 4),
                    Text(
                      _userPubkey.length > 12
                          ? "${_userPubkey.substring(0, 10)}..."
                          : _userPubkey,
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                          fontFamily: 'monospace'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
