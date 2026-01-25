#!/usr/bin/env python3
"""
PiSecure Entropy Validation & Node Registration Example

Demonstrates:
1. Node registration with bootstrap server
2. Hardware entropy validation
3. Reputation tracking
4. Automatic retry and caching
5. Historical entropy analysis
"""

import os
import sys
import time
import logging
from typing import Optional

# Set validation-only mode if not on Pi (for demonstration)
if sys.platform != "linux" or not os.path.exists("/dev/hwrng"):
    print("⚠️  Warning: No hardware RNG detected, using mock mode")
    os.environ["PISECURE_MOCK_HARDWARE"] = "1"

# Use testnet for demo
os.environ["PISECURE_TESTNET"] = "1"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

try:
    from pisecure.core.entropy_client import BootstrapEntropyClient, get_entropy_client
    from pisecure.core.bootstrap_manager import (
        get_node_registration,
        get_bootstrap_registry,
    )
except ImportError:
    print("❌ PiSecure not installed. Run: pip install -e .")
    sys.exit(1)


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def demo_node_registration(node_id: str) -> bool:
    """
    Demonstrate node registration with bootstrap server

    Args:
        node_id: Unique node identifier

    Returns:
        True if registration successful
    """
    print_section("Step 1: Node Registration")

    registration = get_node_registration()

    # Register as miner
    result = registration.register_node(
        node_id=node_id,
        node_type="miner",
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        location="us-east",
        services=["mining", "p2p_sync"],
        capabilities=["mining", "entropy_submission"],
        network="testnet",
    )

    if result:
        print(f"✓ Node registered successfully!")
        print(f"  Node ID: {result.get('node_id')}")
        print(f"  Role: {result.get('assigned_role')}")
        print(f"  Reputation: {result.get('initial_reputation')}")

        if result.get("entropy_submission_required"):
            deadline = result.get("entropy_submission_deadline", 0)
            print(f"  ⚠️  Entropy submission required before {time.ctime(deadline)}")

        return True
    else:
        print(f"✗ Node registration failed")
        return False


def demo_entropy_submission(node_id: str):
    """
    Demonstrate entropy submission and validation

    Args:
        node_id: Node identifier
    """
    print_section("Step 2: Entropy Submission & Validation")

    # Get or create entropy client
    entropy_client = get_entropy_client(
        node_id=node_id,
        bootstrap_url="https://bootstrap-testnet.pisecure.org",
        network="testnet",
    )

    # Read and submit entropy
    print("\n📊 Submitting hardware entropy for NIST validation...")

    result = entropy_client.submit_entropy()

    if result:
        print(f"\n{'✓' if result.passed else '✗'} Validation Result:")
        print(f"  Status: {'PASSED' if result.passed else 'FAILED'}")
        print(f"  Quality Score: {result.quality_score:.1f}/100")
        print(f"  Entropy Estimate: {result.entropy_estimate:.2f} bits/byte")
        print(f"  Reputation Impact: {result.reputation_impact:+.1f}")

        # Show quality rating
        if result.is_excellent:
            print(f"  Rating: ⭐⭐⭐ Excellent")
        elif result.is_acceptable:
            print(f"  Rating: ⭐⭐ Acceptable")
        else:
            print(f"  Rating: ⭐ Needs Attention")

        # Show test breakdown if failed
        if not result.passed and result.tests:
            print(f"\n  📋 Test Breakdown:")
            for test_name, test_data in result.tests.items():
                if isinstance(test_data, dict):
                    passed = test_data.get("pass", True)
                    status = "✓" if passed else "✗"
                    print(
                        f"    {status} {test_name}: {test_data.get('description', '')}"
                    )

        # Show history
        if result.total_samples > 1:
            print(f"\n  📈 Historical Stats:")
            print(f"    Total Samples: {result.total_samples}")
            print(f"    Pass Rate: {result.pass_rate * 100:.1f}%")
            print(f"    Average Quality: {result.avg_quality:.1f}")

        # Show recommendation if provided
        if result.recommendation:
            print(f"\n  💡 Recommendation: {result.recommendation}")

    else:
        print(f"✗ Entropy submission failed (bootstrap server unreachable?)")
        print(f"  Falling back to local validation...")

        # Demonstrate local fallback
        entropy_bytes = entropy_client.read_hardware_entropy()
        if entropy_bytes:
            is_valid, quality = entropy_client.validate_local(entropy_bytes)
            print(f"  Local Validation: {'PASSED' if is_valid else 'FAILED'}")
            print(f"  Local Quality Estimate: {quality:.1f}/100")


def demo_reputation_tracking(node_id: str):
    """
    Demonstrate reputation tracking and queries

    Args:
        node_id: Node identifier
    """
    print_section("Step 3: Reputation Tracking")

    entropy_client = get_entropy_client(node_id=node_id)

    # Query reputation
    print("\n🏆 Querying node reputation...")
    reputation = entropy_client.get_reputation()

    if reputation:
        print(f"  Node ID: {reputation.get('node_id')}")
        print(f"  Reputation Score: {reputation.get('reputation_score'):.1f}")
        print(f"  Trust Level: {reputation.get('trust_level')}")
        print(f"  Network Standing: {reputation.get('network_standing')}")
        print(f"  Incident Count: {reputation.get('incident_count', 0)}")

        # Entropy quality stats
        entropy_qual = reputation.get("entropy_quality", {})
        if entropy_qual:
            print(f"\n  🔬 Entropy Quality:")
            print(f"    Verified: {'✓' if entropy_qual.get('verified') else '✗'}")
            print(f"    Quality Score: {entropy_qual.get('quality_score', 0):.1f}")
    else:
        print(f"  ⚠️  Could not retrieve reputation (not registered or network issue)")


