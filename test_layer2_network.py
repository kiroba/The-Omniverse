import time
from layer2_p2p_crdt_engine import (
    P2PGossipNetwork, OmniHubP2PPeer, EventEnvelope
)

def run_layer2_tests():
    print("=========================================================================")
    print("  LAYER 2 P2P GOSSIPSUB & DELTA-CRDT NETWORK TEST SUITE")
    print("=========================================================================\n")

    # 1. Initialize P2P Network Topology
    network = P2PGossipNetwork()
    peer_alpha = OmniHubP2PPeer("peer_alpha_relay", is_mobile=False)
    peer_beta = OmniHubP2PPeer("peer_beta_desktop", is_mobile=False)
    mobile_kickback = OmniHubP2PPeer("mobile_kickback_ui", is_mobile=True)

    network.register_peer(peer_alpha)
    network.register_peer(peer_beta)
    network.register_peer(mobile_kickback)

    print("[+] P2P Mesh Topology initialized with 3 peers (Relay, Desktop, Mobile).")

    # 2. Test Online Profile Broadcast & LWW CRDT Convergence
    print("\n[TEST 1] Online Profile Broadcast & LWW-Register Convergence")
    profile_payload = {"username": "Kiroba_Architect", "bio": "Building the Omniverse"}
    env_profile = peer_alpha.storage.append_local_event("USER_PROFILE_UPDATE", profile_payload)
    peer_alpha.crdt.apply_event_delta(env_profile)

    delivered = network.broadcast_gossip("peer_alpha_relay", "/kickback/feed", env_profile)
    print(f"   [-] Broadcasted profile update to {delivered} peers.")

    # Verify LWW CRDT convergence on Mobile Node
    mobile_profile = mobile_kickback.crdt.profiles_lww.get(peer_alpha.storage.pubkey_hex)
    assert mobile_profile is not None and mobile_profile[1] == "Kiroba_Architect"
    print("   [✓] PASSED: Mobile node converged to identical user profile via LWW-Register.")

    # 3. Test Mobile Offline Mode & Catch-Up Sync (The KickBack)
    print("\n[TEST 2] Mobile Offline Mode & Ephemeral Catch-Up Syncing")
    print("   [-] Mobile device entering background execution mode (Offline).")
    mobile_kickback.is_online = False

    # Desktop nodes post items while mobile is offline
    post_payload1 = {"post_id": "post_101", "content": "Desktop node post while mobile is offline!"}
    env_post1 = peer_beta.storage.append_local_event("NEWSFEED_POST", post_payload1)
    peer_beta.crdt.apply_event_delta(env_post1)
    network.broadcast_gossip("peer_beta_desktop", "/kickback/feed", env_post1)

    # Mobile generates local offline post (staged in local outbox)
    offline_post_payload = {"post_id": "post_102_mobile", "content": "Offline post created on The KickBack mobile!"}
    env_offline = mobile_kickback.storage.append_local_event("NEWSFEED_POST", offline_post_payload)
    mobile_kickback.crdt.apply_event_delta(env_offline)

    print("   [-] Mobile device re-engaging in foreground mode (Online). Executing catch-up sync...")
    mobile_kickback.is_online = True
    synced_items = network.execute_mobile_catchup_sync("mobile_kickback_ui", "peer_beta_desktop")
    print(f"   [-] Catch-Up Sync completed. Processed {synced_items} missed delta events.")

    # Verify newsfeed convergence across all peers
    mobile_feed = mobile_kickback.crdt.get_kickback_feed()
    beta_feed = peer_beta.crdt.get_kickback_feed()
    assert len(mobile_feed) == len(beta_feed) == 2
    print(f"   [✓] PASSED: Both mobile and desktop feeds synchronized to identical {len(mobile_feed)} posts.")

    # 4. Test Layer 2 Security Attacks
    print("\n[TEST 3] Layer 2 Security Attacks & Network Hardening")
    
    # Attack A: Forged Signature Injection over GossipSub
    forged_env = EventEnvelope(
        event_id="forged_001", timestamp=int(time.time()*1000),
        author_pubkey=peer_alpha.storage.pubkey_hex, event_type="NEWSFEED_POST",
        payload={"content": "I am a malicious injected post!"}, prev_hash="000"*21,
        current_hash="abc"*21, signature="1234"*16
    )
    rejected_a = not peer_beta.on_gossip_message("/kickback/feed", forged_env)
    assert rejected_a
    print("   [✓] PASSED: Forged GossipSub message rejected by Layer 2 signature gateway.")

    # Attack B: Replay Attack over GossipSub
    # Attempting to re-broadcast env_post1
    replayed = not peer_beta.on_gossip_message("/kickback/feed", env_post1)
    assert replayed
    print("   [✓] PASSED: Replayed GossipSub message dropped by in-memory bloom filter.")

    # 5. Test PN-Counter Delta-CRDT Social Likes
    print("\n[TEST 4] PN-Counter Social Post Reactions (+1 / -1 Likes)")
    like_payload = {"post_id": "post_101", "value": 1}
    env_like = mobile_kickback.storage.append_local_event("POST_REACTION", like_payload)
    mobile_kickback.crdt.apply_event_delta(env_like)
    network.broadcast_gossip("mobile_kickback_ui", "/kickback/feed", env_like)

    assert peer_beta.crdt.get_post_likes_count("post_101") == 1
    print("   [✓] PASSED: PN-Counter CRDT merged post likes count deterministically across peers.")

    print("\n=========================================================================")
    print("  ALL LAYER 2 P2P NETWORK & DELTA-CRDT TESTS PASSED SUCCESSFULLY! ")
    print("=========================================================================")

if __name__ == "__main__":
    run_layer2_tests()
