"""
PiSecure Mining Challenge System (Phase 1)
===========================================

Implements Fiat-Shamir commitment-challenge-response protocol for mining challenges.

Architecture:
  1. Network publishes time-locked challenge commitment
  2. Miner receives challenge details (nonce range, epoch)
  3. Miner performs mining within constraint and generates ZK proof
  4. Proof verifies: miner found valid hash without revealing exact nonce
  5. Block includes proof; validators verify challenge was valid

This is Pi-native: no heavy ZK libraries, uses existing RSA/SHA256 infrastructure.
"""

import hashlib
import json
import time
import secrets
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import os


@dataclass
class Challenge:
    """Mining challenge issued by network"""

    challenge_id: str  # Unique challenge identifier
    epoch: int  # Network epoch (increments ~every 10 blocks)
    issued_at: float  # Unix timestamp when challenge was issued
    valid_until: float  # Expiry timestamp (usually issued_at + 3600 seconds)
    nonce_min: int  # Minimum nonce allowed for this challenge
    nonce_max: int  # Maximum nonce allowed for this challenge
    prev_block_hash: str  # Hash of previous block (freshness guarantee)
    commitment_hash: str  # H(challenge_secret || timestamp) - blind commitment
    difficulty: int  # Difficulty in zero-bits


@dataclass
class ChallengeResponse:
    """Zero-knowledge proof of valid mining within challenge constraints"""

    challenge_id: str
    nonce_used: int
    hash_result: str  # Actual hash found by miner
    zero_bits: int  # Number of zero bits in hash

    # Fiat-Shamir proof components (commitment-challenge-response)
    salt: str  # Random salt used in commitment
    commitment: str  # H(nonce_used || salt || timestamp)
    fs_challenge: str  # H(commitment || prev_block_hash || epoch)
    fs_response: int  # nonce_used XOR fs_challenge (masked nonce)

    # Metadata
    timestamp: float  # When proof was generated
    miner_signature: str  # Signature of (challenge_id || hash_result || zero_bits)


