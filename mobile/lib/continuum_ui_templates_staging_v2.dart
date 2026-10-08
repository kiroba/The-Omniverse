/// ============================================================================
/// THE CONTINUUM & LPE: ALL-IN-ONE QoL FEATURE UI TEMPLATES STAGING SCAFFOLD
/// Target Framework: Flutter / Dart (Mobile & PWA Web)
/// Module: `com.omniverse.continuum.ui.templates`
/// Tag Framework: `#qol`
/// ============================================================================
/// Includes ALL 7 Staged UI Components:
/// 1. Multi-Perspective Mesh Fusion (`#mesh_fusion`) + Extended Discovery
/// 2. Edge Pre-Cognition & Living Offline Feed (`#edge_precog`)
/// 3. Threshold Time-Vault Capsules (`#time_vault`)
/// 4. Zero-Trust Spatial Holographic Anchors (`#spatial_anchor`)
/// 5. Interactive Branching Continuum Stories (`#branching_story`)
/// 6. LPE Idle World Plaza & Progression Hub (`#lpe_plaza`)
/// 7. P2P Jail & Rehabilitation Sub-Enclave View (`/cohort_jail_quarantine`)
/// ============================================================================
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;

// ============================================================================
// DATA MODELS & ENUMS
// ============================================================================

enum ContinuumFeatureType {
  meshFusion,
  edgePreCognition,
  timeVault,
  spatialAnchor,
  branchingStory,
  idlePlaza,
  p2pJail,
}

class PerspectiveAngle {
  final String id;
  final String label;
  final String creatorHandle;
  final String streamUrl;
  final bool isFriend;
  final bool isHardwareAttested;

  PerspectiveAngle({
    required this.id,
    required this.label,
    required this.creatorHandle,
    required this.streamUrl,
    this.isFriend = true,
    this.isHardwareAttested = true,
  });
}

class BranchOption {
  final String optionId;
  final String title;
  final int voteCount;
  final double percentage;

  BranchOption({
    required this.optionId,
    required this.title,
    required this.voteCount,
    required this.percentage,
  });
}

// ============================================================================
// MAIN CONTINUUM CARD STAGING CONTAINER
// ============================================================================

class ContinuumCardContainer extends StatelessWidget {
  final ContinuumFeatureType featureType;
  final List<String> tags;
  final Widget child;

  const ContinuumCardContainer({
    super.key,
    required this.featureType,
    required this.tags,
    required this.child,
  });

  Color _getBadgeColor() {
    switch (featureType) {
      case ContinuumFeatureType.meshFusion:
        return const Color(0xFF00FFCC); // Cyan
      case ContinuumFeatureType.edgePreCognition:
        return const Color(0xFFFFB703); // Amber
      case ContinuumFeatureType.timeVault:
        return const Color(0xFF7209B7); // Purple
      case ContinuumFeatureType.spatialAnchor:
        return const Color(0xFF4CC9F0); // Light Blue
      case ContinuumFeatureType.branchingStory:
        return const Color(0xFFF72585); // Pink/Magenta
      case ContinuumFeatureType.idlePlaza:
        return const Color(0xFF3A86EF); // Electric Blue
      case ContinuumFeatureType.p2pJail:
        return const Color(0xFFFF0000); // Red
    }
  }

