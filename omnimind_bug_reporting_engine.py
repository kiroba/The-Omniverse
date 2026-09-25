import hashlib
import hmac
import json
import time
from typing import Dict, Any, List, Optional

class OmniMindBugReportingEngine:
    """
    1-Way Bug Reporting Engine & Developer Console API with Scoped Role-Based Access Control (RBAC).
    
    Access Control Enforcement:
    - Item Creators / Merchants: Can ONLY see bug reports and diagnostics pertaining directly
      to their created items/worlds (matched via createdBy == creatorPubkey).
    - Master Platform Creator: Has unrestricted, full-scope access across all system reports,
      network telemetry, and platform-wide issues.
    """
    
    MASTER_CREATOR_PUBKEY = "ed25519_pk_master_platform_creator_001"
    
    def __init__(self):
        self.bug_database: Dict[str, Dict[str, Any]] = {}
        self.secret_key = b"omnimind_admin_dev_console_secret_2026"

    def submit_bug_report(
        self,
        user_peer_id: str,
        app_version: str,
        category: str,
        title: str,
        description: str,
        device_telemetry: Dict[str, Any],
        item_id: Optional[str] = None,
        item_creator_pubkey: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        1-Way Bug Submission: Ingests user report, strips PII, binds optional itemId & itemCreatorPubkey.
        Returns a 1-way receipt without conversational AI back-and-forth.
        """
        timestamp = int(time.time())
        raw_id = f"{user_peer_id}:{timestamp}:{title}"
        bug_id = f"bug_{hashlib.sha256(raw_id.encode('utf-8')).hexdigest()[:12]}"
        
        # Anonymize user peer ID for bug tracking privacy
        anonymized_reporter = f"peer_anon_{hashlib.sha256(user_peer_id.encode('utf-8')).hexdigest()[:8]}"
        
        bug_entry = {
            "bugId": bug_id,
            "reporterHash": anonymized_reporter,
            "appVersion": app_version,
            "category": category,  # 'P2P_SYNC', 'UI_GLITCH', 'MERCHANT_ITEM', 'WORLD_ROOM', 'CRASH'
            "title": title,
            "description": description,
            "itemId": item_id,
            "itemCreatorPubkey": item_creator_pubkey,
            "deviceTelemetry": device_telemetry,
            "stackTrace": stack_trace or "N/A",
            "timestamp": timestamp,
            "status": "QUEUED",  # QUEUED, INVESTIGATING, PATCH_QUEUED, RESOLVED
            "developerNotes": []
        }
        
        # Signature for admin integrity
        signature = hmac.new(
            self.secret_key,
            json.dumps(bug_entry, sort_keys=True).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        bug_entry["signature"] = f"sig_dev_{signature[:16]}"
        
        # Store in OmniMind Bug Database
        self.bug_database[bug_id] = bug_entry
        
        # 1-Way Receipt
        return {
            "receiptStatus": "BUG_REPORT_RECEIVED",
            "bugId": bug_id,
            "message": "Bug report logged into OmniMind. Thank you for making The Omniverse better."
        }

    def query_bug_reports_scoped(
        self,
        requester_pubkey: str,
        is_master_creator: bool = False,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scoped Role-Based Access Query:
        - Master Creator (is_master_creator=True or requester_pubkey == MASTER_CREATOR_PUBKEY):
          Returns ALL bug reports across all categories and items.
        - Item Creators (3rd-party merchants/world creators):
          Returns ONLY bug reports where itemCreatorPubkey == requester_pubkey.
        """
        results = []
        is_master = is_master_creator or (requester_pubkey == self.MASTER_CREATOR_PUBKEY)
        
        for bug in self.bug_database.values():
            # Category Filter
            if category_filter and bug["category"] != category_filter:
                continue
                
            # Scoped Access Check
            if not is_master:
                # Regular creators only see reports pertaining to their created items
                if bug.get("itemCreatorPubkey") != requester_pubkey:
                    continue
            
            # Formatted summary for dashboard
            results.append({
                "bugId": bug["bugId"],
                "title": bug["title"],
                "category": bug["category"],
                "itemId": bug.get("itemId"),
                "itemCreatorPubkey": bug.get("itemCreatorPubkey"),
                "status": bug["status"],
                "timestamp": bug["timestamp"],
                "appVersion": bug["appVersion"],
                "isMasterView": is_master
            })
            
        return results

    def developer_console_api(
        self,
        requester_pubkey: str,
        action: str,
        bug_id: str,
        new_status: Optional[str] = None,
        note: Optional[str] = None,
        is_master_creator: bool = False
    ) -> Dict[str, Any]:
        """
        Out-of-Band Developer Console API with Scoped Authorization.
        """
        if bug_id not in self.bug_database:
            return {"status": "ERROR", "message": f"Bug ID '{bug_id}' not found."}
            
        bug = self.bug_database[bug_id]
        is_master = is_master_creator or (requester_pubkey == self.MASTER_CREATOR_PUBKEY)
        
        # Access Verification
        if not is_master and bug.get("itemCreatorPubkey") != requester_pubkey:
            return {
                "status": "FORBIDDEN",
                "message": "ACCESS DENIED: Creators can only access bug reports pertaining directly to their created items."
            }
            
        if action == "GET_FULL_DIAGNOSTICS":
            return {"status": "SUCCESS", "bugDetails": bug, "isMasterView": is_master}
            
        elif action == "UPDATE_STATUS":
            if new_status in ["INVESTIGATING", "PATCH_QUEUED", "RESOLVED"]:
                bug["status"] = new_status
                if note:
                    bug["developerNotes"].append({
                        "timestamp": int(time.time()),
                        "author": requester_pubkey,
                        "note": note
                    })
                return {"status": "SUCCESS", "bugId": bug_id, "updatedStatus": new_status}
            return {"status": "ERROR", "message": f"Invalid status '{new_status}'."}
            
        return {"status": "ERROR", "message": f"Unknown action '{action}'."}

if __name__ == "__main__":
    print("=================================================================")
    print(" OMNIMIND: SCOPED ACCESS BUG REPORTING & DEV CONSOLE SUITE TEST  ")
    print("=================================================================")
    
    engine = OmniMindBugReportingEngine()
    
    merchant_alice_pk = "ed25519_pk_merchant_alice_777"
    merchant_bob_pk = "ed25519_pk_merchant_bob_888"
    master_creator_pk = OmniMindBugReportingEngine.MASTER_CREATOR_PUBKEY
    
    # Report 1: Pertaining to Alice's 3D Visor Item
    r1 = engine.submit_bug_report(
        user_peer_id="peer_user_1",
        app_version="1.0.0-oct01",
        category="MERCHANT_ITEM",
        title="Neon Visor Clipping on Female Avatar",
        description="Visor mesh clips through forehead during wave animation.",
        device_telemetry={"os": "iOS 19.1"},
        item_id="item_neon_visor_3d_09",
        item_creator_pubkey=merchant_alice_pk
    )
    
    # Report 2: System-Wide Network Infrastructure Bug (No specific item creator)
    r2 = engine.submit_bug_report(
        user_peer_id="peer_user_2",
        app_version="1.0.0-oct01",
        category="P2P_SYNC",
        title="Global Bootnode Transport Latency",
        description="Cellular CGNAT reconnects take 4 seconds on US_EAST relay.",
        device_telemetry={"os": "Android 16"}
    )
    
    # TEST 1: Alice Queries Bugs (Item Creator View)
    alice_bugs = engine.query_bug_reports_scoped(requester_pubkey=merchant_alice_pk)
    assert len(alice_bugs) == 1, f"Alice should only see 1 report, got {len(alice_bugs)}"
    assert alice_bugs[0]["itemId"] == "item_neon_visor_3d_09"
    print(f"✅ TEST 1 (Item Creator Scoped View - Alice): PASS [Found {len(alice_bugs)} item report for Alice]")
    
    # TEST 2: Bob Queries Bugs (Item Creator View - Should see 0)
    bob_bugs = engine.query_bug_reports_scoped(requester_pubkey=merchant_bob_pk)
    assert len(bob_bugs) == 0, f"Bob should see 0 reports, got {len(bob_bugs)}"
    print(f"✅ TEST 2 (Item Creator Scoped View - Bob): PASS [Bob restricted from seeing Alice or System reports]")
    
    # TEST 3: Master Creator Queries Bugs (Full Master Access)
    master_bugs = engine.query_bug_reports_scoped(requester_pubkey=master_creator_pk)
    assert len(master_bugs) == 2, f"Master Creator should see all 2 reports, got {len(master_bugs)}"
    print(f"✅ TEST 3 (Master Creator Platform Access): PASS [Master Creator sees all {len(master_bugs)} reports]")
    
    # TEST 4: Alice tries to access system bug details via Console (Should be FORBIDDEN)
    alice_unauthorized = engine.developer_console_api(
        requester_pubkey=merchant_alice_pk,
        action="GET_FULL_DIAGNOSTICS",
        bug_id=r2["bugId"]
    )
    assert alice_unauthorized["status"] == "FORBIDDEN", "Alice must be forbidden from accessing system bugs"
    print(f"✅ TEST 4 (Unauthorized Item Access Blocked): PASS [{alice_unauthorized['message']}]")
    
    print("=================================================================")
    print("FINAL SCOPED BUG REPORTING ENGINE VERIFICATION STATUS: PASS")
    print("=================================================================")
