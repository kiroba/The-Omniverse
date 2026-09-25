import math
import time
import json
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field

# Configuration thresholds
MAX_BURST_POSTS_PER_MINUTE = 3
MAX_HOURLY_POSTS = 25
MIN_KEYSTROKE_TIMING_VARIANCE = 15.0  # ms variance (bots usually have 0 or uniform delays)
MIN_GYRO_JITTER_ENTROPY = 0.05        # physical hand tremor/motion jitter
MAX_CONTENT_SIMILARITY = 0.85          # Jaccard similarity threshold for spam

@dataclass
class DeviceTelemetry:
    """Captured touch dynamics and motion sensor telemetry during post creation."""
    keystroke_delays_ms: List[float]       # Inter-key timing in ms
    touch_pressure_samples: List[float]    # Touch screen pressure readings
    gyroscope_jitter_xyz: List[Tuple[float, float, float]] # Motion sensor micro-tremors
    time_to_compose_sec: float             # Total time spent composing post
    has_hardware_attestation: bool         # Apple App Attest / Android Play Integrity token valid
    attestation_nonce: str                 # Cryptographic nonce tied to current timestamp

class ScriptBotDetectionEngine:
    """
    Multi-Tiered Bot Detection & Prevention Engine for The KickBack Mobile App.
    Evaluates posts at creation time prior to cryptographic Merkle logging.
    """
    def __init__(self):
        # User history tracking for rate limits and content entropy
        self.user_post_timestamps: Dict[str, List[float]] = {}
        self.user_recent_contents: Dict[str, List[str]] = {}

    def _calculate_variance(self, data: List[float]) -> float:
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        return sum((x - mean) ** 2 for x in data) / (len(data) - 1)

    def _calculate_gyro_entropy(self, gyro_samples: List[Tuple[float, float, float]]) -> float:
        """Calculates physical motion jitter entropy from mobile gyroscope sensors."""
        if not gyro_samples:
            return 0.0
        diffs = []
        for i in range(1, len(gyro_samples)):
            dx = gyro_samples[i][0] - gyro_samples[i-1][0]
            dy = gyro_samples[i][1] - gyro_samples[i-1][1]
            dz = gyro_samples[i][2] - gyro_samples[i-1][2]
            magnitude = math.sqrt(dx*dx + dy*dy + dz*dz)
            diffs.append(magnitude)
        return self._calculate_variance(diffs)

    def _calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    def check_rate_limits(self, pubkey: str, now: float) -> Tuple[bool, str]:
        timestamps = self.user_post_timestamps.get(pubkey, [])
        # Filter timestamps within last 60s and 3600s
        recent_1m = [t for t in timestamps if now - t <= 60]
        recent_1h = [t for t in timestamps if now - t <= 3600]

        if len(recent_1m) >= MAX_BURST_POSTS_PER_MINUTE:
            return False, f"Rate limit exceeded: {len(recent_1m)} posts in last 60 seconds (max {MAX_BURST_POSTS_PER_MINUTE})"
        if len(recent_1h) >= MAX_HOURLY_POSTS:
            return False, f"Rate limit exceeded: {len(recent_1h)} posts in last hour (max {MAX_HOURLY_POSTS})"

        return True, "Rate limits clean"

    def check_content_duplication(self, pubkey: str, content: str) -> Tuple[bool, str]:
        recent_posts = self.user_recent_contents.get(pubkey, [])
        for past_post in recent_posts:
            similarity = self._calculate_jaccard_similarity(content, past_post)
            if similarity >= MAX_CONTENT_SIMILARITY:
                return False, f"Content duplication detected (Similarity {similarity*100:.1f}% >= {MAX_CONTENT_SIMILARITY*100:.0f}%)"
        return True, "Content entropy clean"

    def analyze_behavioral_telemetry(self, telemetry: DeviceTelemetry, content_len: int) -> Tuple[bool, float, List[str]]:
        reasons = []
        bot_score = 0.0  # 0.0 = Pure Human, 1.0 = Definite Bot

        # 1. Hardware App Attestation Check
        if not telemetry.has_hardware_attestation:
            bot_score += 0.5
            reasons.append("Missing hardware remote attestation token (possible emulator / script runner)")

        # 2. Keystroke Dynamics Analysis
        if content_len > 5:
            if not telemetry.keystroke_delays_ms or len(telemetry.keystroke_delays_ms) < 3:
                bot_score += 0.4
                reasons.append("Instant text insertion detected (zero keystroke telemetry / programmatic paste)")
            else:
                timing_var = self._calculate_variance(telemetry.keystroke_delays_ms)
                if timing_var < MIN_KEYSTROKE_TIMING_VARIANCE:
                    bot_score += 0.35
                    reasons.append(f"Robotic keystroke cadence (Timing variance {timing_var:.2f} < {MIN_KEYSTROKE_TIMING_VARIANCE})")

        # 3. Composition Time vs Content Length Ratio
        # Humans need at least ~100ms per character to type manually
        min_human_type_time = (content_len * 0.08)  # 80ms per char
        if telemetry.time_to_compose_sec < min_human_type_time and content_len > 10:
            bot_score += 0.3
            reasons.append(f"Impossible typing speed ({telemetry.time_to_compose_sec:.2f}s for {content_len} chars)")

        # 4. Motion Sensor Gyroscope Jitter Analysis
        gyro_jitter = self._calculate_gyro_entropy(telemetry.gyroscope_jitter_xyz)
        if gyro_jitter < MIN_GYRO_JITTER_ENTROPY:
            bot_score += 0.25
            reasons.append(f"Synthetic device environment (Gyroscope jitter {gyro_jitter:.4f} < {MIN_GYRO_JITTER_ENTROPY})")

        is_human = bot_score < 0.50
        return is_human, min(1.0, bot_score), reasons

    def evaluate_submission(
        self,
        pubkey: str,
        content: str,
        telemetry: DeviceTelemetry,
        now: Optional[float] = None
    ) -> Dict[str, Any]:
        now = now or time.time()

        # Step 1: Rate Limiting Check
        rate_ok, rate_msg = self.check_rate_limits(pubkey, now)
        if not rate_ok:
            return {
                "verdict": "REJECTED_BOT",
                "is_human": False,
                "confidence_score": 1.0,
                "primary_reason": rate_msg,
                "details": [rate_msg]
            }

        # Step 2: Content Duplication / Spam Entropy
        content_ok, content_msg = self.check_content_duplication(pubkey, content)
        if not content_ok:
            return {
                "verdict": "REJECTED_BOT",
                "is_human": False,
                "confidence_score": 0.9,
                "primary_reason": content_msg,
                "details": [content_msg]
            }

        # Step 3: Behavioral Telemetry & Hardware Attestation
        is_human, bot_score, telemetry_reasons = self.analyze_behavioral_telemetry(telemetry, len(content))

        if is_human:
            # Record successful post for rate limits & similarity tracking
            self.user_post_timestamps.setdefault(pubkey, []).append(now)
            self.user_recent_contents.setdefault(pubkey, []).append(content)
            # Keep only last 50 contents
            if len(self.user_recent_contents[pubkey]) > 50:
                self.user_recent_contents[pubkey].pop(0)

            return {
                "verdict": "APPROVED_HUMAN",
                "is_human": True,
                "bot_probability": round(bot_score, 3),
                "primary_reason": "Verified genuine human creation via biometric telemetry & app attestation",
                "details": []
            }
        else:
            return {
                "verdict": "REJECTED_BOT",
                "is_human": False,
                "bot_probability": round(bot_score, 3),
                "primary_reason": telemetry_reasons[0] if telemetry_reasons else "Bot telemetry detected",
                "details": telemetry_reasons
            }