def demo_entropy_history(node_id: str):
    """
    Demonstrate entropy history retrieval

    Args:
        node_id: Node identifier
    """
    print_section("Step 4: Entropy History Analysis")

    entropy_client = get_entropy_client(node_id=node_id)

    # Get recent history
    print("\n📜 Retrieving entropy submission history...")
    history = entropy_client.get_entropy_history(limit=10)

    if history:
        print(f"  Total Submissions: {history.get('total_submissions', 0)}")

        summary = history.get("summary", {})
        if summary:
            print(f"\n  📊 Summary:")
            print(f"    Pass Rate: {summary.get('pass_rate', 0) * 100:.1f}%")
            print(f"    Average Quality: {summary.get('avg_quality', 0):.1f}")
            print(f"    Trend: {summary.get('trend', 'unknown')}")

        entries = history.get("entries", [])
        if entries:
            print(f"\n  📋 Recent Submissions (last {len(entries)}):")
            for i, entry in enumerate(entries[:5], 1):
                status = "✓" if entry.get("validation_result") else "✗"
                quality = entry.get("quality_score", 0)
                timestamp = time.ctime(entry.get("timestamp", 0))
                print(f"    {i}. {status} Quality: {quality:.1f}, Time: {timestamp}")
    else:
        print(f"  ⚠️  Could not retrieve history")


def demo_periodic_submission(node_id: str, interval: int = 10, count: int = 3):
    """
    Demonstrate periodic entropy submission (like in production)

    Args:
        node_id: Node identifier
        interval: Seconds between submissions
        count: Number of submissions to make
    """
    print_section(f"Step 5: Periodic Submission ({count} times, every {interval}s)")

    entropy_client = get_entropy_client(node_id=node_id)

    for i in range(count):
        print(f"\n🔄 Submission {i+1}/{count}...")

        result = entropy_client.submit_entropy()

        if result:
            status = "✓" if result.passed else "✗"
            print(
                f"  {status} Quality: {result.quality_score:.1f}, "
                f"Entropy: {result.entropy_estimate:.2f} bits/byte"
            )
        else:
            print(f"  ⚠️  Submission failed, cached for retry")

        # Wait before next submission (except for last one)
        if i < count - 1:
            print(f"  ⏳ Waiting {interval}s...")
            time.sleep(interval)

    # Show final stats
    stats = entropy_client.get_stats()
    print(f"\n📈 Final Statistics:")
    print(f"  Total Submissions: {stats['submissions_total']}")
    print(f"  Passed: {stats['submissions_passed']}")
    print(f"  Failed: {stats['submissions_failed']}")
    print(f"  Pass Rate: {stats['pass_rate'] * 100:.1f}%")
    print(f"  Cached (failed): {stats['cached_submissions']}")

    # Demonstrate retry of cached submissions
    if stats["cached_submissions"] > 0:
        print(f"\n🔄 Retrying {stats['cached_submissions']} cached submissions...")
        retry_count = entropy_client.retry_cached_submissions()
        print(f"  ✓ Successfully resubmitted {retry_count} cached entries")


def main():
    """Run complete entropy validation demo"""
    print("=" * 70)
    print("  PiSecure Entropy Validation & Node Registration Demo")
    print("=" * 70)
    print("\n🔐 This demo shows how to:")
    print("  1. Register node with bootstrap server")
    print("  2. Submit hardware entropy for NIST validation")
    print("  3. Track node reputation")
    print("  4. Query entropy history")
    print("  5. Handle automatic retry and caching")
    print()

    # Generate unique node ID for this demo
    import socket

    hostname = socket.gethostname()
    node_id = f"demo-{hostname}-{int(time.time()) % 10000}"
    print(f"🆔 Demo Node ID: {node_id}")
    print(f"🌐 Network: Testnet")
    print()

    try:
        # Step 1: Register node
        registered = demo_node_registration(node_id)

        if not registered:
            print("\n⚠️  Skipping remaining demos (registration failed)")
            print("   This is expected if bootstrap server is unreachable")
            return

        # Wait a moment after registration
        time.sleep(2)

        # Step 2: Submit entropy
        demo_entropy_submission(node_id)

        # Wait before querying (give server time to process)
        time.sleep(2)

        # Step 3: Check reputation
        demo_reputation_tracking(node_id)

        # Step 4: View history
        demo_entropy_history(node_id)

        # Step 5: Periodic submission (commented out by default - takes time)
        # Uncomment to see periodic submission in action:
        # demo_periodic_submission(node_id, interval=10, count=3)

        print_section("Demo Complete!")
        print("\n✅ All demonstrations completed successfully!")
        print("\n📚 Next Steps:")
        print("  • Integrate entropy validation into your mining workflow")
        print("  • Set up automatic hourly submissions")
        print("  • Monitor reputation score in your dashboard")
        print("  • Configure alerts for low entropy quality")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
