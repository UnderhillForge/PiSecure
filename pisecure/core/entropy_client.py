#!/usr/bin/env python3
"""
PiSecure Bootstrap Entropy Validation Client

Handles submission of hardware RNG entropy samples to bootstrap server
for NIST SP 800-90B validation with automatic retry, caching, and reputation tracking.
"""

import time
import json
import logging
import hashlib
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class EntropyValidationResult:
    """Result of entropy validation from bootstrap server"""

    def __init__(self, response_data: Dict[str, Any]):
        self.raw_data = response_data
        self.validation_result = response_data.get("validation_result", False)
        self.quality_score = response_data.get("quality_score", 0.0)
        self.entropy_estimate = response_data.get("entropy_estimate_bits_per_byte", 0.0)
        self.reputation_impact = response_data.get("reputation_impact", 0.0)
        self.timestamp = response_data.get("timestamp", time.time())

        # Test results breakdown
        self.tests = response_data.get("tests", {})

        # History and trends
        history = response_data.get("node_entropy_history", {})
        self.total_samples = history.get("total_samples", 0)
        self.pass_rate = history.get("pass_rate", 0.0)
        self.avg_quality = history.get("avg_quality", 0.0)

        # Recommendations
        self.recommendation = response_data.get("recommendation", "")
        self.severity = response_data.get("severity", "info")

    @property
    def passed(self) -> bool:
        """Check if validation passed"""
        return self.validation_result

    @property
    def is_excellent(self) -> bool:
        """Quality score 80-100"""
        return self.quality_score >= 80

    @property
    def is_acceptable(self) -> bool:
        """Quality score 50-79"""
        return 50 <= self.quality_score < 80

    @property
    def needs_attention(self) -> bool:
        """Quality score < 50"""
        return self.quality_score < 50

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"<EntropyValidation {status} score={self.quality_score:.1f} entropy={self.entropy_estimate:.2f}>"


