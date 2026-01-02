"""
PiSecure OTA Update Authorization System
========================================

Cryptographic authorization ensuring only authorized developers can publish updates.
Implements multi-signature verification and blockchain-based key management.
"""

import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, utils
from cryptography.exceptions import InvalidSignature


class UpdateAuthority:
    """Manages authorized update publishers and their cryptographic keys"""

    def __init__(self, blockchain=None, config_file: str = "/etc/pisecure/update_auth.json"):
        self.blockchain = blockchain
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load or initialize authority configuration
        self.authorized_keys = self._load_authorized_keys()

    def _load_authorized_keys(self) -> Dict[str, Any]:
        """Load authorized public keys from blockchain or config"""
        try:
            if self.blockchain:
                # Load from blockchain (most secure)
                return self._load_keys_from_blockchain()
            else:
                # Fallback to local config
                if self.config_file.exists():
                    with open(self.config_file, 'r') as f:
                        return json.load(f)
        except Exception as e:
            print(f"Failed to load authorized keys: {e}")

        # Return minimal default (should be configured during setup)
        return {
            "version": "1.0",
            "threshold": 1,  # Number of signatures required
            "keys": {},
            "revoked_keys": []
        }

    def _load_keys_from_blockchain(self) -> Dict[str, Any]:
        """Load authorized keys from blockchain transactions"""
        authorized_keys = {
            "version": "1.0",
            "threshold": 1,
            "keys": {},
            "revoked_keys": []
        }

        try:
            # Scan recent blocks for authority registration transactions
            for block in reversed(self.blockchain.chain[-100:]):  # Last 100 blocks
                for tx in block.transactions:
                    if tx.get('type') == 'update_authority_registration':
                        auth_data = tx.get('authority_data', {})

                        # Update threshold if specified
                        if 'threshold' in auth_data:
                            authorized_keys['threshold'] = auth_data['threshold']

                        # Add authorized keys
                        if 'public_keys' in auth_data:
                            for key_id, key_data in auth_data['public_keys'].items():
                                if key_id not in authorized_keys['revoked_keys']:
                                    authorized_keys['keys'][key_id] = {
                                        'public_key': key_data['public_key'],
                                        'added_at': tx.get('timestamp', time.time()),
                                        'added_by': tx.get('publisher', 'system'),
                                        'permissions': key_data.get('permissions', ['sign_updates'])
                                    }

                    elif tx.get('type') == 'update_authority_revocation':
                        # Handle key revocation
                        revoked_key = tx.get('revoked_key_id')
                        if revoked_key:
                            authorized_keys['revoked_keys'].append(revoked_key)
                            # Remove from active keys if present
                            authorized_keys['keys'].pop(revoked_key, None)

        except Exception as e:
            print(f"Error loading keys from blockchain: {e}")

        return authorized_keys

    def register_authority_key(self, key_id: str, public_key_pem: str,
                             permissions: List[str] = None) -> Dict[str, Any]:
        """
        Register a new authorized update signing key

        Args:
            key_id: Unique identifier for the key
            public_key_pem: PEM-encoded public key
            permissions: List of permissions for this key

        Returns:
            Registration result
        """
        try:
            # Validate public key format
            try:
                serialization.load_pem_public_key(public_key_pem.encode())
            except Exception as e:
                return {'success': False, 'error': f'Invalid public key: {e}'}

            # Check if key already exists
            if key_id in self.authorized_keys['keys']:
                return {'success': False, 'error': 'Key ID already exists'}

            # Check if key is revoked
            if key_id in self.authorized_keys['revoked_keys']:
                return {'success': False, 'error': 'Key ID is revoked'}

            # Register on blockchain if available
            if self.blockchain:
                auth_tx = {
                    'type': 'update_authority_registration',
                    'authority_data': {
                        'public_keys': {
                            key_id: {
                                'public_key': public_key_pem,
                                'permissions': permissions or ['sign_updates']
                            }
                        }
                    },
                    'timestamp': time.time(),
                    'publisher': 'system'  # Should be authenticated user
                }

                tx_hash = self.blockchain.add_transaction(auth_tx)

                # Update local cache
                self.authorized_keys['keys'][key_id] = {
                    'public_key': public_key_pem,
                    'added_at': time.time(),
                    'added_by': 'system',
                    'permissions': permissions or ['sign_updates'],
                    'tx_hash': tx_hash
                }

                self._save_config()
                return {'success': True, 'tx_hash': tx_hash}

            else:
                # Local registration only
                self.authorized_keys['keys'][key_id] = {
                    'public_key': public_key_pem,
                    'added_at': time.time(),
                    'added_by': 'local',
                    'permissions': permissions or ['sign_updates']
                }

                self._save_config()
                return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def revoke_authority_key(self, key_id: str, reason: str = "") -> Dict[str, Any]:
        """Revoke an authorized update signing key"""
        try:
            if key_id not in self.authorized_keys['keys']:
                return {'success': False, 'error': 'Key not found'}

            # Register revocation on blockchain
            if self.blockchain:
                revoke_tx = {
                    'type': 'update_authority_revocation',
                    'revoked_key_id': key_id,
                    'reason': reason,
                    'timestamp': time.time(),
                    'publisher': 'system'
                }

                tx_hash = self.blockchain.add_transaction(revoke_tx)

                # Update local state
                self.authorized_keys['revoked_keys'].append(key_id)
                self.authorized_keys['keys'].pop(key_id, None)
                self._save_config()

                return {'success': True, 'tx_hash': tx_hash}
            else:
                # Local revocation only
                self.authorized_keys['revoked_keys'].append(key_id)
                self.authorized_keys['keys'].pop(key_id, None)
                self._save_config()

                return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def verify_update_signature(self, update_data: Dict[str, Any],
                               signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify that an update is authorized by checking signatures

        Args:
            update_data: Update manifest data
            signatures: List of {'key_id': str, 'signature': str} dicts

        Returns:
            Verification result
        """
        try:
            if not signatures:
                return {'authorized': False, 'error': 'No signatures provided'}

            # Canonicalize update data for signing
            canonical_data = self._canonicalize_update_data(update_data)
            data_to_verify = json.dumps(canonical_data, sort_keys=True).encode()

            valid_signatures = 0
            authorized_signers = []

            for sig_data in signatures:
                key_id = sig_data.get('key_id')
                signature_hex = sig_data.get('signature')

                if not key_id or not signature_hex:
                    continue

                # Check if key is authorized and not revoked
                if key_id not in self.authorized_keys['keys']:
                    continue

                if key_id in self.authorized_keys['revoked_keys']:
                    continue

                key_info = self.authorized_keys['keys'][key_id]
                if 'sign_updates' not in key_info.get('permissions', []):
                    continue

                # Load public key
                try:
                    public_key = serialization.load_pem_public_key(
                        key_info['public_key'].encode()
                    )
                except Exception:
                    continue

                # Verify signature
                try:
                    signature_bytes = bytes.fromhex(signature_hex)
                    public_key.verify(
                        signature_bytes,
                        data_to_verify,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )

                    valid_signatures += 1
                    authorized_signers.append(key_id)

                except InvalidSignature:
                    continue

            # Check threshold
            threshold = self.authorized_keys.get('threshold', 1)
            is_authorized = valid_signatures >= threshold

            return {
                'authorized': is_authorized,
                'valid_signatures': valid_signatures,
                'required_threshold': threshold,
                'authorized_signers': authorized_signers,
                'total_signatures_checked': len(signatures)
            }

        except Exception as e:
            return {
                'authorized': False,
                'error': str(e),
                'valid_signatures': 0,
                'required_threshold': self.authorized_keys.get('threshold', 1)
            }

    def _canonicalize_update_data(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create canonical representation of update data for signing"""
        # Remove signature-related fields to prevent circular signing
        canonical = update_data.copy()

        # Remove any existing signatures
        canonical.pop('signatures', None)
        canonical.pop('authorization', None)

        # Ensure consistent ordering and format
        return canonical

    def _save_config(self):
        """Save authority configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.authorized_keys, f, indent=2)
        except Exception as e:
            print(f"Failed to save authority config: {e}")

    def list_authorized_keys(self) -> Dict[str, Any]:
        """List all authorized keys and their status"""
        return {
            'active_keys': self.authorized_keys['keys'],
            'revoked_keys': self.authorized_keys['revoked_keys'],
            'threshold': self.authorized_keys.get('threshold', 1),
            'total_active': len(self.authorized_keys['keys'])
        }

    def set_threshold(self, threshold: int) -> Dict[str, Any]:
        """Set the minimum number of signatures required for updates"""
        try:
            if threshold < 1:
                return {'success': False, 'error': 'Threshold must be at least 1'}

            active_keys = len(self.authorized_keys['keys'])
            if threshold > active_keys:
                return {'success': False, 'error': f'Threshold cannot exceed active keys ({active_keys})'}

            # Update threshold (on blockchain if available)
            if self.blockchain:
                threshold_tx = {
                    'type': 'update_authority_registration',
                    'authority_data': {'threshold': threshold},
                    'timestamp': time.time(),
                    'publisher': 'system'
                }

                tx_hash = self.blockchain.add_transaction(threshold_tx)
                self.authorized_keys['threshold'] = threshold
                self._save_config()

                return {'success': True, 'tx_hash': tx_hash}
            else:
                self.authorized_keys['threshold'] = threshold
                self._save_config()
                return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}


class UpdateSigner:
    """Handles signing of updates with authorized private keys"""

    def __init__(self, private_key_path: str = "/etc/pisecure/update_signing_key.pem"):
        self.private_key_path = Path(private_key_path)
        self._private_key = None

    def load_private_key(self, password: str = None) -> bool:
        """Load the private signing key"""
        try:
            if not self.private_key_path.exists():
                return False

            with open(self.private_key_path, 'rb') as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=password.encode() if password else None
                )
            return True
        except Exception as e:
            print(f"Failed to load private key: {e}")
            return False

    def generate_keypair(self, password: str = None) -> Dict[str, Any]:
        """Generate a new keypair for update signing"""
        try:
            # Generate RSA keypair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )

            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption() if not password
                else serialization.BestAvailableEncryption(password.encode())
            )

            # Serialize public key
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            # Save private key
            self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.private_key_path, 'wb') as f:
                f.write(private_pem)

            self._private_key = private_key

            return {
                'success': True,
                'public_key': public_pem.decode(),
                'key_size': 2048,
                'algorithm': 'RSA-PSS'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def sign_update(self, update_data: Dict[str, Any]) -> Optional[str]:
        """Sign update data with the private key"""
        if not self._private_key:
            return None

        try:
            # Canonicalize update data
            canonical_data = json.dumps(update_data, sort_keys=True).encode()

            # Sign with PSS padding
            signature = self._private_key.sign(
                canonical_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return signature.hex()

        except Exception as e:
            print(f"Failed to sign update: {e}")
            return None

    def get_public_key(self) -> Optional[str]:
        """Get the public key in PEM format"""
        if not self._private_key:
            return None

        try:
            public_key = self._private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return public_pem.decode()
        except Exception:
            return None


# Global instances
update_authority = UpdateAuthority()
update_signer = UpdateSigner()

__all__ = [
    'UpdateAuthority',
    'UpdateSigner',
    'update_authority',
    'update_signer'
]