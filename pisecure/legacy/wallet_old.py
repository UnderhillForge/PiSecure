"""
PiSecure Wallet Management
==========================

User-managed wallet system with cryptographic key management,
balance tracking, and secure token operations for the PiSecure network.
"""

import json
import os
import secrets
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class SignWallet:
    """PiSecure cryptographic wallet for token management"""

    def __init__(self, wallet_file: str = "/var/lib/pisecure/wallets/default.json"):
        self.wallet_file = Path(wallet_file)
        self.wallet_file.parent.mkdir(parents=True, exist_ok=True)

        # Wallet data structure
        self.wallet_data = self._load_wallet()

        # Key storage paths
        self.keys_dir = self.wallet_file.parent / "keys"
        self.keys_dir.mkdir(exist_ok=True)

    def create_wallet(self, wallet_id: str, name: str = None) -> Dict[str, Any]:
        """
        Create a new wallet with cryptographic keys

        Args:
            wallet_id: Unique wallet identifier
            name: Human-readable wallet name

        Returns:
            Wallet creation result
        """
        try:
            # Generate RSA keypair for wallet
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Generate wallet address (hash of public key)
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            wallet_address = hashlib.sha256(public_pem).hexdigest()[:32]

            # Create wallet data
            wallet_data = {
                'wallet_id': wallet_id,
                'name': name or f"Wallet {wallet_id[:8]}",
                'address': wallet_address,
                'public_key': public_pem.decode(),
                'balance': 0,
                'created_at': int(os.times()[4]),  # System time
                'transactions': [],
                'version': '1.0',
                'cold_storage': False,  # Not in cold storage by default
                'cold_storage_date': None
            }

            # Save private key securely
            key_file = self.keys_dir / f"{wallet_id}.pem"
            with open(key_file, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Save wallet metadata
            wallet_file = self.wallet_file.parent / f"{wallet_id}.json"
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)

            return {
                'success': True,
                'wallet_id': wallet_id,
                'address': wallet_address,
                'key_file': str(key_file),
                'wallet_file': str(wallet_file)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """
        Load wallet data and keys

        Args:
            wallet_id: Wallet identifier to load

        Returns:
            Wallet data dictionary
        """
        try:
            wallet_file = self.wallet_file.parent / f"{wallet_id}.json"
            if not wallet_file.exists():
                return {'error': f'Wallet {wallet_id} not found'}

            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)

            # Load private key
            key_file = self.keys_dir / f"{wallet_id}.pem"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
                wallet_data['private_key'] = private_key

            return wallet_data

        except Exception as e:
            return {'error': str(e)}

    def _load_wallet(self) -> Dict[str, Any]:
        """Load the default wallet data"""
        try:
            if self.wallet_file.exists():
                with open(self.wallet_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_wallet(self):
        """Save wallet data to file"""
        try:
            with open(self.wallet_file, 'w') as f:
                json.dump(self.wallet_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save wallet: {e}")

    def get_balance(self) -> float:
        """Get current wallet balance"""
        return self.wallet_data.get('balance', 0)

    def get_address(self) -> str:
        """Get wallet address"""
        return self.wallet_data.get('address', '')

    def get_wallet_id(self) -> str:
        """Get wallet ID"""
        return self.wallet_data.get('wallet_id', '')

    def sign_transaction(self, transaction: Dict[str, Any]) -> Optional[str]:
        """
        Sign a transaction with the wallet's private key

        Args:
            transaction: Transaction data to sign

        Returns:
            Base64-encoded signature or None if failed
        """
        try:
            if 'private_key' not in self.wallet_data:
                return None

            private_key = self.wallet_data['private_key']

            # Create canonical transaction string
            tx_copy = transaction.copy()
            tx_copy.pop('signature', None)  # Remove signature before signing
            tx_string = json.dumps(tx_copy, sort_keys=True)

            # Sign the transaction
            signature = private_key.sign(
                tx_string.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return signature.hex()

        except Exception as e:
            print(f"Transaction signing failed: {e}")
            return None

    def verify_transaction_signature(self, transaction: Dict[str, Any],
                                   signature: str, public_key_pem: str) -> bool:
        """
        Verify a transaction signature

        Args:
            transaction: Transaction data
            signature: Hex-encoded signature
            public_key_pem: Sender's public key in PEM format

        Returns:
            True if signature is valid
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(), backend=default_backend()
            )

            # Create canonical transaction string
            tx_copy = transaction.copy()
            tx_copy.pop('signature', None)
            tx_string = json.dumps(tx_copy, sort_keys=True)

            # Verify signature
            public_key.verify(
                bytes.fromhex(signature),
                tx_string.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return True

        except Exception:
            return False

    def create_transfer_transaction(self, recipient_address: str, amount: float,
                                  memo: str = "") -> Dict[str, Any]:
        """
        Create a signed transfer transaction

        Args:
            recipient_address: Recipient wallet address
            amount: Amount to transfer
            memo: Optional transaction memo

        Returns:
            Signed transaction dictionary
        """
        transaction = {
            'type': 'token_transfer',
            'sender_address': self.get_address(),
            'sender_wallet': self.get_wallet_id(),
            'recipient_address': recipient_address,
            'amount': amount,
            'memo': memo,
            'timestamp': int(os.times()[4]),
            'nonce': secrets.token_hex(8)
        }

        # Sign the transaction
        signature = self.sign_transaction(transaction)
        if signature:
            transaction['signature'] = signature
            return transaction

        return {'error': 'Failed to sign transaction'}

    def create_batch_transaction(self, transfers: List[Dict[str, Any]],
                               memo: str = "") -> Dict[str, Any]:
        """
        Create a batch transfer transaction

        Args:
            transfers: List of {'recipient': address, 'amount': value} dicts
            memo: Batch transaction memo

        Returns:
            Signed batch transaction
        """
        total_amount = sum(t['amount'] for t in transfers)

        transaction = {
            'type': 'batch_transfer',
            'sender_address': self.get_address(),
            'sender_wallet': self.get_wallet_id(),
            'transfers': transfers,
            'total_amount': total_amount,
            'transfer_count': len(transfers),
            'memo': memo,
            'timestamp': int(os.times()[4]),
            'nonce': secrets.token_hex(8)
        }

        # Sign the transaction
        signature = self.sign_transaction(transaction)
        if signature:
            transaction['signature'] = signature
            return transaction

        return {'error': 'Failed to sign batch transaction'}

    def add_transaction_record(self, transaction: Dict[str, Any], tx_hash: str):
        """
        Add a transaction record to wallet history

        Args:
            transaction: Transaction data
            tx_hash: Blockchain transaction hash
        """
        if 'transactions' not in self.wallet_data:
            self.wallet_data['transactions'] = []

        # Add transaction record
        record = {
            'tx_hash': tx_hash,
            'type': transaction.get('type'),
            'timestamp': transaction.get('timestamp'),
            'amount': transaction.get('amount', 0),
            'direction': self._get_transaction_direction(transaction)
        }

        self.wallet_data['transactions'].append(record)

        # Update balance (simplified - should come from blockchain)
        if record['direction'] == 'outgoing':
            self.wallet_data['balance'] -= record['amount']
        elif record['direction'] == 'incoming':
            self.wallet_data['balance'] += record['amount']

        self._save_wallet()

    def _get_transaction_direction(self, transaction: Dict[str, Any]) -> str:
        """Determine if transaction is incoming or outgoing"""
        sender_address = transaction.get('sender_address')
        recipient_address = transaction.get('recipient_address')

        if sender_address == self.get_address():
            return 'outgoing'
        elif recipient_address == self.get_address():
            return 'incoming'
        else:
            return 'unknown'

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Get wallet transaction history"""
        return self.wallet_data.get('transactions', [])

    def export_wallet(self, export_path: str, include_private_key: bool = False,
                     password: str = None) -> Dict[str, Any]:
        """
        Export wallet data with optional private key backup

        Args:
            export_path: Path to export wallet data
            include_private_key: Whether to include encrypted private key
            password: Password for private key encryption (required if include_private_key=True)

        Returns:
            Export result with success status and details
        """
        try:
            export_data = self.wallet_data.copy()

            # Remove private key object (not serializable)
            export_data.pop('private_key', None)

            # Add export metadata
            export_data['export_info'] = {
                'exported_at': int(os.times()[4]),
                'version': '1.1',
                'includes_private_key': include_private_key
            }

            if include_private_key:
                if not password:
                    return {
                        'success': False,
                        'error': 'Password required for private key export'
                    }

                # Load and encrypt private key
                key_file = self.keys_dir / f"{self.get_wallet_id()}.pem"
                if key_file.exists():
                    with open(key_file, 'rb') as f:
                        private_key_pem = f.read()

                    # Encrypt with password using simple XOR (for demo - use proper encryption in production)
                    # In production, use cryptography library for proper encryption
                    encrypted_key = self._simple_encrypt(private_key_pem, password.encode())
                    export_data['encrypted_private_key'] = encrypted_key.hex()
                    export_data['export_info']['encryption'] = 'simple_xor'
                else:
                    return {
                        'success': False,
                        'error': 'Private key file not found'
                    }

            # Export to file
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            return {
                'success': True,
                'export_path': export_path,
                'includes_private_key': include_private_key,
                'file_size': os.path.getsize(export_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def import_wallet(self, import_path: str, password: str = None) -> Dict[str, Any]:
        """
        Import wallet data with optional private key restoration

        Args:
            import_path: Path to import wallet data
            password: Password for private key decryption (if encrypted)

        Returns:
            Import result with success status and details
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)

            # Validate required fields
            required_fields = ['wallet_id', 'address', 'public_key']
            if not all(field in import_data for field in required_fields):
                return {
                    'success': False,
                    'error': 'Invalid wallet backup file - missing required fields'
                }

            # Check for encrypted private key
            if 'encrypted_private_key' in import_data:
                if not password:
                    return {
                        'success': False,
                        'error': 'Password required to decrypt private key'
                    }

                # Decrypt private key
                try:
                    encrypted_key = bytes.fromhex(import_data['encrypted_private_key'])
                    decrypted_key = self._simple_decrypt(encrypted_key, password.encode())

                    # Save private key
                    key_file = self.keys_dir / f"{import_data['wallet_id']}.pem"
                    with open(key_file, 'wb') as f:
                        f.write(decrypted_key)

                    # Load the private key for wallet
                    private_key = serialization.load_pem_private_key(
                        decrypted_key, password=None, backend=default_backend()
                    )
                    import_data['private_key'] = private_key

                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Failed to decrypt private key: {str(e)}'
                    }

            # Update wallet data
            self.wallet_data.update(import_data)
            self._save_wallet()

            return {
                'success': True,
                'wallet_id': import_data['wallet_id'],
                'address': import_data['address'],
                'private_key_restored': 'encrypted_private_key' in import_data
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _simple_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption (for demo - use proper encryption in production)"""
        # This is a simple example - in production use cryptography.fernet or similar
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    def _simple_decrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR decryption"""
        # Same as encryption for XOR
        return self._simple_encrypt(data, key)

    def create_wallet_backup(self, backup_path: str, password: str) -> Dict[str, Any]:
        """
        Create a complete wallet backup with private key

        Args:
            backup_path: Path for backup file
            password: Password to encrypt private key

        Returns:
            Backup result
        """
        return self.export_wallet(backup_path, include_private_key=True, password=password)

    def restore_wallet_backup(self, backup_path: str, password: str) -> Dict[str, Any]:
        """
        Restore wallet from backup

        Args:
            backup_path: Path to backup file
            password: Password to decrypt private key

        Returns:
            Restore result
        """
        return self.import_wallet(backup_path, password=password)

    def list_wallets(self) -> List[Dict[str, Any]]:
        """List all available wallets"""
        wallets = []

        try:
            wallet_dir = self.wallet_file.parent
            for wallet_file in wallet_dir.glob("*.json"):
                try:
                    with open(wallet_file, 'r') as f:
                        wallet_data = json.load(f)
                        wallets.append({
                            'id': wallet_data.get('wallet_id'),
                            'name': wallet_data.get('name'),
                            'address': wallet_data.get('address')[:16] + '...',
                            'balance': wallet_data.get('balance', 0),
                            'created': wallet_data.get('created_at'),
                            'cold_storage': wallet_data.get('cold_storage', False)
                        })
                except:
                    continue
        except Exception as e:
            print(f"Failed to list wallets: {e}")

        return wallets

    def set_cold_storage(self, wallet_id: str, cold: bool = True) -> Dict[str, Any]:
        """Set or unset cold storage status for a wallet"""
        try:
            wallet_file = self.wallet_file.parent / f"{wallet_id}.json"

            if not wallet_file.exists():
                return {
                    'success': False,
                    'error': 'Wallet not found'
                }

            # Load wallet data
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)

            # Update cold storage status
            wallet_data['cold_storage'] = cold
            wallet_data['cold_storage_date'] = int(os.times()[4]) if cold else None

            # Save updated data
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)

            # If setting to cold storage, also update current wallet data if this is the active wallet
            if self.get_wallet_id() == wallet_id:
                self.wallet_data.update(wallet_data)

            return {
                'success': True,
                'wallet_id': wallet_id,
                'cold_storage': cold
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def is_cold_storage(self, wallet_id: str = None) -> bool:
        """Check if wallet is in cold storage"""
        if wallet_id is None:
            wallet_id = self.get_wallet_id()

        wallet_file = self.wallet_file.parent / f"{wallet_id}.json"
        if wallet_file.exists():
            try:
                with open(wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                return wallet_data.get('cold_storage', False)
            except:
                pass

        return False


class SignToken:
    """PiSecure token representation and validation"""

    def __init__(self, token_data: Dict[str, Any]):
        self.token_id = token_data.get('token_id', '')
        self.token_type = token_data.get('token_type', 'standard')
        self.issued_by = token_data.get('issued_by', '')
        self.permissions = token_data.get('permissions', [])
        self.issued_at = token_data.get('issued_at', 0)
        self.expires_at = token_data.get('expires_at', 0)
        self.blockchain_tx = token_data.get('blockchain_tx', '')
        self.metadata = token_data.get('metadata', {})

    @classmethod
    def from_dict(cls, token_data: Dict[str, Any]) -> 'SignToken':
        """Create SignToken from dictionary"""
        return cls(token_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary"""
        return {
            'token_id': self.token_id,
            'token_type': self.token_type,
            'issued_by': self.issued_by,
            'permissions': self.permissions,
            'issued_at': self.issued_at,
            'expires_at': self.expires_at,
            'blockchain_tx': self.blockchain_tx,
            'metadata': self.metadata
        }

    def is_valid(self) -> bool:
        """Check if token is still valid"""
        import time
        current_time = time.time()

        # Check expiration
        if self.expires_at > 0 and current_time > self.expires_at:
            return False

        # Check if issued in future (invalid)
        if self.issued_at > current_time:
            return False

        return True

    def has_permission(self, permission: str) -> bool:
        """Check if token has specific permission"""
        return permission in self.permissions

    def get_permissions(self) -> List[str]:
        """Get all token permissions"""
        return self.permissions.copy()