// ============================================================================
// THE KICKBACK: COIN STOREFRONT (PAYMENTS NOT LIVE YET)
// ============================================================================
// Honest state: there is no Stripe account or payment backend yet, so nothing
// here charges money, simulates a payment, or adds coins. The tiers are shown
// for layout only, every buy button is disabled, and the screen says
// "Payments coming soon". Real checkout comes in a separate PR once a payment
// provider is chosen and set up.
//
// Earlier versions faked a 1-tap "biometric" Apple/Google Pay checkout with a
// timer and added coins to a hardcoded balance; that was removed.
// ============================================================================

import "package:flutter/material.dart";

void main() {
  runApp(const SeamlessCheckoutApp());
}

class SeamlessCheckoutApp extends StatelessWidget {
  const SeamlessCheckoutApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "KickBack Coins",
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0D1117),
        primaryColor: const Color(0xFF00FFCC),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00FFCC),
          secondary: Color(0xFF7209B7),
          surface: Color(0xFF161B22),
        ),
      ),
      home: const KickbackStorefrontScreen(),
    );
  }
}

/// Coin tiers, display only. Buying is disabled until real checkout exists.
class KickbackStorefrontScreen extends StatelessWidget {
  const KickbackStorefrontScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("KickBack Coins", style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF161B22),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF3A2A00),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFFC107)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.schedule, color: Color(0xFFFFC107)),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "Payments coming soon. Coins can't be bought yet, and you have no coin balance.",
                      style: TextStyle(color: Color(0xFFFFE082), fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              "Coin tiers (preview)",
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 20),
            _buildTierCard(title: "Starter Pack", coins: 500, price: 1.99, icon: Icons.flash_on, accentColor: Colors.cyanAccent),
            const SizedBox(height: 12),
            _buildTierCard(title: "Popular Bundle", coins: 1500, price: 4.99, icon: Icons.star, accentColor: const Color(0xFF00FFCC)),
            const SizedBox(height: 12),
            _buildTierCard(title: "Pro Creator Chest", coins: 5000, price: 14.99, icon: Icons.workspace_premium, accentColor: Colors.purpleAccent),
          ],
        ),
      ),
    );
  }

  Widget _buildTierCard({
    required String title,
    required int coins,
    required double price,
    required IconData icon,
    required Color accentColor,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF161B22),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white10),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        leading: CircleAvatar(
          backgroundColor: accentColor.withOpacity(0.2),
          child: Icon(icon, color: accentColor),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        subtitle: Text("$coins coins • \$${price.toStringAsFixed(2)}", style: TextStyle(color: accentColor)),
        trailing: const ElevatedButton(
          onPressed: null, // disabled: no payment backend yet
          child: Text("Coming soon"),
        ),
      ),
    );
  }

}
