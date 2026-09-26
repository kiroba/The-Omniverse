/// ============================================================================
/// THE CONTINUUM: QoL FEATURE UI TEMPLATES STAGING SCAFFOLD
/// Target Framework: Flutter / Dart (Mobile & PWA Web)
/// Module: `com.omniverse.continuum.ui.templates`
/// Tag Framework: `#qol`
/// ============================================================================
/// This file stages UI templates for ALL 5 Continuum QoL features:
/// 1. Q1: Multi-Perspective Mesh Fusion (`#mesh_fusion`)
/// 2. Q2: Edge Pre-Cognition & Living Offline Feed (`#edge_precog`)
/// 3. Q2: Threshold Time-Vault Capsules (`#time_vault`)
/// 4. Q3: Zero-Trust Spatial Holographic Anchors (`#spatial_anchor`)
/// 5. Q4: Interactive Branching Continuum Stories (`#branching_story`)
/// ============================================================================

import 'package:flutter/material.dart';

// ============================================================================
// DATA MODELS & ENUMS
// ============================================================================

enum ContinuumFeatureType {
  meshFusion,
  edgePreCognition,
  timeVault,
  spatialAnchor,
  branchingStory,
}

class PerspectiveAngle {
  final String id;
  final String label;
  final String creatorHandle;
  final String streamUrl;
  final bool isHardwareAttested;

