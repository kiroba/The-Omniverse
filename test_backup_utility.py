import sys
import os
import time
import json

sys.path.append("/workspace/artifacts")
sys.path.append("/workspace/scratch")

from layer2_p2p_crdt_engine_v2 import LocalNodeStorage
from kickback_backup_utility import KickBackBackupUtility

def run_backup_tests():
    print("=========================================================================")
    print("  OFFLINE BACKUP & REHYDRATION UTILITY VERIFICATION SUITE")
    print("=========================================================================\n")

    # 1. Initialize Source Node & Create Mock Data across Continuity-Engine, KickBack, OmniMind
    source_storage = LocalNodeStorage(node_id="source_backup_node")
    print("[-] Populating Source Node with Continuity, KickBack, and OmniMind events...")

    # Event 1: Continuity-Engine Profile Creation
    e1 = source_storage.append_local_event("USER_PROFILE_UPDATE", {
        "username": "Kiroba_Architect",
        "bio": "Building sovereign decentralized protocols.",
        "terms_accepted": True,
        "terms_version": "1.0.0"
    })

    # Event 2: KickBack Social Feed Post
    e2 = source_storage.append_local_event("NEWSFEED_POST", {
        "post_id": "post_kickback_001",
        "content": "Hello KickBack! This post is cryptographically backed up."
    })

    # Event 3: OmniMind System Maintenance Notice
    e3 = source_storage.append_local_event("SYSTEM_INFO_UPDATE", {
        "notice_id": "notice_001",
        "content": "System operational maintenance scheduled for 02:00 UTC."
    }, author_type="AI_AGENT")

    print(f"  • Source Node initialized with pubkey: {source_storage.pubkey_hex[:16]}...")
    print("  • Events created: USER_PROFILE_UPDATE, NEWSFEED_POST, SYSTEM_INFO_UPDATE")

    # 2. Export Backup Archive (.kickback-backup.tar.gz)
    backup_file_path = "/workspace/scratch/node_backup.kickback-backup.tar.gz"
    print(f"\n[-] Exporting backup to '{backup_file_path}'...")
    export_path = KickBackBackupUtility.export_backup(source_storage, backup_file_path)
    
    file_size_bytes = os.path.getsize(export_path)
    print(f"  • Backup File Created: {export_path} ({file_size_bytes} bytes)")
    print("[✓] Export completed successfully.")

    # 3. Initialize Fresh Target Node & Restore from Backup
    target_storage = LocalNodeStorage(node_id="fresh_restored_node")
    print("\n[-] Restoring backup into fresh Target Node...")
    
    success, restore_meta = KickBackBackupUtility.verify_and_restore_backup(export_path, target_storage)
    
    print(f"  • Restore Success = {success}")
    print(f"  • Restore Metadata: {json.dumps(restore_meta, indent=2)}")

    # Verify Target Storage Events
    target_events = target_storage.get_all_events()
    print(f"  • Target Node now contains {len(target_events)} rehydrated events.")

    assert success is True
    assert len(target_events) == 3
    assert restore_meta["summary"]["total_events"] == 3
    print("\n=========================================================================")
    print("  ALL OFFLINE BACKUP & REHYDRATION TESTS PASSED 100%!")
    print("=========================================================================\n")

if __name__ == "__main__":
    run_backup_tests()