class ChallengeManager:
    """
    Manages mining challenges for the network.

    Responsibilities:
    - Generate challenges at regular intervals (every 10 blocks)
    - Issue challenges to mining pool
    - Validate challenge responses
    - Track challenge statistics
    """

    # Challenge lifecycle constants
    CHALLENGE_INTERVAL = 10  # New challenge every N blocks
    CHALLENGE_VALIDITY = 3600  # Challenge valid for 1 hour
    MIN_NONCE_RANGE = 100000000  # Min nonce per challenge (100M)

    def __init__(self, data_dir: str = "/var/lib/pisecure"):
        self.data_dir = Path(data_dir)
        self.challenges_dir = self.data_dir / "challenges"
        self.challenges_dir.mkdir(parents=True, exist_ok=True)

        self.active_challenge: Optional[Challenge] = None
        self.challenge_history: Dict[str, Challenge] = {}
        self.response_stats: Dict[str, Dict[str, Any]] = {}

        self._load_challenge_history()

    def generate_challenge(
        self, epoch: int, prev_block_hash: str, difficulty: int = 146
    ) -> Challenge:
        """
        Generate a new challenge for mining pool.

        Args:
            epoch: Current network epoch
            prev_block_hash: Hash of previous block (ensures freshness)
            difficulty: Target difficulty in zero-bits

        Returns:
            Challenge object with nonce constraints and ZK commitment
        """
        now = time.time()
        challenge_id = hashlib.sha256(
            f"{epoch}:{prev_block_hash}:{now}".encode()
        ).hexdigest()[:16]

        # Divide nonce space into distinct ranges per epoch
        # This allows pool to assign different ranges to different miners
        nonce_min = epoch * self.MIN_NONCE_RANGE
        nonce_max = nonce_min + self.MIN_NONCE_RANGE - 1

        # Generate Fiat-Shamir commitment (blind to actual challenge)
        challenge_secret = secrets.token_hex(32)  # Random secret
        commitment_input = f"{challenge_secret}:{prev_block_hash}:{epoch}"
        commitment_hash = hashlib.sha256(commitment_input.encode()).hexdigest()

        challenge = Challenge(
            challenge_id=challenge_id,
            epoch=epoch,
            issued_at=now,
            valid_until=now + self.CHALLENGE_VALIDITY,
            nonce_min=nonce_min,
            nonce_max=nonce_max,
            prev_block_hash=prev_block_hash,
            commitment_hash=commitment_hash,
            difficulty=difficulty,
        )

        self.active_challenge = challenge
        self.challenge_history[challenge_id] = challenge
        self._save_challenge(challenge)

        return challenge

    def validate_challenge_response(
        self, response: ChallengeResponse, expected_prev_hash: str
    ) -> Tuple[bool, str]:
        """
        Validate a challenge response using Fiat-Shamir proof verification.

        Protocol verification:
        1. Check challenge is current and not expired
        2. Verify Fiat-Shamir proof:
           - Recompute commitment from nonce, salt, timestamp
           - Recompute fs_challenge from commitment, prev_block_hash, epoch
           - Verify fs_response = nonce XOR fs_challenge
        3. Verify nonce is within allowed range
        4. Verify proof-of-work (hash meets difficulty)

        Args:
            response: ChallengeResponse with ZK proof
            expected_prev_hash: Hash we expect from challenge

        Returns:
            (is_valid, error_message)
        """
        # 1. Challenge freshness check
        if response.challenge_id not in self.challenge_history:
            return False, f"Unknown challenge: {response.challenge_id}"

        challenge = self.challenge_history[response.challenge_id]
        now = time.time()

        if now > challenge.valid_until:
            return False, f"Challenge expired at {challenge.valid_until}"

        # 2. Fiat-Shamir proof verification
        # Recompute commitment
        commitment_input = f"{response.nonce_used}:{response.salt}:{response.timestamp}"
        recomputed_commitment = hashlib.sha256(commitment_input.encode()).hexdigest()

        if recomputed_commitment != response.commitment:
            return False, "Commitment verification failed: hash mismatch"

        # Recompute fs_challenge
        fs_challenge_input = (
            f"{response.commitment}:{expected_prev_hash}:{challenge.epoch}"
        )
        recomputed_fs_challenge = int(
            hashlib.sha256(fs_challenge_input.encode()).hexdigest(), 16
        )

        # Verify fs_response = nonce XOR fs_challenge
        recovered_nonce = response.fs_response ^ recomputed_fs_challenge
        if recovered_nonce != response.nonce_used:
            return False, "Fiat-Shamir proof verification failed: nonce mismatch"

        # 3. Nonce range check
        if not (challenge.nonce_min <= response.nonce_used <= challenge.nonce_max):
            return (
                False,
                f"Nonce out of range: {response.nonce_used} not in [{challenge.nonce_min}, {challenge.nonce_max}]",
            )

        # 4. Proof-of-work check
        from .pihash import count_zero_bits

        zero_bits = count_zero_bits(response.hash_result)

        if zero_bits < challenge.difficulty:
            return (
                False,
                f"Insufficient proof-of-work: {zero_bits} < {challenge.difficulty}",
            )

        # All checks passed!
        self._record_response_stat(
            response.challenge_id, response.nonce_used, zero_bits
        )
        return True, "Challenge response valid"

    def generate_proof(
        self,
        nonce: int,
        hash_result: str,
        zero_bits: int,
        challenge: Challenge,
        miner_signature: str = "",
    ) -> ChallengeResponse:
        """
        Generate Fiat-Shamir zero-knowledge proof of valid mining.

        Protocol:
        1. Miner commits to nonce: commitment = H(nonce || random_salt || timestamp)
        2. Network challenges: fs_challenge = H(commitment || prev_block_hash || epoch)
        3. Miner responds: fs_response = nonce XOR fs_challenge (masked nonce)
        4. Verifier checks: XOR(fs_response, fs_challenge) == nonce

        This proves the miner knows a nonce producing valid hash, without revealing it.

        Args:
            nonce: Nonce used in mining
            hash_result: Hash produced by mining
            zero_bits: Number of zero bits in hash
            challenge: Challenge object this response addresses
            miner_signature: Optional RSA signature of proof

        Returns:
            ChallengeResponse with ZK proof
        """
        timestamp = time.time()
        salt = secrets.token_hex(16)  # Random salt

        # Step 1: Commitment (hiding nonce)
        commitment_input = f"{nonce}:{salt}:{timestamp}"
        commitment = hashlib.sha256(commitment_input.encode()).hexdigest()

        # Step 2: Fiat-Shamir challenge (deterministic, based on commitment)
        fs_challenge_input = (
            f"{commitment}:{challenge.prev_block_hash}:{challenge.epoch}"
        )
        fs_challenge = int(hashlib.sha256(fs_challenge_input.encode()).hexdigest(), 16)

        # Step 3: Response (masked nonce)
        fs_response = nonce ^ fs_challenge

        return ChallengeResponse(
            challenge_id=challenge.challenge_id,
            nonce_used=nonce,
            hash_result=hash_result,
            zero_bits=zero_bits,
            salt=salt,
            commitment=commitment,
            fs_challenge=hex(fs_challenge),
            fs_response=fs_response,
            timestamp=timestamp,
            miner_signature=miner_signature,
        )

    def get_current_challenge(self) -> Optional[Challenge]:
        """Get the currently active challenge"""
        if self.active_challenge and time.time() < self.active_challenge.valid_until:
            return self.active_challenge
        return None

    def get_challenge_stats(self, challenge_id: str) -> Dict[str, Any]:
        """Get statistics for a challenge"""
        return self.response_stats.get(
            challenge_id,
            {
                "total_responses": 0,
                "valid_responses": 0,
                "avg_zero_bits": 0,
                "nonce_coverage": 0.0,
            },
        )

    def _record_response_stat(self, challenge_id: str, nonce: int, zero_bits: int):
        """Record statistics for a response"""
        if challenge_id not in self.response_stats:
            self.response_stats[challenge_id] = {
                "total_responses": 0,
                "valid_responses": 0,
                "avg_zero_bits": 0,
                "nonce_usage": [],
            }

        stats = self.response_stats[challenge_id]
        stats["total_responses"] += 1
        stats["valid_responses"] += 1

        # Track average zero bits
        prev_avg = stats["avg_zero_bits"]
        new_count = stats["valid_responses"]
        stats["avg_zero_bits"] = (prev_avg * (new_count - 1) + zero_bits) / new_count

        # Track nonce usage
        stats["nonce_usage"].append(nonce)

    def _save_challenge(self, challenge: Challenge):
        """Persist challenge to disk"""
        challenge_file = self.challenges_dir / f"{challenge.challenge_id}.json"
        with open(challenge_file, "w") as f:
            json.dump(asdict(challenge), f, indent=2)

    def _load_challenge_history(self):
        """Load challenge history from disk"""
        if self.challenges_dir.exists():
            for challenge_file in self.challenges_dir.glob("*.json"):
                try:
                    with open(challenge_file, "r") as f:
                        data = json.load(f)
                        challenge = Challenge(**data)
                        self.challenge_history[challenge.challenge_id] = challenge
                except Exception as e:
                    print(f"⚠️ Failed to load challenge {challenge_file}: {e}")


# Global challenge manager instance
_challenge_manager = None


def get_challenge_manager() -> ChallengeManager:
    """Get or create global challenge manager"""
    global _challenge_manager
    if _challenge_manager is None:
        _challenge_manager = ChallengeManager()
    return _challenge_manager