  PerspectiveAngle({
    required this.id,
    required this.label,
    required this.creatorHandle,
    required this.streamUrl,
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
// MAIN CONTINUUM CARD STAGING WIDGET
// ============================================================================

class ContinuumCardContainer extends StatelessWidget {
  final ContinuumFeatureType featureType;
  final List<String> tags;
  final Widget child;

  const ContinuumCardContainer({
    Key? key,
    required this.featureType,
    required this.tags,
    required this.child,
  }) : super(key: key);

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
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF121824),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _getBadgeColor().withOpacity(0.4), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: _getBadgeColor().withOpacity(0.1),
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
                    color: _getBadgeColor().withOpacity(0.2),
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
                      color: Colors.white.withOpacity(0.6),
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
// TEMPLATE 1: MULTI-PERSPECTIVE MESH FUSION TEMPLATE
// ============================================================================

class ContinuumMeshFusionTemplate extends StatefulWidget {
  final String title;
  final List<PerspectiveAngle> perspectives;

  const ContinuumMeshFusionTemplate({
    Key? key,
    required this.title,
    required this.perspectives,
  }) : super(key: key);

  @override
  _ContinuumMeshFusionTemplateState createState() => _ContinuumMeshFusionTemplateState();
}

class _ContinuumMeshFusionTemplateState extends State<ContinuumMeshFusionTemplate> {
  int _activeAngleIndex = 0;

  @override
  Widget build(BuildContext context) {
    final activeAngle = widget.perspectives[_activeAngleIndex];

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
          // Video Viewport Frame
          Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white24),
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
                        "Rendering Angle: ${activeAngle.label}",
                        style: const TextStyle(color: Colors.white70, fontSize: 13),
                      ),
                      Text(
                        "Camera Host: ${activeAngle.creatorHandle}",
                        style: const TextStyle(color: Color(0xFF00FFCC), fontSize: 12),
                      ),
                    ],
                  ),
                ),
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF00FFCC)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.verified, color: Color(0xFF00FFCC), size: 14),
                        const SizedBox(width: 4),
                        Text(
                          "${widget.perspectives.length} Fused Angles",
                          style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Angle Switcher Selector
          const Text(
            "SWITCH CAMERA PERSPECTIVE:",
            style: TextStyle(color: Colors.white54, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.0),
          ),
          const SizedBox(height: 6),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List.generate(widget.perspectives.length, (index) {
                final isSelected = index == _activeAngleIndex;
                final p = widget.perspectives[index];
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
    Key? key,
    required this.draftTitle,
    required this.lastSavedTime,
    required this.pendingOutboxEvents,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.edgePreCognition,
      tags: const ["#qol", "#offline_draft", "#edge_precog"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.offline_pin, color: Color(0xFFFFB703), size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  draftTitle,
                  style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF1A2232),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Local SQLite WAL Outbox:", style: TextStyle(color: Colors.white54, fontSize: 11)),
                    Text(
                      "$pendingOutboxEvents Event(s) Pending Mesh Sync",
                      style: const TextStyle(color: Color(0xFFFFB703), fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.sync, size: 14, color: Colors.black),
                  label: const Text("Sync Now", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFFB703),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "Last saved to phone memory: $lastSavedTime",
            style: const TextStyle(color: Colors.white38, fontSize: 10),
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
  final String unlockCondition;
  final double progressPercent;
  final String remainingTime;

  const ContinuumTimeVaultTemplate({
    Key? key,
    required this.vaultTitle,
    required this.unlockCondition,
    required this.progressPercent,
    required this.remainingTime,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.timeVault,
      tags: const ["#qol", "#time_vault", "#shamir_lock"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lock_clock, color: Color(0xFF7209B7), size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  vaultTitle,
                  style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            "UNLOCK CONDITION: $unlockCondition",
            style: const TextStyle(color: Color(0xFF9D4EDD), fontSize: 11, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: progressPercent,
              minHeight: 10,
              backgroundColor: const Color(0xFF1A2232),
              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF7209B7)),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "Threshold Key Shares: ${(progressPercent * 5).toInt()}/5 Verified",
                style: const TextStyle(color: Colors.white54, fontSize: 11),
              ),
              Text(
                remainingTime,
                style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// TEMPLATE 4: ZERO-TRUST SPATIAL HOLOGRAPHIC ANCHOR TEMPLATE
// ============================================================================

class ContinuumSpatialAnchorTemplate extends StatelessWidget {
  final String anchorName;
  final String locationTag;
  final String spatialHash;

  const ContinuumSpatialAnchorTemplate({
    Key? key,
    required this.anchorName,
    required this.locationTag,
    required this.spatialHash,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.spatialAnchor,
      tags: const ["#qol", "#spatial_anchor", "#zero_gps_ar"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.view_in_ar_rounded, color: Color(0xFF4CC9F0), size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  anchorName,
                  style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            "LOCATION: $locationTag (No GPS Tracking)",
            style: const TextStyle(color: Color(0xFF4CC9F0), fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF1A2232),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF4CC9F0).withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.qr_code_scanner, color: Color(0xFF4CC9F0), size: 28),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("LiDAR Camera Feature Match:", style: TextStyle(color: Colors.white54, fontSize: 10)),
                      Text(
                        spatialHash,
                        style: const TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace'),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                ElevatedButton(
                  onPressed: () {},
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF4CC9F0)),
                  child: const Text("View AR", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11)),
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
// TEMPLATE 5: INTERACTIVE BRANCHING CONTINUUM STORY TEMPLATE
// ============================================================================

class ContinuumBranchingStoryTemplate extends StatelessWidget {
  final String storyTitle;
  final String currentPrompt;
  final List<BranchOption> options;
  final String timeRemaining;

  const ContinuumBranchingStoryTemplate({
    Key? key,
    required this.storyTitle,
    required this.currentPrompt,
    required this.options,
    required this.timeRemaining,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ContinuumCardContainer(
      featureType: ContinuumFeatureType.branchingStory,
      tags: const ["#qol", "#branching_story", "#p2p_consensus"],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  storyTitle,
                  style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFF72585).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFF72585)),
                ),
                child: Text(
                  "VOTING: $timeRemaining",
                  style: const TextStyle(color: Color(0xFFF72585), fontWeight: FontWeight.bold, fontSize: 10),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            currentPrompt,
            style: const TextStyle(color: Colors.white70, fontSize: 13, fontStyle: FontStyle.italic),
          ),
          const SizedBox(height: 12),
          Column(
            children: options.map((opt) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A2232),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.white12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            opt.title,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12),
                          ),
                          Text(
                            "${(opt.percentage * 100).toInt()}% (${opt.voteCount} votes)",
                            style: const TextStyle(color: Color(0xFFF72585), fontWeight: FontWeight.bold, fontSize: 11),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: opt.percentage,
                          minHeight: 6,
                          backgroundColor: Colors.white10,
                          valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFFF72585)),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// STAGING DEMO PAGE (COMPLETE FEED INTEGRATION)
// ============================================================================

class ContinuumFeedStagingPage extends StatelessWidget {
  const ContinuumFeedStagingPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: AppBar(
        title: const Text("THE CONTINUUM (#qol Feed)"),
        backgroundColor: const Color(0xFF121824),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list_rounded, color: Color(0xFF00FFCC)),
            onPressed: () {},
          ),
        ],
      ),
      body: ListView(
        children: [
          // 1. Mesh Fusion Template Staging
          ContinuumMeshFusionTemplate(
            title: "Live Concert Stage - Multi-Angle Mesh",
            perspectives: [
              PerspectiveAngle(id: "p1", label: "Front Stage (Alice)", creatorHandle: "@alice", streamUrl: "webrtc://..."),
              PerspectiveAngle(id: "p2", label: "Stage Right (Bob)", creatorHandle: "@bob", streamUrl: "webrtc://..."),
              PerspectiveAngle(id: "p3", label: "Crowd Center (Charlie)", creatorHandle: "@charlie", streamUrl: "webrtc://..."),
            ],
          ),

          // 2. Offline Pre-Cog Template Staging
          const ContinuumOfflinePrecogTemplate(
            draftTitle: "Continuum Story Draft: Decentralized AI Thoughts",
            lastSavedTime: "2 mins ago (Offline Cache)",
            pendingOutboxEvents: 3,
          ),

          // 3. Time Vault Template Staging
          const ContinuumTimeVaultTemplate(
            vaultTitle: "New Year's Eve 2027 Time-Capsule Memory",
            unlockCondition: "12:00 AM Jan 1, 2027 OR 1,000 Mesh Peers",
            progressPercent: 0.60,
            remainingTime: "3 Threshold Shares Remaining",
          ),

          // 4. Spatial Anchor Template Staging
          const ContinuumSpatialAnchorTemplate(
            anchorName: "3D Holographic Note on Library Table #4",
            locationTag: "University Science Quad",
            spatialHash: "sp_anchor_9a8f7c1d2e3b4a5f6",
          ),

          // 5. Branching Story Template Staging
          ContinuumBranchingStoryTemplate(
            storyTitle: "The Omniverse Quest: Episode 1",
            currentPrompt: "The team approaches the cryptographic portal. Which path do we take?",
            timeRemaining: "00:42s",
            options: [
              BranchOption(optionId: "opt_1", title: "Path A: Enter the High-Bandwidth Sub-Enclave", voteCount: 142, percentage: 0.68),
              BranchOption(optionId: "opt_2", title: "Path B: Investigate the P2P Mesh Anomaly", voteCount: 67, percentage: 0.32),
            ],
          ),
        ],
      ),
    );
  }
}
