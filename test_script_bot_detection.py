import time
from script_bot_detection_engine import ScriptBotDetectionEngine, DeviceTelemetry

def run_bot_detection_tests():
    print("=========================================================================")
    print("  SCRIPT BOT DETECTION & PREVENTION SUITE FOR THE KICKBACK MOBILE SERVICE")
    print("=========================================================================\n")

    engine = ScriptBotDetectionEngine()
    user_pubkey = "ed25519_user_human_mobile_device_01"

    # -------------------------------------------------------------------------
    # TEST 1: Genuine Human User Post Creation
    # -------------------------------------------------------------------------
    print("[TEST 1] Legitimate Human User Post Creation")
    human_telemetry = DeviceTelemetry(
        keystroke_delays_ms=[140.0, 220.0, 95.0, 310.0, 180.0, 260.0, 115.0, 420.0],
        touch_pressure_samples=[0.82, 0.79, 0.85, 0.88, 0.80],
        gyroscope_jitter_xyz=[(0.01, 0.03, 0.02), (0.04, 0.01, 0.05), (0.02, 0.08, 0.01), (0.05, 0.02, 0.04)],
        time_to_compose_sec=5.2,
        has_hardware_attestation=True,
        attestation_nonce="nonce_app_attest_valid_12345"
    )
    res1 = engine.evaluate_submission(user_pubkey, "Hello KickBack! Loving this decentralized network.", human_telemetry)
    print(f"   Verdict: {res1['verdict']} | Bot Probability: {res1['bot_probability']}")
    print(f"   Reason: {res1['primary_reason']}")
    assert res1['verdict'] == "APPROVED_HUMAN", f"Failed Test 1: {res1}"
    print("   [✓] PASSED: Genuine human post approved.\n")

    # -------------------------------------------------------------------------
    # TEST 2: Headless Script Runner (Appium / Frida / Playwright Bot)
    # -------------------------------------------------------------------------
    print("[TEST 2] Headless Script Bot Attack (Programmatic Insertion)")
    bot_telemetry_1 = DeviceTelemetry(
        keystroke_delays_ms=[], # Zero keystrokes (programmatic field populate)
        touch_pressure_samples=[],
        gyroscope_jitter_xyz=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)], # Flat emulator gyro
        time_to_compose_sec=0.01, # 10ms compose time
        has_hardware_attestation=False, # Missing mobile app attest token
        attestation_nonce=""
    )
    res2 = engine.evaluate_submission("bot_pubkey_script_runner", "Automated script post injecting content!", bot_telemetry_1)
    print(f"   Verdict: {res2['verdict']} | Bot Probability: {res2['bot_probability']}")
    print(f"   Details: {res2['details']}")
    assert res2['verdict'] == "REJECTED_BOT", f"Failed Test 2: {res2}"
    print("   [✓] PASSED: Headless script runner detected and blocked.\n")

    # -------------------------------------------------------------------------
    # TEST 3: High-Frequency Post Burst Spam Attack
    # -------------------------------------------------------------------------
    print("[TEST 3] High-Frequency Post Burst Spam Attack")
    spammer_pubkey = "spammer_pubkey_rapid_fire"
    now = time.time()
    for i in range(3):
        r = engine.evaluate_submission(spammer_pubkey, f"Burst post message #{i+1}", human_telemetry, now=now+i)
        assert r['verdict'] == "APPROVED_HUMAN"

    # 4th post within 60s window should be blocked
    res3 = engine.evaluate_submission(spammer_pubkey, "Burst post message #4 (Exceeds limit!)", human_telemetry, now=now+5)
    print(f"   Verdict: {res3['verdict']} | Reason: {res3['primary_reason']}")
    assert res3['verdict'] == "REJECTED_BOT"
    assert "Rate limit exceeded" in res3['primary_reason']
    print("   [✓] PASSED: Burst rate limit attack blocked.\n")

    # -------------------------------------------------------------------------
    # TEST 4: Repetitive Content Spam Bot
    # -------------------------------------------------------------------------
    print("[TEST 4] Repetitive Content Spam Bot")
    spammer_pubkey2 = "spammer_pubkey_content_duplication"
    r_init = engine.evaluate_submission(spammer_pubkey2, "Buy cheap tokens now at http://spam.xyz!", human_telemetry)
    assert r_init['verdict'] == "APPROVED_HUMAN"

    # Attempt to post identical content
    res4 = engine.evaluate_submission(spammer_pubkey2, "Buy cheap tokens now at http://spam.xyz!", human_telemetry)
    print(f"   Verdict: {res4['verdict']} | Reason: {res4['primary_reason']}")
    assert res4['verdict'] == "REJECTED_BOT"
    assert "Content duplication detected" in res4['primary_reason']
    print("   [✓] PASSED: Content duplication spam attack blocked.\n")

    # -------------------------------------------------------------------------
    # TEST 5: Robotic Uniform Keystroke Emulator Bot
    # -------------------------------------------------------------------------
    print("[TEST 5] Robotic Uniform Keystroke Emulator Bot")
    robotic_telemetry = DeviceTelemetry(
        keystroke_delays_ms=[50.0, 50.0, 50.0, 50.0, 50.0, 50.0], # Exact 50ms uniform timing (variance = 0)
        touch_pressure_samples=[0.5, 0.5, 0.5],
        gyroscope_jitter_xyz=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
        time_to_compose_sec=2.0,
        has_hardware_attestation=True,
        attestation_nonce="nonce_valid"
    )
    res5 = engine.evaluate_submission("bot_uniform_keystrokes", "Uniform robotic timing test content", robotic_telemetry)
    print(f"   Verdict: {res5['verdict']} | Bot Probability: {res5['bot_probability']}")
    print(f"   Details: {res5['details']}")
    assert res5['verdict'] == "REJECTED_BOT"
    print("   [✓] PASSED: Robotic uniform timing emulator blocked.\n")

    print("=========================================================================")
    print("  ALL SCRIPT BOT DETECTION & PREVENTION SUITE TESTS PASSED 100%! ")
    print("=========================================================================")

if __name__ == "__main__":
    run_bot_detection_tests()
