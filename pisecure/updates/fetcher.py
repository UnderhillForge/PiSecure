"""
PiSecure Update Fetcher
=======================

Decentralized update distribution using IPFS with on-chain hash verification.
Supports P2P swarming, multi-source fetching, and integrity validation.
"""

import hashlib
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse


class UpdateFetcher:
    """Decentralized update package fetching with IPFS integration"""

    def __init__(self, cache_dir: str = "/var/lib/pisecure/updates/cache",
                 blockchain=None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # IPFS configuration
        self.ipfs_gateways = [
            'https://ipfs.io/ipfs/',
            'https://gateway.pinata.cloud/ipfs/',
            'https://cloudflare-ipfs.com/ipfs/',
            'https://dweb.link/ipfs/',
            'https://gateway.ipfs.io/ipfs/'
        ]

        # Blockchain reference for on-chain verification
        self.blockchain = blockchain

        # Download sources (can be extended)
        self.sources = {
            'ipfs': self._fetch_from_ipfs,
            'http': self._fetch_from_http,
            'https': self._fetch_from_http
        }

    def fetch_update(self, update_hash: str, expected_size: Optional[int] = None,
                    timeout: int = 300) -> Dict[str, Any]:
        """
        Fetch update package from decentralized sources

        Args:
            update_hash: IPFS hash or blockchain transaction hash
            expected_size: Expected file size for validation
            timeout: Download timeout in seconds

        Returns:
            Fetch result with local path if successful
        """
        # Check cache first
        cached_path = self._check_cache(update_hash)
        if cached_path:
            return {
                'fetched': True,
                'cached': True,
                'local_path': str(cached_path),
                'size': cached_path.stat().st_size,
                'source': 'cache'
            }

        # Try blockchain lookup first (for on-chain registered updates)
        if self.blockchain:
            blockchain_info = self._lookup_blockchain(update_hash)
            if blockchain_info:
                return self._fetch_from_blockchain_info(blockchain_info, timeout)

        # Try IPFS directly
        ipfs_result = self._fetch_from_ipfs(update_hash, expected_size, timeout)
        if ipfs_result['fetched']:
            return ipfs_result

        # Try other sources
        for source_type, fetch_func in self.sources.items():
            if source_type == 'ipfs':  # Already tried
                continue

            try:
                result = fetch_func(update_hash, expected_size, timeout)
                if result['fetched']:
                    return result
            except Exception as e:
                print(f"Failed to fetch from {source_type}: {e}")
                continue

        return {
            'fetched': False,
            'error': 'All sources failed',
            'attempted_sources': list(self.sources.keys())
        }

    def _lookup_blockchain(self, update_hash: str) -> Optional[Dict[str, Any]]:
        """Lookup update information from blockchain"""
        try:
            # Search for update registration transactions
            for block in reversed(self.blockchain.chain[-100:]):  # Last 100 blocks
                for tx in block.transactions:
                    if (tx.get('type') in ['update_registration', 'ota_update'] and
                        tx.get('update_hash') == update_hash):

                        return {
                            'hash': tx.get('update_hash'),
                            'ipfs_hash': tx.get('ipfs_hash'),
                            'http_urls': tx.get('http_urls', []),
                            'size': tx.get('size'),
                            'version': tx.get('version'),
                            'publisher': tx.get('publisher'),
                            'signature': tx.get('signature'),
                            'block_height': block.index,
                            'timestamp': block.timestamp
                        }

            # Try direct hash lookup
            tx = self.blockchain.get_transaction(update_hash)
            if tx and tx.get('type') in ['update_registration', 'ota_update']:
                return tx

        except Exception as e:
            print(f"Blockchain lookup failed: {e}")

        return None

    def _fetch_from_blockchain_info(self, info: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Fetch using information from blockchain"""
        # Try IPFS hash first
        if 'ipfs_hash' in info:
            result = self._fetch_from_ipfs(info['ipfs_hash'], info.get('size'), timeout)
            if result['fetched']:
                return result

        # Try HTTP URLs
        if 'http_urls' in info:
            for url in info['http_urls']:
                try:
                    result = self._fetch_from_http(url, info.get('size'), timeout)
                    if result['fetched']:
                        return result
                except Exception as e:
                    print(f"Failed to fetch from {url}: {e}")
                    continue

        return {
            'fetched': False,
            'error': 'Blockchain sources failed'
        }

    def _fetch_from_ipfs(self, ipfs_hash: str, expected_size: Optional[int] = None,
                        timeout: int = 300) -> Dict[str, Any]:
        """Fetch package from IPFS network"""
        temp_path = None

        try:
            # Clean IPFS hash (remove any prefix)
            if 'ipfs://' in ipfs_hash:
                ipfs_hash = ipfs_hash.split('ipfs://', 1)[1]
            elif '/' in ipfs_hash and not ipfs_hash.startswith('Qm'):
                # Handle full IPFS URLs
                parts = ipfs_hash.split('/')
                ipfs_hash = parts[parts.index('ipfs') + 1] if 'ipfs' in parts else ipfs_hash

            # Try multiple IPFS gateways
            for gateway in self.ipfs_gateways:
                try:
                    url = f"{gateway}{ipfs_hash}"
                    print(f"Fetching from IPFS: {url}")

                    response = requests.get(url, timeout=timeout, stream=True)
                    response.raise_for_status()

                    # Check content length if available
                    content_length = response.headers.get('content-length')
                    if content_length and expected_size:
                        if abs(int(content_length) - expected_size) > 1024:  # 1KB tolerance
                            print(f"Size mismatch: expected {expected_size}, got {content_length}")
                            continue

                    # Create temporary file
                    temp_path = self.cache_dir / f"temp_{ipfs_hash}"
                    temp_path.parent.mkdir(parents=True, exist_ok=True)

                    # Download with progress
                    downloaded = 0
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                # Progress indicator
                                if downloaded % (1024 * 1024) == 0:  # Every MB
                                    print(f"Downloaded: {downloaded / (1024*1024):.1f} MB")

                    # Verify size if expected
                    if expected_size and abs(temp_path.stat().st_size - expected_size) > 1024:
                        print(f"Downloaded size mismatch: {temp_path.stat().st_size} vs {expected_size}")
                        temp_path.unlink()
                        continue

                    # Verify hash integrity
                    actual_hash = self._calculate_hash(temp_path)
                    if actual_hash != ipfs_hash:
                        print(f"Hash mismatch: expected {ipfs_hash}, got {actual_hash}")
                        temp_path.unlink()
                        continue

                    # Move to cache
                    cache_path = self._move_to_cache(temp_path, ipfs_hash)
                    return {
                        'fetched': True,
                        'local_path': str(cache_path),
                        'size': cache_path.stat().st_size,
                        'source': 'ipfs',
                        'gateway': gateway,
                        'hash': actual_hash
                    }

                except Exception as e:
                    print(f"IPFS gateway {gateway} failed: {e}")
                    if temp_path and temp_path.exists():
                        temp_path.unlink()
                    continue

            return {
                'fetched': False,
                'error': 'All IPFS gateways failed',
                'ipfs_hash': ipfs_hash
            }

        except Exception as e:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            return {
                'fetched': False,
                'error': f'IPFS fetch failed: {e}',
                'ipfs_hash': ipfs_hash
            }

    def _fetch_from_http(self, url: str, expected_size: Optional[int] = None,
                        timeout: int = 300) -> Dict[str, Any]:
        """Fetch package from HTTP/HTTPS URL"""
        temp_path = None

        try:
            print(f"Fetching from HTTP: {url}")

            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and expected_size:
                if abs(int(content_length) - expected_size) > 1024:
                    return {
                        'fetched': False,
                        'error': f'Size mismatch: expected {expected_size}, server reports {content_length}'
                    }

            # Create temporary file
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            temp_path = self.cache_dir / f"temp_http_{url_hash}"

            # Download
            downloaded = 0
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # Verify size
            if expected_size and abs(temp_path.stat().st_size - expected_size) > 1024:
                temp_path.unlink()
                return {
                    'fetched': False,
                    'error': f'Downloaded size mismatch: {temp_path.stat().st_size} vs {expected_size}'
                }

            # Calculate hash for caching
            file_hash = self._calculate_hash(temp_path)
            cache_path = self._move_to_cache(temp_path, file_hash)

            return {
                'fetched': True,
                'local_path': str(cache_path),
                'size': cache_path.stat().st_size,
                'source': 'http',
                'url': url,
                'hash': file_hash
            }

        except Exception as e:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            return {
                'fetched': False,
                'error': f'HTTP fetch failed: {e}',
                'url': url
            }

    def _check_cache(self, file_hash: str) -> Optional[Path]:
        """Check if file is already cached"""
        cache_path = self.cache_dir / file_hash
        if cache_path.exists():
            # Verify integrity
            if self._calculate_hash(cache_path) == file_hash:
                return cache_path

            # Remove corrupted cache
            cache_path.unlink()

        return None

    def _move_to_cache(self, temp_path: Path, file_hash: str) -> Path:
        """Move downloaded file to cache with hash-based name"""
        cache_path = self.cache_dir / file_hash
        temp_path.rename(cache_path)
        return cache_path

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_update_on_chain(self, update_info: Dict[str, Any]) -> Optional[str]:
        """Register update information on blockchain"""
        if not self.blockchain:
            print("No blockchain connection - cannot register update")
            return None

        try:
            # Create update registration transaction
            tx = {
                'type': 'update_registration',
                'update_hash': update_info.get('hash'),
                'ipfs_hash': update_info.get('ipfs_hash'),
                'http_urls': update_info.get('http_urls', []),
                'version': update_info.get('version'),
                'size': update_info.get('size'),
                'publisher': update_info.get('publisher', 'pisecure'),
                'target_hardware': update_info.get('target_hardware', ['raspberry_pi']),
                'timestamp': time.time(),
                'description': update_info.get('description', ''),
                'changelog': update_info.get('changelog', '')
            }

            # Add to blockchain
            tx_hash = self.blockchain.add_transaction(tx)

            print(f"✅ Update registered on blockchain: {tx_hash}")
            return tx_hash

        except Exception as e:
            print(f"❌ Failed to register update: {e}")
            return None

    def list_cached_updates(self) -> List[Dict[str, Any]]:
        """List all cached update packages"""
        cached = []
        try:
            for cache_file in self.cache_dir.glob('*'):
                if cache_file.is_file() and not cache_file.name.startswith('temp_'):
                    stat = cache_file.stat()
                    cached.append({
                        'hash': cache_file.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'path': str(cache_file)
                    })
        except Exception as e:
            print(f"Failed to list cache: {e}")

        return cached

    def cleanup_cache(self, max_age_days: int = 30, max_size_mb: int = 500) -> Dict[str, Any]:
        """Clean up old cached files"""
        try:
            cleaned = {'removed_files': 0, 'freed_bytes': 0}
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

            total_size = 0
            files_by_age = []

            # Analyze cache
            for cache_file in self.cache_dir.glob('*'):
                if cache_file.is_file():
                    stat = cache_file.stat()
                    total_size += stat.st_size
                    files_by_age.append((stat.st_mtime, stat.st_size, cache_file))

            # Sort by age (oldest first)
            files_by_age.sort()

            # Remove old files
            for mtime, size, file_path in files_by_age:
                if mtime < cutoff_time or total_size > (max_size_mb * 1024 * 1024):
                    file_path.unlink()
                    cleaned['removed_files'] += 1
                    cleaned['freed_bytes'] += size
                    total_size -= size
                else:
                    break

            return {**cleaned, 'success': True}

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def add_ipfs_gateway(self, gateway_url: str) -> bool:
        """Add custom IPFS gateway"""
        try:
            parsed = urlparse(gateway_url)
            if parsed.scheme in ['http', 'https'] and parsed.netloc:
                if gateway_url not in self.ipfs_gateways:
                    self.ipfs_gateways.insert(0, gateway_url.rstrip('/') + '/')
                    return True
        except:
            pass
        return False

    def get_update_info(self, update_hash: str) -> Optional[Dict[str, Any]]:
        """Get update information from blockchain"""
        return self._lookup_blockchain(update_hash)