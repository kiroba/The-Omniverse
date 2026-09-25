#!/usr/bin/env bash
# ==============================================================================
# THE OMNIVERSE & THE KICKBACK - AUTOMATIC REPOSITORY FILE ORGANIZER
# Run this inside Termux or your repository root folder to automatically create
# the exact folder structure and sort all project files into their directories.
# ==============================================================================

echo "🚀 [1/3] Creating directory hierarchy..."
mkdir -p core/engines
mkdir -p mobile/lib
mkdir -p web
mkdir -p config
mkdir -p docs

echo "📁 [2/3] Sorting files into designated directories..."

# Core Python Engines
for file in \
    zero_dep_master_runner.py \
    zero_dep_mainnet_cutover_suite.py \
    zero_dep_role_entitlement_engine.py \
    zero_dep_p2p_milestone_consensus_engine.py \
    zero_dep_websocket_pubsub_bridge.py \
    zero_dep_p2p_bootnode_cluster.py \
    zero_dep_continuity_social_import_engine.py \
    lpe_idle_plaza_engine.py \
    lpe_p2p_jail_quarantine_engine.py \
    lpe_reputation_aura_engine.py \
    spatial_anchor_engine.py \
    time_vault_engine.py \
    branching_story_consensus_engine.py \
    kickback_gift_and_credit_engine.py \
    kickback_payout_and_anti_fraud_engine.py \
    hybrid_storage_engine.py \
    disaster_recovery_validator.py \
    public_accountability_engine.py \
    mainnet_cutover_suite.py \
    role_entitlement_and_milestone_engine.py \
    p2p_milestone_consensus_engine.py \
    omniverse_websocket_pubsub_bridge.py \
    p2p_bootnode_cluster.py \
    continuity_social_import_engine.py
do
    if [ -f "$file" ]; then
        mv "$file" core/engines/
        echo "  ├─ Moved $file -> core/engines/"
    fi
done

# Mobile Flutter UI Components
for file in \
    continuum_ui_templates_staging.dart \
    continuum_ui_templates_staging-v2.dart \
    kickback_wallet_and_store_ui.dart \
    kickback_creator_studio_ui.dart \
    kickback_storefront_mini_app_ui.dart \
    omni_hub_gateway_launcher_ui.dart \
    flutter_live_stream_reaction_overlay.dart
do
    if [ -f "$file" ]; then
        mv "$file" mobile/lib/
        echo "  ├─ Moved $file -> mobile/lib/"
    fi
done

# Web PWA Assets
for file in \
    kickback_pwa_manifest.json \
    kickback_pwa_service_worker.js
do
    if [ -f "$file" ]; then
        mv "$file" web/
        echo "  ├─ Moved $file -> web/"
    fi
done

# Config Files
for file in \
    p2p_seed_nodes.json \
    kickback_tier_payment_config.py
do
    if [ -f "$file" ]; then
        mv "$file" config/
        echo "  ├─ Moved $file -> config/"
    fi
done

# Documentation & Build Guides
for file in \
    dev_blog_changelog*.md \
    mobile_assembly_and_build_guide*.md \
    mobile_one_click_setup.sh \
    README*.md \
    SECURITY*.md \
    launch_release_notes.md
do
    if [ -f "$file" ]; then
        mv "$file" docs/
        echo "  ├─ Moved $file -> docs/"
    fi
done

echo ""
echo "=============================================================================="
echo "🎉 REPOSITORY STRUCTURE SUCCESSFULLY ORGANIZED!"
echo "=============================================================================="
