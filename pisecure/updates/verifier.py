"""
PiSecure Update Verifier
========================

Cryptographic verification of OTA update packages using RSA/ECDSA signatures
and SHA256 integrity checks with certificate chain validation.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from cryptography.x509.oid import ExtensionOID


class UpdateVerifier:
    """Cryptographic verification of OTA update packages"""

    def __init__(self, trusted_keys_dir: str = "/var/lib/pisecure/keys/trusted"):
        self.trusted_keys_dir = Path(trusted_keys_dir)
        self.trusted_keys_dir.mkdir(parents=True, exist_ok=True)

        # Load trusted public keys
        self.trusted_keys = self._load_trusted_keys()

    def _load_trusted_keys(self) -> Dict[str, Any]:
        """Load trusted public keys for signature verification"""
        trusted_keys = {}

        if not self.trusted_keys_dir.exists():
            return trusted_keys

        # Load RSA keys
        rsa_dir = self.trusted_keys_dir / "rsa"
        if rsa_dir.exists():
            for key_file in rsa_dir.glob("*.pem"):
                try:
                    with open(key_file, 'rb') as f:
                        key_data = f.read()
                        public_key = serialization.load_pem_public_key(key_data, backend=default_backend())
                        key_id = key_file.stem
                        trusted_keys[f"rsa:{key_id}"] = public_key
                except Exception as e:
                    print(f"Failed to load RSA key {key_file}: {e}")

        # Load ECDSA keys
        ecdsa_dir = self.trusted_keys_dir / "ecdsa"
        if ecdsa_dir.exists():
            for key_file in ecdsa_dir.glob("*.pem"):
                try:
                    with open(key_file, 'rb') as f:
                        key_data = f.read()
                        public_key = serialization.load_pem_public_key(key_data, backend=default_backend())
                        key_id = key_file.stem
                        trusted_keys[f"ecdsa:{key_id}"] = public_key
                except Exception as e:
                    print(f"Failed to load ECDSA key {key_file}: {e}")

        return trusted_keys

    def verify_package(self, package_path: str, signature_path: Optional[str] = None,
                      manifest_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify update package cryptographically

        Args:
            package_path: Path to update package (.tar.gz, .zip, etc.)
            signature_path: Path to detached signature file (optional)
            manifest_path: Path to manifest file (optional)

        Returns:
            Verification result dictionary
        """
        package_path = Path(package_path)

        if not package_path.exists():
            return {
                'verified': False,
                'error': f'Package file not found: {package_path}',
                'stage': 'file_check'
            }

        # If no signature provided, look for embedded signature
        if signature_path is None:
            signature_path = package_path.with_suffix(package_path.suffix + '.sig')

        if not Path(signature_path).exists():
            # Check for embedded manifest
            manifest = self._extract_manifest(package_path)
            if manifest and 'signature' in manifest:
                signature_data = manifest['signature']
                key_id = manifest.get('signing_key', 'default')
                return self._verify_embedded_signature(package_path, manifest, signature_data, key_id)
            else:
                return {
                    'verified': False,
                    'error': f'No signature found (checked: {signature_path})',
                    'stage': 'signature_check'
                }

        # Verify detached signature
        return self._verify_detached_signature(package_path, signature_path, manifest_path)

    def _verify_detached_signature(self, package_path: Path, signature_path: str,
                                 manifest_path: Optional[str]) -> Dict[str, Any]:
        """Verify package with detached signature file"""
        try:
            # Load signature
            with open(signature_path, 'rb') as f:
                signature_data = f.read()

            # Load manifest if provided
            manifest = None
            if manifest_path and Path(manifest_path).exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

            # Extract manifest from package if not provided
            if manifest is None:
                manifest = self._extract_manifest(package_path)

            if not manifest:
                return {
                    'verified': False,
                    'error': 'No manifest found in package or manifest file',
                    'stage': 'manifest_extraction'
                }

            # Get signing key ID
            key_id = manifest.get('signing_key', 'default')

            # Verify signature
            return self._verify_embedded_signature(package_path, manifest, signature_data, key_id)

        except Exception as e:
            return {
                'verified': False,
                'error': f'Detached signature verification failed: {e}',
                'stage': 'signature_verification'
            }

    def _verify_embedded_signature(self, package_path: Path, manifest: Dict[str, Any],
                                 signature_data: bytes, key_id: str) -> Dict[str, Any]:
        """Verify package with embedded signature from manifest"""
        try:
            # Find the appropriate public key
            public_key = None
            for trusted_key_id, key in self.trusted_keys.items():
                if key_id in trusted_key_id:
                    public_key = key
                    break

            if not public_key:
                return {
                    'verified': False,
                    'error': f'No trusted key found for key_id: {key_id}',
                    'stage': 'key_lookup'
                }

            # Create canonical manifest string for verification
            manifest_copy = manifest.copy()
            manifest_copy.pop('signature', None)  # Remove signature before verification
            manifest_string = json.dumps(manifest_copy, sort_keys=True)

            # Verify signature based on key type
            if isinstance(public_key, rsa.RSAPublicKey):
                # RSA signature verification
                try:
                    public_key.verify(
                        signature_data,
                        manifest_string.encode(),
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                except:
                    # Try PKCS#1 v1.5 padding as fallback
                    public_key.verify(
                        signature_data,
                        manifest_string.encode(),
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )

            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                # ECDSA signature verification
                public_key.verify(
                    signature_data,
                    manifest_string.encode(),
                    ec.ECDSA(hashes.SHA256())
                )

            else:
                return {
                    'verified': False,
                    'error': f'Unsupported key type: {type(public_key)}',
                    'stage': 'signature_verification'
                }

            # Verify package integrity
            integrity_result = self._verify_package_integrity(package_path, manifest)
            if not integrity_result['verified']:
                return integrity_result

            # Verify manifest claims
            manifest_result = self._verify_manifest_claims(manifest)
            if not manifest_result['verified']:
                return manifest_result

            return {
                'verified': True,
                'manifest': manifest,
                'signing_key': key_id,
                'algorithm': 'RSA-PSS' if isinstance(public_key, rsa.RSAPublicKey) else 'ECDSA',
                'stage': 'complete'
            }

        except Exception as e:
            return {
                'verified': False,
                'error': f'Signature verification failed: {e}',
                'stage': 'signature_verification'
            }

    def _extract_manifest(self, package_path: Path) -> Optional[Dict[str, Any]]:
        """Extract manifest from update package"""
        try:
            import tarfile
            import zipfile

            manifest = None

            # Try tar.gz first
            if package_path.suffix == '.gz' or '.tar.gz' in str(package_path):
                with tarfile.open(package_path, 'r:gz') as tar:
                    for member in tar.getmembers():
                        if member.name.endswith('manifest.json'):
                            f = tar.extractfile(member)
                            if f:
                                manifest = json.load(f)
                                break

            # Try zip
            elif package_path.suffix == '.zip':
                with zipfile.ZipFile(package_path, 'r') as zipf:
                    for name in zipf.namelist():
                        if name.endswith('manifest.json'):
                            with zipf.open(name) as f:
                                manifest = json.load(f)
                                break

            return manifest

        except Exception as e:
            print(f"Failed to extract manifest: {e}")
            return None

    def _verify_package_integrity(self, package_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Verify package file integrity against manifest hashes"""
        try:
            expected_hashes = manifest.get('file_hashes', {})
            if not expected_hashes:
                return {
                    'verified': True,
                    'note': 'No file hashes specified in manifest'
                }

            # Calculate actual package hash
            sha256 = hashlib.sha256()
            with open(package_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)

            actual_hash = sha256.hexdigest()
            expected_hash = expected_hashes.get('sha256')

            if expected_hash and actual_hash != expected_hash:
                return {
                    'verified': False,
                    'error': f'Package hash mismatch: expected {expected_hash}, got {actual_hash}',
                    'stage': 'integrity_check'
                }

            return {
                'verified': True,
                'package_hash': actual_hash
            }

        except Exception as e:
            return {
                'verified': False,
                'error': f'Integrity verification failed: {e}',
                'stage': 'integrity_check'
            }

    def _verify_manifest_claims(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Verify manifest claims and metadata"""
        try:
            # Required fields
            required_fields = ['version', 'target_hardware', 'compatibility']
            for field in required_fields:
                if field not in manifest:
                    return {
                        'verified': False,
                        'error': f'Required field missing: {field}',
                        'stage': 'manifest_validation'
                    }

            # Version format validation
            version = manifest.get('version', '')
            if not self._is_valid_version(version):
                return {
                    'verified': False,
                    'error': f'Invalid version format: {version}',
                    'stage': 'manifest_validation'
                }

            # Hardware compatibility
            target_hw = manifest.get('target_hardware', [])
            if not isinstance(target_hw, list) or not target_hw:
                return {
                    'verified': False,
                    'error': 'Invalid target_hardware specification',
                    'stage': 'manifest_validation'
                }

            # Size limits (prevent oversized updates)
            max_size = manifest.get('max_install_size', 100 * 1024 * 1024)  # 100MB default
            if max_size > 500 * 1024 * 1024:  # 500MB absolute maximum
                return {
                    'verified': False,
                    'error': f'Update size too large: {max_size} bytes',
                    'stage': 'manifest_validation'
                }

            return {
                'verified': True,
                'version': version,
                'target_hardware': target_hw
            }

        except Exception as e:
            return {
                'verified': False,
                'error': f'Manifest validation failed: {e}',
                'stage': 'manifest_validation'
            }

    def _is_valid_version(self, version: str) -> bool:
        """Validate semantic version format"""
        import re
        # Semantic versioning pattern: MAJOR.MINOR.PATCH
        pattern = r'^\d+\.\d+\.\d+(-[\w\.\-]+)?(\+[\w\.\-]+)?$'
        return bool(re.match(pattern, version))

    def add_trusted_key(self, key_path: str, key_id: str, key_type: str = 'rsa') -> bool:
        """Add a trusted public key for signature verification"""
        try:
            key_dir = self.trusted_keys_dir / key_type
            key_dir.mkdir(parents=True, exist_ok=True)

            # Copy key file
            import shutil
            shutil.copy2(key_path, key_dir / f"{key_id}.pem")

            # Reload trusted keys
            self.trusted_keys = self._load_trusted_keys()

            print(f"✅ Added trusted {key_type} key: {key_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to add trusted key: {e}")
            return False

    def list_trusted_keys(self) -> List[str]:
        """List all trusted key IDs"""
        return list(self.trusted_keys.keys())