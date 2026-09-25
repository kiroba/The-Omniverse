// kickback_storefront_mini_app_ui.dart
// Production-grade Flutter Mini-App Scaffold for OmniMarket Storefront & Merchant Studio
// Ecosystem: The Omniverse / KickBack Universe (com.omniboutique)

import 'package:flutter/material.dart';

class OmniMarketStorefrontMiniApp extends StatefulWidget {
  const OmniMarketStorefrontMiniApp({Key? key}) : super(key: key);

  @override
  _OmniMarketStorefrontMiniAppState createState() => _OmniMarketStorefrontMiniAppState();
}

class _OmniMarketStorefrontMiniAppState extends State<OmniMarketStorefrontMiniApp>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  int _userCreditBalance = 2450;
  bool _isLicensedMerchant = false;
  
  // Sample Catalog Data
  final List<Map<String, dynamic>> _cosmeticsCatalog = [
    {
      "id": "item_01",
      "name": "Neon Cyber Visor (3D)",
      "socket": "head_socket",
      "price": 500,
      "merchant": "@CyberpunkVault",
      "rating": 4.9,
      "icon": Icons.remove_red_eye_outlined,
      "color": Colors.cyanAccent,
      "equipped": false
    },
    {
      "id": "item_02",
      "name": "Holographic Wings",
      "socket": "torso_bone",
      "price": 1200,
      "merchant": "@AetherCraft",
      "rating": 5.0,
      "icon": Icons.blur_on_rounded,
      "color": Colors.purpleAccent,
      "equipped": false
    },
    {
      "id": "item_03",
      "name": "Quantum Combat Boots",
      "socket": "legs_socket",
      "price": 350,
      "merchant": "@FutureWear",
      "rating": 4.7,
      "icon": Icons.directions_run_rounded,
      "color": Colors.amberAccent,
      "equipped": true
    },
    {
      "id": "item_04",
      "name": "Floating Plasma Pet",
      "socket": "shoulder_socket",
      "price": 850,
      "merchant": "@OmniBeasts",
      "rating": 4.8,
      "icon": Icons.pets_rounded,
      "color": Colors.greenAccent,
      "equipped": false
    },
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _purchaseItem(Map<String, dynamic> item) {
    int price = item["price"];
    if (_userCreditBalance < price) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Insufficient OmniCredits! Top up in Wallet."),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    setState(() {
      _userCreditBalance -= price;
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
            Text("Purchase Complete", style: TextStyle(color: Colors.white)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Item: ${item['name']}", style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 6),
            Text("Total Paid: $price OmniCredits", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            const Divider(color: Colors.white24, height: 20),
            Text("• Merchant (80%): $merchantShare Credits", style: const TextStyle(color: Colors.greenAccent, fontSize: 13)),
            Text("• Platform Fee (20%): $platformShare Credits", style: const TextStyle(color: Colors.cyanAccent, fontSize: 13)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Equip to Avatar", style: TextStyle(color: Colors.cyanAccent)),
          ),
        ],
      ),
    );
  }

  void _applyMerchantLicense() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF181824),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Become an OmniMarket Merchant",
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              "One-Time License Fee: \$15.00 USD\n"
              "• Set your own prices for LPE 2D/3D avatar cosmetics\n"
              "• Receive 80% net revenue on every item sale\n"
              "• Automated 1-Tap Cash Out via OmniLedger Treasury",
              style: TextStyle(color: Colors.white70, fontSize: 14, height: 1.5),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepAccent,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  Navigator.pop(context);
                  setState(() {
                    _isLicensedMerchant = true;
                  });
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("🎉 Merchant License Granted! You can now publish LPE cosmetics."),
                      backgroundColor: Colors.greenAccent,
                    ),
                  );
                },
                child: const Text(
                  "Pay \$15.00 Fee & Start Selling",
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF181824),
        elevation: 0,
        title: Row(
          children: const [
            Icon(Icons.shopping_bag_outlined, color: Colors.cyanAccent),
            SizedBox(width: 8),
            Text("OmniMarket Boutique", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
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
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
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
            Tab(icon: Icon(Icons.dry_cleaning_rounded), text: "Avatar Boutique"),
            Tab(icon: Icon(Icons.storefront_rounded), text: "Merchant Studio"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // TAB 1: Avatar Boutique & Dressing Room
          _buildAvatarBoutiqueTab(),
          
          // TAB 2: Merchant Studio & 80/20 Hub
          _buildMerchantStudioTab(),
        ],
      ),
    );
  }

  Widget _buildAvatarBoutiqueTab() {
    return Column(
      children: [
        // Live 3D/2D Avatar Dressing Room Preview Header
        Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.purple.shade900.withOpacity(0.5), Colors.blue.shade900.withOpacity(0.5)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.purpleAccent.withOpacity(0.3)),
          ),
          child: Row(
            children: [
              Container(
                width: 70,
                height: 70,
                decoration: BoxDecoration(
                  color: Colors.black38,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.cyanAccent, width: 2),
                ),
                child: const Icon(Icons.person_pin_rounded, color: Colors.cyanAccent, size: 40),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text("LPE Live Dressing Room", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                    SizedBox(height: 4),
                    Text("Real-time 2D Z-Index & 3D Socket Attachment Active", style: TextStyle(color: Colors.white60, fontSize: 12)),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Cosmetic Item Cards
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
                    color: item["equipped"] ? Colors.greenAccent : Colors.white10,
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
                          child: Icon(item["icon"] as IconData, color: item["color"] as Color, size: 48),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(item["name"], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                    Text("Socket: ${item['socket']}", style: const TextStyle(color: Colors.white38, fontSize: 10)),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("${item['price']} CR", style: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: item["equipped"] ? Colors.green.withOpacity(0.2) : Colors.cyan,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          ),
                          onPressed: () => _purchaseItem(item),
                          child: Text(
                            item["equipped"] ? "Equipped" : "Buy",
                            style: TextStyle(
                              color: item["equipped"] ? Colors.greenAccent : Colors.black,
                              fontSize: 12,
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
              const Icon(Icons.storefront_rounded, color: Colors.cyanAccent, size: 80),
              const SizedBox(height: 16),
              const Text(
                "Open Your Avatar Boutique",
                style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                "Design and sell custom 2D/3D LPE avatar cosmetics to citizens across the entire Omniverse network.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white60, fontSize: 14),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                ),
                onPressed: _applyMerchantLicense,
                icon: const Icon(Icons.verified_sharp, color: Colors.black),
                label: const Text("Apply for Merchant License (\$15)", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
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
          // Merchant Dashboard Stats
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
                    Text("Total Sales", style: TextStyle(color: Colors.white54, fontSize: 12)),
                    SizedBox(height: 4),
                    Text("142", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 20)),
                  ],
                ),
                Column(
                  children: const [
                    Text("Merchant Payout (80%)", style: TextStyle(color: Colors.white54, fontSize: 12)),
                    SizedBox(height: 4),
                    Text("56,800 CR", style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 20)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const Text("Publish New LPE Asset", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          TextFormField(
            decoration: InputDecoration(
              labelText: "Asset Name",
              labelStyle: const TextStyle(color: Colors.white60),
              filled: true,
              fillColor: const Color(0xFF181824),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
            style: const TextStyle(color: Colors.white),
          ),
          const SizedBox(height: 12),
          TextFormField(
            decoration: InputDecoration(
              labelText: "Price (OmniCredits)",
              labelStyle: const TextStyle(color: Colors.white60),
              filled: true,
              fillColor: const Color(0xFF181824),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
            style: const TextStyle(color: Colors.white),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.cyanAccent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text("🚀 Asset submitted! WASM Sandbox audit in progress..."),
                    backgroundColor: Colors.cyanAccent,
                  ),
                );
              },
              icon: const Icon(Icons.cloud_upload_outlined, color: Colors.black),
              label: const Text("Upload glTF / PNG Socket Package", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}
