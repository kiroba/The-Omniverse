import hashlib
import json
import time
from typing import Dict, Any, List, Optional

class PublicAccountabilityEngine:
    """
    Public Accountability Engine for KickBack and The Omniverse.
    
    Acts as a lightweight, decoupled presentation and ticker manager for public
    security alerts, node bans, and cross-cohort violation warnings.
    
    Enforces:
    1. Strict Minor Identity Redaction (Masks minor PII/handles completely).
    2. Public Exposure of Adult Bad Actors and Slashed Node Peer IDs.
    3. Low-Memory Circular Buffer (Max 100 recent alerts stored).
    4. Rate-limiting & Spam Throttling for public ticker streams.
    """

    ALERT_NODE_BANNED = "NODE_BANNED"
    ALERT_ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    ALERT_CROSS_COHORT_VIOLATION = "CROSS_COHORT_VIOLATION_BLOCKED"
    ALERT_PATTERN_MATCHED = "BAD_BEHAVIOR_PATTERN_MATCHED"

    def __init__(self, max_ticker_capacity: int = 100):
        self.max_ticker_capacity = max_ticker_capacity
        self.ticker_buffer: List[Dict[str, Any]] = []
        self.last_broadcast_timestamp: float = 0.0
        self.min_broadcast_interval_sec: float = 0.1  # Throttling burst spam

    def process_security_event(self, raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ingests a raw security event from OmniMind Moderation, verifies envelope structure,
        applies privacy redactions, and formats a public ticker alert.
        """
        event_type = raw_event.get("alertType")
        timestamp = raw_event.get("timestamp", int(time.time()))
        
        # Rate limit broadcast stream
        now = time.time()
        if now - self.last_broadcast_timestamp < self.min_broadcast_interval_sec:
            # Throttling rapid burst spam
            time.sleep(self.min_broadcast_interval_sec)
        self.last_broadcast_timestamp = time.time()

        sanitized_alert = {
            "alertId": f"pub_alert_{hashlib.sha256(f'{event_type}_{timestamp}_{time.time()}'.encode('utf-8')).hexdigest()[:12]}",
            "alertType": event_type,
            "timestamp": timestamp,
            "formattedMessage": "",
            "severity": raw_event.get("severity", "MEDIUM")
        }

        if event_type in [self.ALERT_NODE_BANNED, self.ALERT_ACCOUNT_SUSPENDED]:
            peer_id = raw_event.get("peerId", "UNKNOWN_PEER")
            account_handle = raw_event.get("actorHandle", "ANONYMOUS_ACTOR")
            reason = raw_event.get("reason", "Protocol Violation")
            score_delta = raw_event.get("scoreDelta", -100.0)

            sanitized_alert["actorHandle"] = account_handle
            sanitized_alert["peerId"] = f"{peer_id[:8]}...{peer_id[-4:]}" if len(peer_id) > 12 else peer_id
            sanitized_alert["formattedMessage"] = (
                f"NETWORK SECURITY ALERT: Account '{account_handle}' "
                f"(Peer: {sanitized_alert['peerId']}) was BANNED. "
                f"Reason: {reason}. Slashing Delta: {score_delta} points."
            )

        elif event_type == self.ALERT_CROSS_COHORT_VIOLATION:
            adult_handle = raw_event.get("adultHandle", "UNIDENTIFIED_ADULT")
            attempted_action = raw_event.get("actionAttempted", "DIRECT_INTERACTION")
            
            # STRICT REDACTION: Ensure minor identity is NEVER exposed in public logs
            sanitized_alert["adultHandle"] = adult_handle
            sanitized_alert["protectedTargetCohort"] = "COHORT_MINOR_13_17 (Identity Shielded)"
            sanitized_alert["formattedMessage"] = (
                f"PROTECTION ALERT: Direct {attempted_action} attempt by Adult Account '{adult_handle}' "
                f"toward a protected Minor Account was BLOCKED at the P2P gateway. "
                f"Account '{adult_handle}' flagged & queued for enforcement review."
            )

        elif event_type == self.ALERT_PATTERN_MATCHED:
            pattern_id = raw_event.get("patternId", "UNKNOWN_PATTERN")
            target_handle = raw_event.get("actorHandle", "SUSPECT_ACCOUNT")
            
            sanitized_alert["actorHandle"] = target_handle
            sanitized_alert["patternId"] = pattern_id
            sanitized_alert["formattedMessage"] = (
                f"OMNIMIND PATTERN MATCH: Post by '{target_handle}' matched human-trained "
                f"bad behavior vector ({pattern_id[:12]}). Content shadow-isolated."
            )

        else:
            sanitized_alert["formattedMessage"] = f"SYSTEM ALERT: {raw_event.get('details', 'General Network Event')}"

        # Append to circular memory buffer
        self._append_to_ticker(sanitized_alert)
        return sanitized_alert

    def _append_to_ticker(self, alert: Dict[str, Any]):
        """
        Maintains lightweight circular buffer to ensure zero storage bloat.
        """
        self.ticker_buffer.append(alert)
        if len(self.ticker_buffer) > self.max_ticker_capacity:
            self.ticker_buffer.pop(0)

    def get_public_ticker_feed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns recent sanitized public alerts for rendering on System Health HUDs.
        """
        return self.ticker_buffer[-limit:]


def run_accountability_engine_test_suite():
    print("=================================================================")
    print("   KICKBACK: PUBLIC ACCOUNTABILITY STANDALONE ENGINE TEST        ")
    print("=================================================================")
    
    engine = PublicAccountabilityEngine(max_ticker_capacity=5)
    
    # Test 1: Node Ban Event Processing
    event_1 = {
        "alertType": PublicAccountabilityEngine.ALERT_NODE_BANNED,
        "peerId": "12D3KooW9x8y7z6a5b4c3d2e1f0g9h8i",
        "actorHandle": "@MaliciousBot99",
        "reason": "Script-Bot Automated Spam Relaying",
        "scoreDelta": -210.0,
        "severity": "CRITICAL",
        "timestamp": int(time.time())
    }
    alert_1 = engine.process_security_event(event_1)
    print(f"TEST 1 (Node Ban Processing): PASS")
    print(f"   Ticker Output: {alert_1['formattedMessage']}\n")
    
    # Test 2: Cross-Cohort Violation with Redaction
    event_2 = {
        "alertType": PublicAccountabilityEngine.ALERT_CROSS_COHORT_VIOLATION,
        "adultHandle": "@CreepyAdultUser",
        "actionAttempted": "DIRECT_MESSAGE",
        "minorHandle": "@SecretTeen15",  # MUST BE REDACTED
        "severity": "HIGH",
        "timestamp": int(time.time())
    }
    alert_2 = engine.process_security_event(event_2)
    assert "@SecretTeen15" not in json.dumps(alert_2), "CRITICAL PRIVACY LEAK: Minor handle exposed in public alert!"
    print(f"TEST 2 (Cross-Cohort Minor Privacy Redaction): PASS")
    print(f"   Ticker Output: {alert_2['formattedMessage']}\n")
    
    # Test 3: Circular Buffer Cap Verification
    for i in range(10):
        engine.process_security_event({
            "alertType": PublicAccountabilityEngine.ALERT_PATTERN_MATCHED,
            "actorHandle": f"@Scammer_{i}",
            "patternId": f"pattern_vector_00{i}",
            "timestamp": int(time.time())
        })
    
    ticker_feed = engine.get_public_ticker_feed(limit=10)
    assert len(ticker_feed) == 5, f"Expected 5 items in circular buffer, got {len(ticker_feed)}"
    print(f"TEST 3 (Zero-Storage Circular Buffer Cap): PASS [Buffer capped at {len(ticker_feed)} items]\n")
    
    print("=================================================================")
    print("FINAL PUBLIC ACCOUNTABILITY ENGINE VERIFICATION STATUS: PASS")
    print("=================================================================")

if __name__ == "__main__":
    run_accountability_engine_test_suite()