class BootstrapEntropyClient:
    """
    Client for submitting entropy to bootstrap server with:
    - Automatic retry with exponential backoff
    - Caching of failed submissions
    - Rate limit handling
    - Reputation tracking
    - Fallback to local validation
    """

    def __init__(
        self,
        node_id: str,
        bootstrap_url: str = "https://bootstrap.pisecure.org",
        network: str = "mainnet",
        cache_dir: str = "/var/lib/pisecure/entropy_cache",
    ):
        """
        Initialize entropy client

        Args:
            node_id: Unique node identifier
            bootstrap_url: Bootstrap server base URL
            network: 'mainnet' or 'testnet'
            cache_dir: Directory for caching failed submissions
        """
        self.node_id = node_id
        self.bootstrap_url = bootstrap_url
        self.network = network
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Endpoints (network specified as query parameter)
        self.entropy_endpoint = f"{bootstrap_url}/api/v1/hardware/entropy"
        self.reputation_endpoint = f"{bootstrap_url}/api/v1/nodes/{node_id}/reputation"
        self.history_endpoint = (
            f"{bootstrap_url}/api/v1/nodes/{node_id}/entropy-history"
        )

        # Configure session with retry logic
        self.session = self._create_session()

        # Stats
        self.submissions_count = 0
        self.submissions_passed = 0
        self.submissions_failed = 0
        self.last_submission_time = None
        self.last_quality_score = None

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()

        # Retry strategy for transient errors
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=2,  # 2s, 4s, 8s
            allowed_methods=["POST", "GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def read_hardware_entropy(self, num_bytes: int = 32) -> Optional[bytes]:
        """
        Read entropy from hardware RNG

        Args:
            num_bytes: Number of bytes to read (default: 32)

        Returns:
            Entropy bytes or None if failed
        """
        import os

        if os.environ.get("PISECURE_MOCK_HARDWARE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            raise RuntimeError(
                "PISECURE_MOCK_HARDWARE is not allowed. Refusing to fake entropy."
            )

        try:
            with open("/dev/hwrng", "rb") as hwrng:
                entropy = hwrng.read(num_bytes)

                if len(entropy) != num_bytes:
                    logger.error(f"Read {len(entropy)} bytes, expected {num_bytes}")
                    return None

                return entropy

        except IOError as e:
            logger.error(f"Failed to read /dev/hwrng: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading entropy: {e}")
            return None

    def submit_entropy(
        self, entropy_bytes: Optional[bytes] = None, metadata: Optional[Dict] = None
    ) -> Optional[EntropyValidationResult]:
        """
        Submit entropy sample to bootstrap server for validation

        Args:
            entropy_bytes: 32-byte entropy sample (auto-read if None)
            metadata: Optional metadata about collection

        Returns:
            EntropyValidationResult or None if submission failed
        """
        # Read entropy if not provided
        if entropy_bytes is None:
            entropy_bytes = self.read_hardware_entropy()
            if entropy_bytes is None:
                return None

        # Validate entropy length
        if len(entropy_bytes) != 32:
            logger.error(f"Invalid entropy length: {len(entropy_bytes)}, expected 32")
            return None

        # Build request payload
        payload = {
            "node_id": self.node_id,
            "entropy_hex": entropy_bytes.hex(),
            "network": self.network,
            "timestamp": time.time(),
        }

        if metadata:
            payload["metadata"] = metadata

        # Submit to bootstrap (with network query parameter)
        try:
            response = self.session.post(
                self.entropy_endpoint,
                params={"network": self.network},
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"PiSecure-Miner/{self.node_id}",
                },
                timeout=10,
            )

            # Handle response
            if response.status_code == 200:
                result = EntropyValidationResult(response.json())
                self._handle_success(result)
                return result

            elif response.status_code == 400:
                # Validation failed
                result = EntropyValidationResult(response.json())
                self._handle_failure(result, entropy_bytes)
                return result

            elif response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get("Retry-After", 3600))
                logger.warning(f"Rate limited, retry after {retry_after}s")
                self._cache_submission(payload)
                return None

            elif response.status_code == 403:
                # Node not registered
                logger.error("Node not registered with bootstrap server")
                logger.info("Register at: /api/v1/nodes/register")
                return None

            else:
                # Other error
                logger.error(
                    f"Unexpected status {response.status_code}: {response.text}"
                )
                self._cache_submission(payload)
                return None

        except requests.exceptions.Timeout:
            logger.warning("Bootstrap server timeout, caching for later")
            self._cache_submission(payload)
            return None

        except requests.exceptions.ConnectionError:
            logger.warning(
                "Bootstrap server unreachable, falling back to local validation"
            )
            self._cache_submission(payload)
            return None

        except Exception as e:
            logger.error(f"Entropy submission error: {e}")
            self._cache_submission(payload)
            return None

    def _handle_success(self, result: EntropyValidationResult):
        """Handle successful entropy validation"""
        self.submissions_count += 1
        self.submissions_passed += 1
        self.last_submission_time = time.time()
        self.last_quality_score = result.quality_score

        if result.is_excellent:
            logger.info(
                f"✓ Excellent entropy: quality={result.quality_score:.1f}, "
                f"entropy={result.entropy_estimate:.2f} bits/byte"
            )
        elif result.is_acceptable:
            logger.info(
                f"✓ Acceptable entropy: quality={result.quality_score:.1f}, "
                f"entropy={result.entropy_estimate:.2f} bits/byte"
            )
        else:
            logger.warning(
                f"⚠ Low quality entropy: quality={result.quality_score:.1f}, "
                f"entropy={result.entropy_estimate:.2f} bits/byte"
            )

    def _handle_failure(self, result: EntropyValidationResult, entropy_bytes: bytes):
        """Handle failed entropy validation"""
        self.submissions_count += 1
        self.submissions_failed += 1
        self.last_submission_time = time.time()
        self.last_quality_score = result.quality_score

        logger.warning(
            f"✗ Entropy validation failed: quality={result.quality_score:.1f}, "
            f"penalty={result.reputation_impact:.1f}, "
            f"severity={result.severity}"
        )

        if result.recommendation:
            logger.info(f"Recommendation: {result.recommendation}")

        # Log failed tests
        for test_name, test_result in result.tests.items():
            if isinstance(test_result, dict) and not test_result.get("pass", True):
                logger.warning(
                    f"  Failed: {test_name} - {test_result.get('description', '')}"
                )

    def _cache_submission(self, payload: Dict):
        """Cache failed submission for later retry"""
        try:
            cache_file = self.cache_dir / f"entropy_{int(time.time())}.json"
            with open(cache_file, "w") as f:
                json.dump(payload, f)
            logger.debug(f"Cached submission: {cache_file}")
        except Exception as e:
            logger.error(f"Failed to cache submission: {e}")

    def retry_cached_submissions(self) -> int:
        """
        Retry all cached submissions

        Returns:
            Number of successfully submitted cached entries
        """
        cache_files = sorted(self.cache_dir.glob("entropy_*.json"))
        success_count = 0

        for cache_file in cache_files:
            try:
                with open(cache_file, "r") as f:
                    payload = json.load(f)

                # Reconstruct entropy bytes from hex
                entropy_hex = payload.get("entropy_hex", "")
                entropy_bytes = bytes.fromhex(entropy_hex)

                # Attempt resubmission
                result = self.submit_entropy(entropy_bytes)

                if result and result.passed:
                    cache_file.unlink()  # Delete cached file on success
                    success_count += 1
                    logger.info(f"Resubmitted cached entropy: {cache_file.name}")

            except Exception as e:
                logger.error(f"Failed to retry {cache_file}: {e}")

        return success_count

    def get_reputation(self) -> Optional[Dict[str, Any]]:
        """
        Query current node reputation from bootstrap

        Returns:
            Reputation data or None if query failed
        """
        try:
            response = self.session.get(
                self.reputation_endpoint,
                params={"network": self.network},
                timeout=5,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Reputation query failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Reputation query error: {e}")
            return None

    def get_entropy_history(
        self, limit: int = 100, since: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get entropy submission history

        Args:
            limit: Maximum number of entries (default: 100, max: 1000)
            since: Unix timestamp to filter from

        Returns:
            History data or None if query failed
        """
        params = {"limit": min(limit, 1000), "network": self.network}
        if since:
            params["since"] = since

        try:
            response = self.session.get(self.history_endpoint, params=params, timeout=5)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"History query failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"History query error: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get client-side statistics"""
        pass_rate = (
            self.submissions_passed / self.submissions_count
            if self.submissions_count > 0
            else 0.0
        )

        return {
            "node_id": self.node_id,
            "network": self.network,
            "submissions_total": self.submissions_count,
            "submissions_passed": self.submissions_passed,
            "submissions_failed": self.submissions_failed,
            "pass_rate": pass_rate,
            "last_submission": self.last_submission_time,
            "last_quality_score": self.last_quality_score,
            "cached_submissions": len(list(self.cache_dir.glob("entropy_*.json"))),
        }

    def validate_local(self, entropy_bytes: bytes) -> Tuple[bool, float]:
        """
        Fallback local entropy validation (simple quality check)

        Args:
            entropy_bytes: Entropy sample to validate

        Returns:
            (is_valid, quality_estimate) tuple
        """
        if len(entropy_bytes) != 32:
            return False, 0.0

        # Check for patterns (should be random)
        unique_bytes = len(set(entropy_bytes))
        diversity_score = unique_bytes / 256.0  # 0.0 to 1.0

        # Check for repeating 4-byte chunks
        chunks = [entropy_bytes[i : i + 4] for i in range(0, len(entropy_bytes), 4)]
        unique_chunks = len(set(chunks))
        chunk_diversity = unique_chunks / len(chunks)  # Should be close to 1.0

        # Simple quality estimate (not NIST-compliant)
        quality_estimate = (diversity_score * 50) + (chunk_diversity * 50)

        # Pass if quality > 70
        is_valid = quality_estimate > 70

        return is_valid, quality_estimate


# Global singleton instance
_entropy_client: Optional[BootstrapEntropyClient] = None


def get_entropy_client(
    node_id: Optional[str] = None,
    bootstrap_url: Optional[str] = None,
    network: str = "mainnet",
) -> BootstrapEntropyClient:
    """
    Get or create global entropy client instance

    Args:
        node_id: Node identifier (required for first call)
        bootstrap_url: Bootstrap server URL (optional)
        network: 'mainnet' or 'testnet'

    Returns:
        BootstrapEntropyClient instance
    """
    global _entropy_client

    if _entropy_client is None:
        if node_id is None:
            raise ValueError("node_id required for first entropy client initialization")

        if bootstrap_url is None:
            # Auto-detect from environment or use default
            import os

            # Always use single bootstrap.pisecure.org domain with network query param
            bootstrap_url = "https://bootstrap.pisecure.org"

        _entropy_client = BootstrapEntropyClient(
            node_id=node_id, bootstrap_url=bootstrap_url, network=network
        )

    return _entropy_client