  String _getFeatureLabel() {
    switch (featureType) {
      case ContinuumFeatureType.meshFusion:
        return "MESH FUSION";
      case ContinuumFeatureType.edgePreCognition:
        return "OFFLINE PRE-COG";
      case ContinuumFeatureType.timeVault:
        return "TIME-VAULT";
      case ContinuumFeatureType.spatialAnchor:
        return "SPATIAL ANCHOR";
      case ContinuumFeatureType.branchingStory:
        return "BRANCHING STORY";
      case ContinuumFeatureType.idlePlaza:
        return "IDLE PLAZA";
      case ContinuumFeatureType.p2pJail:
        return "P2P JAIL ENCLAVE";
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF121824),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _getBadgeColor().withValues(alpha: 0.4), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: _getBadgeColor().withValues(alpha: 0.1),
            blurRadius: 12,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Bar
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getBadgeColor().withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: _getBadgeColor(), width: 1),
                  ),
                  child: Text(
                    _getFeatureLabel(),
                    style: TextStyle(
                      color: _getBadgeColor(),
                      fontWeight: FontWeight.bold,
                      fontSize: 11,
                      letterSpacing: 1.1,
                    ),
                  ),
                ),
                Wrap(
                  spacing: 6,
                  children: tags.map((t) => Text(
                    t,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  )).toList(),
                ),
              ],
            ),
          ),
          const Divider(color: Colors.white10, height: 1),
          // Content Body
          Padding(
            padding: const EdgeInsets.all(14.0),
            child: child,
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 1: MULTI-PERSPECTIVE MESH FUSION & EXTENDED DISCOVERY
// ============================================================================

class ContinuumMeshFusionTemplate extends StatefulWidget {
  final String title;
  final List<PerspectiveAngle> perspectives;

  const ContinuumMeshFusionTemplate({
    super.key,
    required this.title,
    required this.perspectives,
  });

  @override
  State<ContinuumMeshFusionTemplate> createState() =>
      _ContinuumMeshFusionTemplateState();
}

class _ContinuumMeshFusionTemplateState extends State<ContinuumMeshFusionTemplate> {
  int _activeAngleIndex = 0;
  bool _isExtendedDiscoveryExpanded = false;

  @override
  Widget build(BuildContext context) {
    final friendPerspectives = widget.perspectives.where((p) => p.isFriend).toList();
    final externalPerspectives = widget.perspectives.where((p) => !p.isFriend).toList();

    final visiblePerspectives = _isExtendedDiscoveryExpanded
        ? widget.perspectives
        : (friendPerspectives.isNotEmpty ? friendPerspectives : widget.perspectives);

    final activeAngle = visiblePerspectives[_activeAngleIndex < visiblePerspectives.length ? _activeAngleIndex : 0];
    final bool isAtLastFriend = _activeAngleIndex >= (friendPerspectives.length - 1);
    final bool shouldShowPrompt = isAtLastFriend && !_isExtendedDiscoveryExpanded && externalPerspectives.isNotEmpty;

    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.meshFusion,
      tags: const ["#qol", "#continuum", "#mesh_fusion"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.title,
            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF00FFCC).withValues(alpha: 0.5)),
            ),
            child: Stack(
              children: [
                Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.videocam_rounded, color: Color(0xFF00FFCC), size: 48),
                      const SizedBox(height: 6),
                      Text(
                        "Angle: ${activeAngle.label}",
                        style: const TextStyle(color: Colors.white70, fontSize: 13),
                      ),
                      Text(
                        "Host: ${activeAngle.creatorHandle} ${activeAngle.isFriend ? '(Friend)' : '[NEARBY PEER]'}",
                        style: TextStyle(
                          color: activeAngle.isFriend ? const Color(0xFF00FFCC) : Colors.purpleAccent,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                ...List.generate(visiblePerspectives.length, (index) {
                  final isSelected = index == _activeAngleIndex;
                  final p = visiblePerspectives[index];
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: ChoiceChip(
                      label: Text(p.label),
                      selected: isSelected,
                      selectedColor: const Color(0xFF00FFCC),
                      backgroundColor: const Color(0xFF1A2232),
                      labelStyle: TextStyle(
                        color: isSelected ? Colors.black : Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                      onSelected: (bool selected) {
                        if (selected) {
                          setState(() => _activeAngleIndex = index);
                        }
                      },
                    ),
                  );
                }),
                if (shouldShowPrompt)
                  Padding(
                    padding: const EdgeInsets.only(left: 4.0),
                    child: ActionChip(
                      avatar: const Icon(Icons.explore_rounded, color: Colors.purpleAccent, size: 16),
                      label: Text(
                        "See ${externalPerspectives.length} More Similar Streams",
                        style: const TextStyle(color: Colors.purpleAccent, fontWeight: FontWeight.bold, fontSize: 11),
                      ),
                      backgroundColor: Colors.purpleAccent.withValues(alpha: 0.15),
                      side: const BorderSide(color: Colors.purpleAccent),
                      onPressed: () {
                        setState(() {
                          _isExtendedDiscoveryExpanded = true;
                        });
                      },
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 2: EDGE PRE-COGNITION & OFFLINE DRAFT TEMPLATE
// ============================================================================

class ContinuumOfflinePrecogTemplate extends StatelessWidget {
  final String draftTitle;
  final String lastSavedTime;
  final int pendingOutboxEvents;

  const ContinuumOfflinePrecogTemplate({
    super.key,
    required this.draftTitle,
    required this.lastSavedTime,
    required this.pendingOutboxEvents,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.edgePreCognition,
      tags: const ["#qol", "#continuum", "#edge_precog"],
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(draftTitle, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Text("Saved: $lastSavedTime (SQLite WAL Outbox)", style: const TextStyle(color: Colors.white54, fontSize: 11)),
            ],
          ),
          ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.sync_rounded, size: 16),
            label: Text("$pendingOutboxEvents Pending"),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFFFB703), foregroundColor: Colors.black),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 3: THRESHOLD TIME-VAULT TEMPLATE
// ============================================================================

class ContinuumTimeVaultTemplate extends StatelessWidget {
  final String vaultTitle;
  final int sharesCollected;
  final int sharesRequired;
  final String unlockMilestoneText;

  const ContinuumTimeVaultTemplate({
    super.key,
    required this.vaultTitle,
    required this.sharesCollected,
    required this.sharesRequired,
    required this.unlockMilestoneText,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.timeVault,
      tags: const ["#qol", "#continuum", "#time_vault"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(vaultTitle, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: sharesCollected / sharesRequired,
            backgroundColor: Colors.white10,
            valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF7209B7)),
          ),
          const SizedBox(height: 6),
          Text("Key Shares: $sharesCollected/$sharesRequired | $unlockMilestoneText", style: const TextStyle(color: Color(0xFF7209B7), fontSize: 11)),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 4: ZERO-TRUST SPATIAL HOLOGRAPHIC ANCHOR TEMPLATE
// ============================================================================

class ContinuumSpatialAnchorTemplate extends StatelessWidget {
  final String locationTitle;
  final String lidarFeatureHash;

  const ContinuumSpatialAnchorTemplate({
    super.key,
    required this.locationTitle,
    required this.lidarFeatureHash,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.spatialAnchor,
      tags: const ["#qol", "#continuum", "#spatial_anchor"],
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(locationTitle, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Text("LiDAR Hash: $lidarFeatureHash (Zero-GPS)", style: const TextStyle(color: Colors.white54, fontSize: 11)),
            ],
          ),
          OutlinedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.view_in_ar_rounded, size: 16),
            label: const Text("View AR"),
            style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF4CC9F0), side: const BorderSide(color: Color(0xFF4CC9F0))),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 5: INTERACTIVE BRANCHING CONTINUUM STORY TEMPLATE
// ============================================================================

class ContinuumBranchingStoryTemplate extends StatelessWidget {
  final String questionTitle;
  final List<BranchOption> options;

  const ContinuumBranchingStoryTemplate({
    super.key,
    required this.questionTitle,
    required this.options,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.branchingStory,
      tags: const ["#qol", "#continuum", "#branching_story"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(questionTitle, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          ...options.map((opt) => Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(opt.title, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                    Text("${opt.percentage}% (${opt.voteCount} votes)", style: const TextStyle(color: Color(0xFFF72585), fontSize: 11, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 4),
                LinearProgressIndicator(
                  value: opt.percentage / 100.0,
                  backgroundColor: Colors.white10,
                  valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFFF72585)),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 6: LPE IDLE WORLD PLAZA WIDGET (#lpe_plaza)
// ============================================================================

class LpeIdlePlazaWidget extends StatelessWidget {
  final String mainUserHandle;
  final String activeAction;
  final int totalPlazaAvatars;
  final int totalXpAccrued;

  const LpeIdlePlazaWidget({
    super.key,
    required this.mainUserHandle,
    required this.activeAction,
    required this.totalPlazaAvatars,
    required this.totalXpAccrued,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.idlePlaza,
      tags: const ["#qol", "#lpe_plaza", "#idle_xp"],
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Plaza Center: $mainUserHandle", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Text("Action: $activeAction | $totalPlazaAvatars Avatars Nearby", style: const TextStyle(color: Colors.white54, fontSize: 11)),
            ],
          ),
          Chip(
            avatar: const Icon(Icons.bolt, color: Color(0xFF3A86EF), size: 16),
            label: Text("+$totalXpAccrued XP", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
            backgroundColor: const Color(0xFF3A86EF).withValues(alpha: 0.2),
            side: const BorderSide(color: Color(0xFF3A86EF)),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 7: P2P JAIL & REHABILITATION SUB-ENCLAVE VIEW (/cohort_jail_quarantine)
// ============================================================================

class LpeJailQuarantineView extends StatelessWidget {
  final String jailedHandle;
  final String quarantineReason;
  final double paroleProgressPercent;

  const LpeJailQuarantineView({
    super.key,
    required this.jailedHandle,
    required this.quarantineReason,
    required this.paroleProgressPercent,
  });

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.p2pJail,
      tags: const ["#qol", "#p2p_jail", "#quarantine"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.gavel_rounded, color: Colors.redAccent, size: 18),
              const SizedBox(width: 6),
              Text("Quarantined Node: $jailedHandle", style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 6),
          Text("Reason: $quarantineReason", style: const TextStyle(color: Colors.white54, fontSize: 11)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Parole Rehabilitation Progress:", style: TextStyle(color: Colors.white70, fontSize: 11)),
              Text("${(paroleProgressPercent * 100).toInt()}%", style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: paroleProgressPercent,
            backgroundColor: Colors.white10,
            valueColor: const AlwaysStoppedAnimation<Color>(Colors.redAccent),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// DYNAMIC CONTINUUM FEED STAGING PAGE (PRODUCTION-READY SQLITE WAL INTEGRATION)
// ============================================================================

class ContinuumFeedStagingPage extends StatefulWidget {
  const ContinuumFeedStagingPage({super.key});

  @override
  State<ContinuumFeedStagingPage> createState() =>
      _ContinuumFeedStagingPageState();
}

class _ContinuumFeedStagingPageState extends State<ContinuumFeedStagingPage> {
  Database? _db;
  int _outboxCount = 0;
  String _activeHandle = "@citizen";

  @override
  void initState() {
    super.initState();
    _connectDatabase();
  }

  Future<void> _connectDatabase() async {
    final dbPath = p.join(await getDatabasesPath(), 'omni_hub_immutable.db');
    _db = await openDatabase(dbPath);
    
    final identities = await _db?.query('citizen_identity', limit: 1);
    if (identities != null && identities.isNotEmpty) {
      _activeHandle = identities.first['handle'] as String? ?? "@citizen";
    }

    final events = await _db?.rawQuery("SELECT COUNT(*) as cnt FROM event_log");
    if (events != null && events.isNotEmpty) {
      _outboxCount = Sqflite.firstIntValue(events) ?? 0;
    }

    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: AppBar(
        title: const Text("The Continuum Meta-Story Feed (#qol)"),
        backgroundColor: const Color(0xFF121824),
      ),
      body: ListView(
        children: [
          ContinuumMeshFusionTemplate(
            title: "Live Mainstage Stream",
            perspectives: [
              PerspectiveAngle(id: "p1", label: "Front Stage", creatorHandle: _activeHandle, streamUrl: "p2p://stream_01", isFriend: true),
              PerspectiveAngle(id: "p2", label: "Peer Stream", creatorHandle: "@mesh_peer", streamUrl: "p2p://stream_02", isFriend: false),
            ],
          ),
          ContinuumOfflinePrecogTemplate(
            draftTitle: "Local Feed State (SQLite WAL Outbox)",
            lastSavedTime: "Live Sync",
            pendingOutboxEvents: _outboxCount,
          ),
          const ContinuumTimeVaultTemplate(
            vaultTitle: "Community Milestone Vault",
            sharesCollected: 3,
            sharesRequired: 5,
            unlockMilestoneText: "Unlocks via Local Key Threshold",
          ),
          const ContinuumSpatialAnchorTemplate(
            locationTitle: "Local Spatial Anchor",
            lidarFeatureHash: "spa_anchor_active",
          ),
          ContinuumBranchingStoryTemplate(
            questionTitle: "Current Swarm Vote",
            options: [
              BranchOption(optionId: "o1", title: "Option Alpha", voteCount: 84, percentage: 60.0),
              BranchOption(optionId: "o2", title: "Option Beta", voteCount: 56, percentage: 40.0),
            ],
          ),
          LpeIdlePlazaWidget(
            mainUserHandle: _activeHandle,
            activeAction: "P2P Mesh Node Active",
            totalPlazaAvatars: 1,
            totalXpAccrued: 100,
          ),
        ],
      ),
    );
  }
}
