#!/usr/bin/env python3
"""
PiSecure Cross-Platform Validator Demo

Demonstrates how to run a validator node on ANY platform:
- Mac
- Windows
- Linux
- Raspberry Pi

This validator can validate blocks WITHOUT requiring Pi hardware.
Only mining requires Pi hardware - validation is universal!
"""

import os
import sys
import time
from typing import Dict, Any

# Enable validation-only mode BEFORE importing PiSecure
# This allows validation on Mac, Windows, Linux without Pi hardware
os.environ["PISECURE_VALIDATE_ONLY"] = "1"
os.environ["PISECURE_TESTNET"] = "1"  # Use testnet for demo

print("=" * 70)
print("🛡️  PiSecure Cross-Platform Validator Demo")
print("=" * 70)
print("\n📋 Platform Detection:")
print(f"   OS: {sys.platform}")
print(f"   Python: {sys.version.split()[0]}")
print(f"   Mode: Validation-Only (PISECURE_VALIDATE_ONLY=1)")
print(f"   Network: Testnet (PISECURE_TESTNET=1)")
print("\n✨ This validator runs on ANY platform (Mac/Windows/Linux/Pi)!")
print("   - Block validation: ✅ Enabled")
print("   - Mining: ❌ Disabled (requires Pi hardware)")
print("   - Challenge proofs: ✅ Can validate")
print()

try:
    from pisecure.core import SignChain
    from pisecure.core.challenges import get_challenge_manager
    from pisecure.core.pihash import count_zero_bits

    print("✅ PiSecure modules imported successfully\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\n💡 Install PiSecure first:")
    print("   pip install pisecure")
    sys.exit(1)


class CrossPlatformValidator:
    """Validator that runs on any platform (not just Pi)"""

    def __init__(self):
        """Initialize validator with validation-only mode"""
        print("🔧 Initializing validator...")

        # Create blockchain instance (validation-only mode)
        self.blockchain = SignChain()

        # Get challenge manager (for validating ZK proofs)
        self.challenge_manager = get_challenge_manager()

        # Stats
        self.blocks_validated = 0
        self.challenges_validated = 0
        self.validation_errors = 0

        print(f"✅ Validator initialized")
        print(f"   Blockchain: {len(self.blockchain.chain)} blocks")
        print()

    def validate_blockchain(self) -> bool:
        """
        Validate entire blockchain

        This works on ANY platform - no Pi hardware required!
        """
        print("🔍 Validating blockchain integrity...")

        start_time = time.time()
        is_valid = self.blockchain.validate_chain()
        elapsed = time.time() - start_time

        if is_valid:
            print(f"✅ Blockchain valid ({len(self.blockchain.chain)} blocks)")
            print(f"   Validation time: {elapsed:.3f}s")
            self.blocks_validated += len(self.blockchain.chain)
        else:
            print(f"❌ Blockchain validation failed")
            self.validation_errors += 1

        print()
        return is_valid

    def validate_block_challenges(self) -> Dict[str, Any]:
        """
        Validate Phase 1 challenge proofs in all blocks

        This validates Fiat-Shamir ZK proofs WITHOUT requiring Pi hardware!
        """
        print("🎯 Validating Phase 1 challenge proofs...")

        blocks_with_challenges = 0
        valid_challenges = 0
        invalid_challenges = 0

        for i in range(1, len(self.blockchain.chain)):
            block = self.blockchain.chain[i]

            # Check if block has challenge response
            if hasattr(block, "challenge_response") and block.challenge_response:
                blocks_with_challenges += 1

                # Reconstruct challenge response object
                from pisecure.core.challenges import ChallengeResponse

                cr_dict = block.challenge_response
                challenge_response = ChallengeResponse(
                    challenge_id=cr_dict["challenge_id"],
                    nonce_used=cr_dict["nonce_used"],
                    hash_result=cr_dict["hash_result"],
                    zero_bits=cr_dict["zero_bits"],
                    salt=cr_dict["salt"],
                    commitment=cr_dict["commitment"],
                    fs_challenge=cr_dict["fs_challenge"],
                    fs_response=cr_dict["fs_response"],
                    timestamp=cr_dict["timestamp"],
                    miner_signature=cr_dict["miner_signature"],
                )

                # Validate challenge response (pure SHA256 + XOR math)
                prev_hash = self.blockchain.chain[i - 1].hash if i > 0 else "0"
                is_valid, error_msg = (
                    self.challenge_manager.validate_challenge_response(
                        challenge_response, expected_prev_hash=prev_hash
                    )
                )

                if is_valid:
                    valid_challenges += 1
                    print(f"   ✅ Block {block.index}: Challenge valid")
                else:
                    invalid_challenges += 1
                    print(f"   ❌ Block {block.index}: Challenge invalid - {error_msg}")

        self.challenges_validated += valid_challenges

        print()
        print(f"📊 Challenge Validation Summary:")
        print(f"   Total blocks: {len(self.blockchain.chain)}")
        print(f"   Blocks with challenges: {blocks_with_challenges}")
        print(f"   Valid challenges: {valid_challenges}")
        print(f"   Invalid challenges: {invalid_challenges}")
        print()

        return {
            "total_blocks": len(self.blockchain.chain),
            "blocks_with_challenges": blocks_with_challenges,
            "valid_challenges": valid_challenges,
            "invalid_challenges": invalid_challenges,
        }

    def validate_proof_of_work(self) -> Dict[str, Any]:
        """
        Validate proof-of-work on all blocks

        This counts zero bits WITHOUT requiring Pi hardware!
        """
        print("⛏️  Validating proof-of-work (zero bits)...")

        min_difficulty = 130  # Minimum safe difficulty
        blocks_below_difficulty = []

        for block in self.blockchain.chain:
            zero_bits = count_zero_bits(block.hash)

            if zero_bits < min_difficulty:
                blocks_below_difficulty.append(
                    {
                        "index": block.index,
                        "zero_bits": zero_bits,
                        "hash": block.hash[:32] + "...",
                    }
                )
                print(
                    f"   ⚠️  Block {block.index}: {zero_bits} zero bits (below minimum {min_difficulty})"
                )
            else:
                print(f"   ✅ Block {block.index}: {zero_bits} zero bits")

        print()
        if blocks_below_difficulty:
            print(f"⚠️  {len(blocks_below_difficulty)} blocks below minimum difficulty")
        else:
            print(f"✅ All blocks meet minimum difficulty ({min_difficulty} zero bits)")
        print()

        return {
            "total_blocks": len(self.blockchain.chain),
            "min_difficulty": min_difficulty,
            "blocks_below_difficulty": blocks_below_difficulty,
        }

    def get_validator_stats(self) -> Dict[str, Any]:
        """Get validator statistics"""
        return {
            "platform": sys.platform,
            "mode": "validation_only",
            "blocks_validated": self.blocks_validated,
            "challenges_validated": self.challenges_validated,
            "validation_errors": self.validation_errors,
            "blockchain_length": len(self.blockchain.chain),
            "validation_only_mode": os.environ.get("PISECURE_VALIDATE_ONLY") == "1",
        }

    def print_stats(self):
        """Print validator statistics"""
        stats = self.get_validator_stats()

        print("=" * 70)
        print("📊 Validator Statistics")
        print("=" * 70)
        print(f"Platform: {stats['platform']}")
        print(f"Mode: {stats['mode']}")
        print(f"Validation-Only: {'✅' if stats['validation_only_mode'] else '❌'}")
        print()
        print(f"Blockchain Length: {stats['blockchain_length']} blocks")
        print(f"Blocks Validated: {stats['blocks_validated']}")
        print(f"Challenges Validated: {stats['challenges_validated']}")
        print(f"Validation Errors: {stats['validation_errors']}")
        print("=" * 70)
        print()


def demonstrate_universal_validation():
    """
    Demonstrate that validation works on ANY platform

    This is the key insight: while mining requires Pi hardware,
    validation is universal and platform-agnostic!
    """
    print("🚀 Starting Cross-Platform Validation Demo...\n")

    # Create validator instance
    validator = CrossPlatformValidator()

    # 1. Validate blockchain integrity
    blockchain_valid = validator.validate_blockchain()

    if not blockchain_valid:
        print("⚠️  Blockchain validation failed - stopping demo")
        return

    # 2. Validate Phase 1 challenge proofs (Fiat-Shamir ZK)
    challenge_results = validator.validate_block_challenges()

    # 3. Validate proof-of-work (zero bits counting)
    pow_results = validator.validate_proof_of_work()

    # 4. Print final statistics
    validator.print_stats()

    # 5. Summary
    print("✅ Demo Complete!")
    print("\n🎯 Key Takeaways:")
    print("   1. Validation works on ANY platform (Mac/Windows/Linux/Pi)")
    print("   2. Only mining requires Pi hardware")
    print("   3. Challenge proofs use pure SHA256 + XOR (universal)")
    print("   4. Zero-bit counting is pure Python (no hardware dependency)")
    print("   5. Validators earn 0.1x block reward distributed proportionally")
    print()
    print("💡 To run a validator node:")
    print("   export PISECURE_VALIDATE_ONLY=1")
    print("   pisecure validate --continuous")
    print()


def test_validation_without_mining():
    """
    Test that validation works without mining capability

    This proves validators don't need Pi hardware!
    """
    print("🧪 Testing Validation-Only Mode...\n")

    # Attempt to create blockchain in validation-only mode
    try:
        blockchain = SignChain()
        print("✅ Blockchain created in validation-only mode")
        print(f"   Blocks: {len(blockchain.chain)}")
        print()
    except Exception as e:
        print(f"❌ Failed to create blockchain: {e}")
        return False

    # Attempt to validate chain (should work)
    try:
        is_valid = blockchain.validate_chain()
        print(f"✅ Chain validation: {'PASSED' if is_valid else 'FAILED'}")
        print()
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

    # Attempt to mine (should fail gracefully in validation-only mode)
    print("🔬 Testing mining (should fail gracefully)...")
    try:
        # Try to mine with validation-only mode enabled
        blockchain.mine_pending_transactions(allow_empty=True, verbose=False)
        print("⚠️  Mining succeeded (unexpected - should be disabled)")
    except Exception as e:
        print(f"✅ Mining disabled as expected: {type(e).__name__}")
        print(f"   (Validation-only mode prevents mining without Pi hardware)")

    print()
    return True


if __name__ == "__main__":
    print("🎬 Starting PiSecure Cross-Platform Validator Demo\n")

    # Test validation-only mode
    test_validation_without_mining()

    # Demonstrate universal validation
    demonstrate_universal_validation()

    print("🏁 Demo finished!\n")
    print("📚 Learn more:")
    print("   - docs/validator-guide.md")
    print("   - docs/phase1_mining_challenges.md")
    print("   - examples/phase1_mining_challenges.py")
    print()
