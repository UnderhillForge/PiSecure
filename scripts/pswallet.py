#!/usr/bin/env python3
"""
PiSecure Wallet Management System
==================================

Comprehensive wallet management with cryptographic key management,
balance tracking, secure token operations, and advanced wallet features.

This module provides a unified interface for all wallet operations including:
- Wallet creation and management
- Cryptographic operations (signing, verification)
- Transaction management
- Backup and recovery
- Multi-wallet support
- Cold storage management
- Security features
"""

import os
import json
import time
import secrets
import hashlib
import threading
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

try:
    # Try relative imports first (when used as package module)
    from .core.blockchain import SignChain
    from .core.wallet import SignWallet
    from .api.client import PiSecureClient
except ImportError:
    try:
        # Try absolute imports (when run standalone)
        from core.blockchain import SignChain
        from core.wallet import SignWallet
        from api.client import PiSecureClient
    except ImportError:
        # Create stub classes for testing/documentation
        class SignChain:
            def __init__(self):
                self.name_registry = {}  # name -> {address, registered_at, tx_hash}

            def get_wallet_balance(self, address): return 0.0
            def add_transaction(self, tx): return "test_hash"
            def register_name(self, name, address):
                self.name_registry[name] = {
                    'address': address,
                    'registered_at': time.time(),
                    'tx_hash': f"tx_{hashlib.sha256(f'{name}_{address}'.encode()).hexdigest()[:16]}",
                    'block_index': 0
                }
                return self.name_registry[name]['tx_hash']
            def get_name_info(self, name):
                return self.name_registry.get(name)
            def get_registered_names(self):
                return list(self.name_registry.keys())

        class SignWallet:
            pass

        class PiSecureClient:
            def __init__(self):
                self.bootstrap_endpoints = [
                    "https://bootstrap.pisecure.org",
                    "https://bootstrap-secondary-01.pisecure.org"
                ]

        class PiSecureDEX:
            def __init__(self):
                self.pools = {}
                self.trading_pairs = ['314ST/USDT', '314ST/BTC', '314ST/ETH']

            async def create_liquidity_pool(self, token_a, token_b, amount_a, amount_b, creator):
                pool_id = f"{token_a}_{token_b}_{int(time.time())}"
                self.pools[pool_id] = {
                    'token_a': token_a,
                    'token_b': token_b,
                    'reserve_a': amount_a,
                    'reserve_b': amount_b,
                    'total_liquidity': (amount_a * amount_b) ** 0.5,
                    'price': amount_b / amount_a if amount_a > 0 else 0,
                    'creator': creator,
                    'created_at': time.time()
                }
                return self.pools[pool_id]

            def get_market_overview(self):
                return {
                    'total_pools': len(self.pools),
                    'total_liquidity': sum(p.get('total_liquidity', 0) for p in self.pools.values()),
                    'volume_24h': 0.0,  # Simplified
                    'trading_pairs': self.trading_pairs,
                    'top_pools': list(self.pools.keys())[:5]
                }


@dataclass
class WalletInfo:
    """Wallet information data structure"""
    wallet_id: str
    name: str
    address: str
    balance: float
    created_at: float
    cold_storage: bool
    transaction_count: int
    last_transaction: Optional[float] = None


@dataclass
class TransactionInfo:
    """Transaction information data structure"""
    tx_hash: str
    type: str
    amount: float
    direction: str  # 'incoming', 'outgoing', 'unknown'
    timestamp: float
    confirmations: int = 0
    fee: float = 0.0


@dataclass
class WalletSecurityStatus:
    """Wallet security status"""
    wallet_id: str
    private_key_present: bool
    backup_exists: bool
    cold_storage: bool
    last_backup: Optional[float]
    security_score: int  # 0-100
    vulnerabilities: List[str]


class WalletManager:
    """
    Comprehensive wallet management system for PiSecure

    Features:
    - Multi-wallet support
    - Secure key management
    - Backup and recovery
    - Transaction management
    - Security monitoring
    - Cold storage support
    """

    def __init__(self, wallet_dir: str = "/var/lib/pisecure/wallets"):
        self.wallet_dir = Path(wallet_dir)
        self.wallet_dir.mkdir(parents=True, exist_ok=True)

        self.keys_dir = self.wallet_dir / "keys"
        self.keys_dir.mkdir(exist_ok=True)

        self.backups_dir = self.wallet_dir / "backups"
        self.backups_dir.mkdir(exist_ok=True)

        self.blockchain = SignChain()
        self.client = PiSecureClient()

        # Cache for wallet data
        self._wallet_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}

        # Security monitoring
        self._security_alerts: List[Dict[str, Any]] = []

        # Foundation and Trust support
        self._trust_economics = None
        self._foundation_loaded = False

    # === WALLET CREATION AND MANAGEMENT ===

    def create_wallet(self, wallet_id: str, name: str = None,
                     passphrase: str = None) -> Dict[str, Any]:
        """
        Create a new wallet with cryptographic keys

        Args:
            wallet_id: Unique wallet identifier
            name: Human-readable wallet name
            passphrase: Optional passphrase for key encryption

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
                'balance': 0.0,
                'created_at': time.time(),
                'transactions': [],
                'version': '2.0',
                'cold_storage': False,
                'cold_storage_date': None,
                'security_level': 'high',
                'last_access': time.time(),
                'metadata': {
                    'created_by': 'wallet_manager',
                    'creation_method': 'cryptographic'
                }
            }

            # Save private key (encrypted if passphrase provided)
            key_file = self.keys_dir / f"{wallet_id}.pem"
            if passphrase:
                # Encrypt private key with passphrase
                key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                encrypted_key = self._encrypt_with_passphrase(key_pem, passphrase)
                with open(key_file, 'wb') as f:
                    f.write(encrypted_key)
                wallet_data['encrypted_private_key'] = True
            else:
                # Save unencrypted (not recommended for production)
                with open(key_file, 'wb') as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                wallet_data['encrypted_private_key'] = False

            # Save wallet metadata
            wallet_file = self.wallet_dir / f"{wallet_id}.json"
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)

            # Update cache
            self._wallet_cache[wallet_id] = wallet_data
            self._cache_timestamps[wallet_id] = time.time()

            # Create initial backup
            self.create_wallet_backup(wallet_id)

            return {
                'success': True,
                'wallet_id': wallet_id,
                'address': wallet_address,
                'key_file': str(key_file),
                'wallet_file': str(wallet_file),
                'encrypted': bool(passphrase)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def load_wallet(self, wallet_id: str, passphrase: str = None) -> Dict[str, Any]:
        """
        Load wallet data and keys

        Args:
            wallet_id: Wallet identifier to load
            passphrase: Passphrase if private key is encrypted

        Returns:
            Wallet data dictionary
        """
        try:
            # Check cache first
            if (wallet_id in self._wallet_cache and
                time.time() - self._cache_timestamps.get(wallet_id, 0) < self._cache_ttl):
                wallet_data = self._wallet_cache[wallet_id].copy()
            else:
                # Load from file
                wallet_file = self.wallet_dir / f"{wallet_id}.json"
                if not wallet_file.exists():
                    return {'error': f'Wallet {wallet_id} not found'}

                with open(wallet_file, 'r') as f:
                    wallet_data = json.load(f)

                # Update cache
                self._wallet_cache[wallet_id] = wallet_data.copy()
                self._cache_timestamps[wallet_id] = time.time()

            # Load private key
            key_file = self.keys_dir / f"{wallet_id}.pem"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key_data = f.read()

                if wallet_data.get('encrypted_private_key', False):
                    if not passphrase:
                        return {'error': 'Passphrase required for encrypted private key'}
                    key_data = self._decrypt_with_passphrase(key_data, passphrase)

                private_key = serialization.load_pem_private_key(
                    key_data, password=None, backend=default_backend()
                )
                wallet_data['private_key'] = private_key

            # Update last access
            wallet_data['last_access'] = time.time()
            self._save_wallet_data(wallet_id, wallet_data)

            return wallet_data

        except Exception as e:
            return {'error': str(e)}

    def delete_wallet(self, wallet_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a wallet and all associated data

        Args:
            wallet_id: Wallet to delete
            confirm: Confirmation flag (safety measure)

        Returns:
            Deletion result
        """
        if not confirm:
            return {
                'success': False,
                'error': 'Deletion requires confirmation. Set confirm=True'
            }

        try:
            # Remove wallet files
            wallet_file = self.wallet_dir / f"{wallet_id}.json"
            key_file = self.keys_dir / f"{wallet_id}.pem"

            files_deleted = []
            if wallet_file.exists():
                wallet_file.unlink()
                files_deleted.append(str(wallet_file))

            if key_file.exists():
                key_file.unlink()
                files_deleted.append(str(key_file))

            # Clear from cache
            self._wallet_cache.pop(wallet_id, None)
            self._cache_timestamps.pop(wallet_id, None)

            # Remove from backups (optional - keep for recovery)
            # backup_file = self.backups_dir / f"{wallet_id}_backup.json"
            # if backup_file.exists():
            #     backup_file.unlink()

            return {
                'success': True,
                'wallet_id': wallet_id,
                'files_deleted': files_deleted
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_wallets(self) -> List[WalletInfo]:
        """List all available wallets"""
        wallets = []

        try:
            for wallet_file in self.wallet_dir.glob("*.json"):
                try:
                    with open(wallet_file, 'r') as f:
                        wallet_data = json.load(f)

                    # Get transaction info
                    transactions = wallet_data.get('transactions', [])
                    last_tx = max((tx.get('timestamp', 0) for tx in transactions), default=None)

                    wallet_info = WalletInfo(
                        wallet_id=wallet_data.get('wallet_id'),
                        name=wallet_data.get('name', 'Unnamed'),
                        address=wallet_data.get('address', ''),
                        balance=wallet_data.get('balance', 0.0),
                        created_at=wallet_data.get('created_at', 0),
                        cold_storage=wallet_data.get('cold_storage', False),
                        transaction_count=len(transactions),
                        last_transaction=last_tx
                    )
                    wallets.append(wallet_info)

                except Exception as e:
                    print(f"Error loading wallet {wallet_file}: {e}")
                    continue

        except Exception as e:
            print(f"Error listing wallets: {e}")

        return wallets

    # === WALLET OPERATIONS ===

    def get_balance(self, wallet_id: str, refresh: bool = False) -> float:
        """
        Get current wallet balance

        Args:
            wallet_id: Wallet identifier
            refresh: Force refresh from blockchain

        Returns:
            Current balance
        """
        if refresh:
            # Get balance from blockchain
            try:
                wallet_data = self.load_wallet(wallet_id)
                if 'error' in wallet_data:
                    return 0.0

                address = wallet_data.get('address', '')
                balance = self.blockchain.get_wallet_balance(address)

                # Update cached balance
                wallet_data['balance'] = balance
                self._save_wallet_data(wallet_id, wallet_data)

                return balance
            except Exception as e:
                print(f"Error refreshing balance: {e}")
                # Fall back to cached balance

        # Return cached balance
        wallet_data = self.load_wallet(wallet_id)
        return wallet_data.get('balance', 0.0) if 'error' not in wallet_data else 0.0

    def get_wallet_info(self, wallet_id: str) -> Optional[WalletInfo]:
        """Get comprehensive wallet information"""
        wallet_data = self.load_wallet(wallet_id)
        if 'error' in wallet_data:
            return None

        transactions = wallet_data.get('transactions', [])
        last_tx = max((tx.get('timestamp', 0) for tx in transactions), default=None)

        return WalletInfo(
            wallet_id=wallet_data.get('wallet_id'),
            name=wallet_data.get('name', 'Unnamed'),
            address=wallet_data.get('address'),
            balance=wallet_data.get('balance', 0.0),
            created_at=wallet_data.get('created_at', 0),
            cold_storage=wallet_data.get('cold_storage', False),
            transaction_count=len(transactions),
            last_transaction=last_tx
        )

    def get_transaction_history(self, wallet_id: str, limit: int = 50) -> List[TransactionInfo]:
        """Get wallet transaction history"""
        wallet_data = self.load_wallet(wallet_id)
        if 'error' in wallet_data:
            return []

        transactions = wallet_data.get('transactions', [])
        address = wallet_data.get('address', '')

        # Convert to TransactionInfo objects
        tx_info_list = []
        for tx in transactions[-limit:]:
            tx_info = TransactionInfo(
                tx_hash=tx.get('tx_hash', ''),
                type=tx.get('type', 'unknown'),
                amount=tx.get('amount', 0.0),
                direction=tx.get('direction', 'unknown'),
                timestamp=tx.get('timestamp', 0),
                confirmations=tx.get('confirmations', 0),
                fee=tx.get('fee', 0.0)
            )
            tx_info_list.append(tx_info)

        return tx_info_list

    # === TRANSACTION OPERATIONS ===

    def create_transaction(self, wallet_id: str, recipient_address: str,
                          amount: float, memo: str = "") -> Dict[str, Any]:
        """
        Create a signed transaction

        Args:
            wallet_id: Sender wallet ID
            recipient_address: Recipient address
            amount: Amount to send
            memo: Optional transaction memo

        Returns:
            Signed transaction data
        """
        try:
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Check balance
            balance = wallet_data.get('balance', 0.0)
            if balance < amount:
                return {
                    'success': False,
                    'error': f'Insufficient balance: {balance} < {amount}'
                }

            # Create transaction data
            transaction = {
                'type': 'token_transfer',
                'sender_address': wallet_data.get('address'),
                'sender_wallet': wallet_id,
                'recipient_address': recipient_address,
                'amount': amount,
                'memo': memo,
                'timestamp': time.time(),
                'nonce': secrets.token_hex(8)
            }

            # Sign transaction
            signature = self.sign_transaction(wallet_id, transaction)
            if not signature:
                return {
                    'success': False,
                    'error': 'Failed to sign transaction'
                }

            transaction['signature'] = signature

            return {
                'success': True,
                'transaction': transaction,
                'tx_hash': self._calculate_tx_hash(transaction)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def send_transaction(self, wallet_id: str, recipient_address: str,
                        amount: float, memo: str = "") -> Dict[str, Any]:
        """
        Create and submit a transaction

        Args:
            wallet_id: Sender wallet ID
            recipient_address: Recipient address
            amount: Amount to send
            memo: Optional transaction memo

        Returns:
            Transaction submission result
        """
        # Create transaction
        tx_result = self.create_transaction(wallet_id, recipient_address, amount, memo)
        if not tx_result.get('success', False):
            return tx_result

        transaction = tx_result['transaction']
        tx_hash = tx_result['tx_hash']

        try:
            # Submit to blockchain
            submitted_tx_hash = self.blockchain.add_transaction(transaction)

            if submitted_tx_hash != tx_hash:
                # Blockchain may modify hash - use blockchain's hash
                tx_hash = submitted_tx_hash

            # Record transaction in wallet
            self._record_transaction(wallet_id, transaction, tx_hash)

            return {
                'success': True,
                'tx_hash': tx_hash,
                'amount': amount,
                'recipient': recipient_address
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to submit transaction: {str(e)}'
            }

    def sign_transaction(self, wallet_id: str, transaction: Dict[str, Any]) -> Optional[str]:
        """
        Sign a transaction with wallet's private key

        Args:
            wallet_id: Wallet ID
            transaction: Transaction data to sign

        Returns:
            Hex-encoded signature or None if failed
        """
        try:
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data or 'private_key' not in wallet_data:
                return None

            private_key = wallet_data['private_key']

            # Create canonical transaction string
            tx_copy = transaction.copy()
            tx_copy.pop('signature', None)  # Remove signature before signing
            tx_string = json.dumps(tx_copy, sort_keys=True, default=str)

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

    # === BACKUP AND RECOVERY ===

    def create_wallet_backup(self, wallet_id: str, backup_path: str = None,
                           include_private_key: bool = True,
                           passphrase: str = None) -> Dict[str, Any]:
        """
        Create a comprehensive wallet backup

        Args:
            wallet_id: Wallet to backup
            backup_path: Custom backup path (auto-generated if None)
            include_private_key: Include encrypted private key
            passphrase: Passphrase for encryption

        Returns:
            Backup result
        """
        try:
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Generate backup filename if not provided
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = str(self.backups_dir / f"{wallet_id}_backup_{timestamp}.json")

            # Create backup data
            backup_data = wallet_data.copy()

            # Add backup metadata
            backup_data['backup_info'] = {
                'backup_created': time.time(),
                'wallet_version': wallet_data.get('version', '1.0'),
                'backup_version': '2.0',
                'includes_private_key': include_private_key,
                'encrypted': bool(passphrase)
            }

            # Handle private key
            if include_private_key and 'private_key' in backup_data:
                private_key = backup_data.pop('private_key')  # Remove object

                # Export private key
                key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                if passphrase:
                    # Encrypt with passphrase
                    encrypted_key = self._encrypt_with_passphrase(key_pem, passphrase)
                    backup_data['encrypted_private_key'] = encrypted_key.hex()
                else:
                    # Store unencrypted (not recommended)
                    backup_data['private_key_pem'] = key_pem.decode()

            # Save backup
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)

            # Update wallet's last backup time
            wallet_data['last_backup'] = time.time()
            self._save_wallet_data(wallet_id, wallet_data)

            return {
                'success': True,
                'backup_path': backup_path,
                'wallet_id': wallet_id,
                'includes_private_key': include_private_key,
                'encrypted': bool(passphrase),
                'file_size': os.path.getsize(backup_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def restore_wallet_backup(self, backup_path: str, wallet_id: str = None,
                            passphrase: str = None) -> Dict[str, Any]:
        """
        Restore wallet from backup

        Args:
            backup_path: Path to backup file
            wallet_id: New wallet ID (uses backup ID if None)
            passphrase: Passphrase for decryption

        Returns:
            Restore result
        """
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)

            # Validate backup
            if 'backup_info' not in backup_data:
                return {
                    'success': False,
                    'error': 'Invalid backup file'
                }

            # Use provided wallet_id or from backup
            if not wallet_id:
                wallet_id = backup_data.get('wallet_id')
                if not wallet_id:
                    return {
                        'success': False,
                        'error': 'No wallet ID in backup'
                    }

            # Handle private key restoration
            private_key = None
            if 'encrypted_private_key' in backup_data:
                if not passphrase:
                    return {
                        'success': False,
                        'error': 'Passphrase required for encrypted private key'
                    }
                encrypted_key = bytes.fromhex(backup_data['encrypted_private_key'])
                key_pem = self._decrypt_with_passphrase(encrypted_key, passphrase)
                private_key = serialization.load_pem_private_key(
                    key_pem, password=None, backend=default_backend()
                )
            elif 'private_key_pem' in backup_data:
                key_pem = backup_data['private_key_pem'].encode()
                private_key = serialization.load_pem_private_key(
                    key_pem, password=None, backend=default_backend()
                )

            # Restore wallet data
            wallet_data = backup_data.copy()
            wallet_data.pop('backup_info', None)

            if private_key:
                wallet_data['private_key'] = private_key

            # Save restored wallet
            wallet_file = self.wallet_dir / f"{wallet_id}.json"
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2, default=str)

            # Save private key if available
            if private_key:
                key_file = self.keys_dir / f"{wallet_id}.pem"
                with open(key_file, 'wb') as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))

            # Update cache
            self._wallet_cache[wallet_id] = wallet_data
            self._cache_timestamps[wallet_id] = time.time()

            return {
                'success': True,
                'wallet_id': wallet_id,
                'address': wallet_data.get('address'),
                'private_key_restored': private_key is not None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # === SECURITY AND MONITORING ===

    def get_security_status(self, wallet_id: str) -> WalletSecurityStatus:
        """Get comprehensive wallet security status"""
        wallet_data = self.load_wallet(wallet_id)
        if 'error' in wallet_data:
            return WalletSecurityStatus(
                wallet_id=wallet_id,
                private_key_present=False,
                backup_exists=False,
                cold_storage=False,
                last_backup=None,
                security_score=0,
                vulnerabilities=['Wallet not found']
            )

        # Check security factors
        private_key_present = 'private_key' in wallet_data
        cold_storage = wallet_data.get('cold_storage', False)
        last_backup = wallet_data.get('last_backup')

        # Check for backup
        backup_exists = False
        try:
            for backup_file in self.backups_dir.glob(f"{wallet_id}_backup_*.json"):
                backup_exists = True
                break
        except:
            pass

        # Calculate security score
        score = 0
        vulnerabilities = []

        if private_key_present:
            score += 30
        else:
            vulnerabilities.append('Private key not loaded')

        if backup_exists:
            score += 25
        else:
            vulnerabilities.append('No recent backup')

        if cold_storage:
            score += 20
        else:
            vulnerabilities.append('Not in cold storage')

        if wallet_data.get('encrypted_private_key', False):
            score += 15
        else:
            vulnerabilities.append('Private key not encrypted')

        # Age-based scoring
        age_days = (time.time() - wallet_data.get('created_at', 0)) / (24 * 3600)
        if age_days < 30:
            vulnerabilities.append('Wallet is very new')

        last_access_days = (time.time() - wallet_data.get('last_access', 0)) / (24 * 3600)
        if last_access_days > 90:
            vulnerabilities.append('Wallet not accessed recently')

        return WalletSecurityStatus(
            wallet_id=wallet_id,
            private_key_present=private_key_present,
            backup_exists=backup_exists,
            cold_storage=cold_storage,
            last_backup=last_backup,
            security_score=min(score, 100),
            vulnerabilities=vulnerabilities
        )

    def set_cold_storage(self, wallet_id: str, cold: bool = True) -> Dict[str, Any]:
        """Set or unset cold storage for a wallet"""
        try:
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            wallet_data['cold_storage'] = cold
            wallet_data['cold_storage_date'] = time.time() if cold else None

            self._save_wallet_data(wallet_id, wallet_data)

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

    # === FOUNDATION AND TRUST SUPPORT ===

    def _load_trust_economics(self):
        """Lazy load trust economics module"""
        if not self._trust_economics:
            try:
                from .core.token_economics import TokenEconomics
                self._trust_economics = TokenEconomics()
            except ImportError:
                # Create stub for standalone operation
                self._trust_economics = None
        return self._trust_economics

    def create_trust_fund(self, wallet_id: str, trust_type: str = "public",
                          initial_funding: float = 0.0) -> Dict[str, Any]:
        """
        Create a developer trust fund

        Args:
            wallet_id: Developer wallet ID
            trust_type: Type of trust ('public', 'private', 'foundation', 'exchange')
            initial_funding: Initial funding amount

        Returns:
            Trust fund creation result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Trust economics not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Check if wallet has sufficient balance for initial funding
            balance = wallet_data.get('balance', 0.0)
            if balance < initial_funding:
                return {
                    'success': False,
                    'error': f'Insufficient balance: {balance} < {initial_funding}'
                }

            # Map string type to enum
            from enum import Enum
            class TrustType(Enum):
                PUBLIC = "public"
                PRIVATE = "private"
                FOUNDATION = "foundation"
                EXCHANGE = "exchange"

            try:
                trust_type_enum = TrustType(trust_type.lower())
            except ValueError:
                return {'success': False, 'error': f'Invalid trust type: {trust_type}'}

            # Create trust fund
            trust_id = economics.create_trust_fund(
                developer_address=wallet_data.get('address'),
                trust_type=trust_type_enum,
                initial_funding=initial_funding
            )

            # Deduct initial funding from wallet if provided
            if initial_funding > 0:
                wallet_data['balance'] -= initial_funding
                self._save_wallet_data(wallet_id, wallet_data)

            return {
                'success': True,
                'trust_id': trust_id,
                'trust_type': trust_type,
                'initial_funding': initial_funding
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def fund_trust(self, wallet_id: str, trust_id: str, amount: float) -> Dict[str, Any]:
        """
        Fund a trust fund from wallet

        Args:
            wallet_id: Funding wallet ID
            trust_id: Trust fund ID
            amount: Amount to fund

        Returns:
            Funding result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Trust economics not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Check balance
            balance = wallet_data.get('balance', 0.0)
            if balance < amount:
                return {
                    'success': False,
                    'error': f'Insufficient balance: {balance} < {amount}'
                }

            # Fund trust
            success = economics.fund_trust(trust_id, amount, wallet_data.get('address'))
            if not success:
                return {'success': False, 'error': 'Failed to fund trust'}

            # Update wallet balance
            wallet_data['balance'] -= amount
            self._save_wallet_data(wallet_id, wallet_data)

            return {
                'success': True,
                'trust_id': trust_id,
                'amount': amount
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_subscription_plan(self, wallet_id: str, trust_id: str,
                                plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a subscription plan for a trust fund

        Args:
            wallet_id: Developer wallet ID
            trust_id: Trust fund ID
            plan_data: Plan configuration

        Returns:
            Plan creation result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Trust economics not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Check if wallet owns the trust
            trust = economics.get_trust_fund_details(trust_id)
            if not trust or trust['trust']['developer_address'] != wallet_data.get('address'):
                return {'success': False, 'error': 'Wallet does not own this trust'}

            # Create subscription plan
            plan_id = economics.create_subscription_plan(trust_id, plan_data)

            return {
                'success': True,
                'trust_id': trust_id,
                'plan_id': plan_id,
                'plan_data': plan_data
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def subscribe_to_plan(self, wallet_id: str, trust_id: str,
                         plan_id: str) -> Dict[str, Any]:
        """
        Subscribe wallet to a trust fund plan

        Args:
            wallet_id: Subscriber wallet ID
            trust_id: Trust fund ID
            plan_id: Subscription plan ID

        Returns:
            Subscription result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Trust economics not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Subscribe to plan
            subscription_id = economics.subscribe_to_plan(
                trust_id, wallet_data.get('address'), plan_id
            )

            return {
                'success': True,
                'subscription_id': subscription_id,
                'trust_id': trust_id,
                'plan_id': plan_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_trust_funds(self) -> List[Dict[str, Any]]:
        """Get all available trust funds"""
        try:
            economics = self._load_trust_economics()
            if not economics:
                return []

            # Get trust funds summary
            status = economics.get_economic_status()
            return status.get('trust_funds', {}).get('details', [])

        except Exception as e:
            print(f"Error getting trust funds: {e}")
            return []

    def get_foundation_status(self) -> Dict[str, Any]:
        """Get foundation trust status"""
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'error': 'Foundation trust not available'}

            return economics.get_foundation_status()

        except Exception as e:
            return {'error': str(e)}

    def create_foundation_grant(self, wallet_id: str, title: str,
                               description: str, amount: float,
                               duration_months: int) -> Dict[str, Any]:
        """
        Create a foundation grant proposal

        Args:
            wallet_id: Proposer wallet ID
            title: Grant title
            description: Grant description
            amount: Requested amount
            duration_months: Grant duration

        Returns:
            Grant creation result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Foundation trust not available'}

            # Create grant
            grant_id = economics.create_foundation_grant(
                title=title,
                description=description,
                amount=amount,
                duration_months=duration_months,
                milestones=[f"Month {i+1}" for i in range(duration_months)]
            )

            return {
                'success': True,
                'grant_id': grant_id,
                'title': title,
                'amount': amount
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def vote_on_grant(self, wallet_id: str, grant_id: str, vote: bool) -> Dict[str, Any]:
        """
        Vote on a foundation grant proposal

        Args:
            wallet_id: Voter wallet ID
            grant_id: Grant proposal ID
            vote: True for approve, False for reject

        Returns:
            Voting result
        """
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'success': False, 'error': 'Foundation trust not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Vote on grant
            success = economics.vote_on_grant(
                grant_id, wallet_data.get('address'), vote
            )

            return {
                'success': success,
                'grant_id': grant_id,
                'vote': 'approve' if vote else 'reject'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_economic_status(self) -> Dict[str, Any]:
        """Get comprehensive economic status"""
        try:
            economics = self._load_trust_economics()
            if not economics:
                return {'error': 'Economic system not available'}

            return economics.get_economic_status()

        except Exception as e:
            return {'error': str(e)}

    # === PiNS (Pi Name System) SUPPORT ===

    def check_name_availability(self, name: str) -> Dict[str, Any]:
        """
        Check if a PiNS name is available for registration

        Args:
            name: Name to check (without .pisecure suffix)

        Returns:
            Availability status and registration info
        """
        try:
            # Validate name format
            if not name or len(name) < 2 or len(name) > 32:
                return {
                    'available': False,
                    'error': 'Name must be 2-32 characters long'
                }

            # Check for valid characters (alphanumeric, hyphens, underscores)
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                return {
                    'available': False,
                    'error': 'Name can only contain letters, numbers, hyphens, and underscores'
                }

            # Check if name is reserved
            reserved_names = {'foundation', 'genesis', 'admin', 'system', 'pisecure'}
            if name.lower() in reserved_names:
                return {
                    'available': False,
                    'error': 'This name is reserved for system use'
                }

            # Check if name exists in registry
            name_info = self.blockchain.get_name_info(name)
            if name_info:
                return {
                    'available': False,
                    'registered': True,
                    'owner': name_info.get('address'),
                    'registered_at': name_info.get('registered_at'),
                    'expires_at': name_info.get('expires_at')
                }

            # Name is available
            return {
                'available': True,
                'registration_fee': 5.0,  # Fixed fee from economics
                'estimated_confirmation': 600  # ~10 minutes
            }

        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }

    def resolve_name(self, name: str) -> Dict[str, Any]:
        """
        Resolve a PiNS name to wallet address

        Args:
            name: Name to resolve (with or without .pisecure suffix)

        Returns:
            Resolution result with address or error
        """
        try:
            # Remove .pisecure suffix if present
            if name.endswith('.pisecure'):
                name = name[:-9]

            # Get name information
            name_info = self.blockchain.get_name_info(name)
            if not name_info:
                return {
                    'resolved': False,
                    'error': f'Name "{name}" not found'
                }

            # Check if name has expired (simplified check)
            expires_at = name_info.get('expires_at', 0)
            if expires_at > 0 and time.time() > expires_at:
                return {
                    'resolved': False,
                    'error': f'Name "{name}" has expired'
                }

            return {
                'resolved': True,
                'name': name,
                'address': name_info.get('address'),
                'registered_at': name_info.get('registered_at'),
                'expires_at': name_info.get('expires_at'),
                'block_index': name_info.get('block_index'),
                'tx_hash': name_info.get('tx_hash')
            }

        except Exception as e:
            return {
                'resolved': False,
                'error': str(e)
            }

    def register_name(self, name: str, wallet_id: str, years: int = 1) -> Dict[str, Any]:
        """
        Register a PiNS name for a wallet

        Args:
            name: Name to register (without .pisecure suffix)
            wallet_id: Wallet ID to own the name
            years: Number of years to register (default: 1)

        Returns:
            Registration result
        """
        try:
            # Check name availability first
            availability = self.check_name_availability(name)
            if not availability.get('available', False):
                return availability

            # Load wallet
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # Calculate total cost (5 tokens per year)
            total_cost = 5.0 * years

            # Check balance
            balance = wallet_data.get('balance', 0.0)
            if balance < total_cost:
                return {
                    'success': False,
                    'error': f'Insufficient balance: {balance} < {total_cost} tokens required'
                }

            # Register name via blockchain
            tx_hash = self.blockchain.register_name(name, wallet_data.get('address'))

            if not tx_hash:
                return {
                    'success': False,
                    'error': 'Failed to register name on blockchain'
                }

            # Deduct fee from wallet
            wallet_data['balance'] -= total_cost
            self._save_wallet_data(wallet_id, wallet_data)

            # Calculate expiration
            expires_at = time.time() + (years * 365 * 24 * 60 * 60)  # years in seconds

            return {
                'success': True,
                'name': name,
                'wallet_id': wallet_id,
                'address': wallet_data.get('address'),
                'tx_hash': tx_hash,
                'fee_paid': total_cost,
                'years': years,
                'expires_at': expires_at,
                'status': 'pending_mining'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_wallet_names(self, wallet_id: str) -> List[Dict[str, Any]]:
        """
        Get all PiNS names registered to a wallet

        Args:
            wallet_id: Wallet ID to check

        Returns:
            List of names owned by the wallet
        """
        try:
            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return []

            wallet_address = wallet_data.get('address', '')
            owned_names = []

            # Get all registered names and filter by address
            all_names = self.blockchain.get_registered_names()
            for name in all_names:
                name_info = self.blockchain.get_name_info(name)
                if name_info and name_info.get('address') == wallet_address:
                    owned_names.append({
                        'name': name,
                        'registered_at': name_info.get('registered_at'),
                        'expires_at': name_info.get('expires_at'),
                        'block_index': name_info.get('block_index'),
                        'tx_hash': name_info.get('tx_hash'),
                        'status': 'active' if time.time() < name_info.get('expires_at', 0) else 'expired'
                    })

            return owned_names

        except Exception as e:
            print(f"Error getting wallet names: {e}")
            return []

    def transfer_name(self, name: str, from_wallet_id: str, to_wallet_id: str) -> Dict[str, Any]:
        """
        Transfer a PiNS name to another wallet

        Args:
            name: Name to transfer
            from_wallet_id: Current owner wallet
            to_wallet_id: New owner wallet

        Returns:
            Transfer result
        """
        try:
            # Verify ownership
            from_wallet = self.load_wallet(from_wallet_id)
            to_wallet = self.load_wallet(to_wallet_id)

            if 'error' in from_wallet:
                return from_wallet
            if 'error' in to_wallet:
                return to_wallet

            # Check if from_wallet owns the name
            name_info = self.blockchain.get_name_info(name)
            if not name_info or name_info.get('address') != from_wallet.get('address'):
                return {
                    'success': False,
                    'error': f'Wallet {from_wallet_id} does not own name "{name}"'
                }

            # Create transfer transaction
            transfer_tx = {
                'type': 'name_transfer',
                'name': name,
                'from_address': from_wallet.get('address'),
                'to_address': to_wallet.get('address'),
                'timestamp': time.time(),
                'nonce': secrets.token_hex(8)
            }

            # Sign transaction
            signature = self.sign_transaction(from_wallet_id, transfer_tx)
            if not signature:
                return {
                    'success': False,
                    'error': 'Failed to sign transfer transaction'
                }

            transfer_tx['signature'] = signature

            # Submit to blockchain (placeholder - would need blockchain method)
            # For now, just return success
            return {
                'success': True,
                'name': name,
                'from_wallet': from_wallet_id,
                'to_wallet': to_wallet_id,
                'tx_data': transfer_tx,
                'status': 'transfer_initiated'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # === DEX (Decentralized Exchange) SUPPORT ===

    def _load_dex(self):
        """Lazy load DEX module"""
        # For standalone execution, use stub DEX
        return PiSecureDEX()

    def _get_bootstrap_dex_stats(self) -> Dict[str, Any]:
        """Get DEX statistics from bootstrap servers"""
        for bootstrap_url in self.client.bootstrap_endpoints:
            try:
                response = requests.get(f"{bootstrap_url}/api/v1/dex/stats", timeout=5)
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        return {}

    def _create_bootstrap_liquidity_pool(self, token_a: str, token_b: str,
                                       amount_a: float, wallet_id: str) -> Dict[str, Any]:
        """Create liquidity pool via bootstrap DEX API"""
        wallet_data = self.load_wallet(wallet_id)
        if 'error' in wallet_data:
            return wallet_data

        pool_data = {
            'token_a': token_a,
            'token_b': token_b,
            'initial_liquidity_a': amount_a,
            'creator': wallet_data.get('address')
        }

        for bootstrap_url in self.client.bootstrap_endpoints:
            try:
                response = requests.post(
                    f"{bootstrap_url}/api/v1/dex/pool/create",
                    json=pool_data,
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue

        # Fallback to local DEX if bootstrap unavailable
        return self._create_local_liquidity_pool(token_a, token_b, amount_a, wallet_id)

    def _create_local_liquidity_pool(self, token_a: str, token_b: str,
                                   amount_a: float, wallet_id: str) -> Dict[str, Any]:
        """Create liquidity pool using local DEX engine"""
        dex = self._load_dex()
        if not dex:
            return {'success': False, 'error': 'DEX not available'}

        # Simplified - assumes equal value for demo
        amount_b = amount_a  # In production, would need price oracle
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                dex.create_liquidity_pool(token_a, token_b, amount_a, amount_b, wallet_id)
            )
            return {'success': True, 'pool': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            loop.close()

    def create_liquidity_pool(self, token_a: str, token_b: str,
                             amount_a: float, wallet_id: str) -> Dict[str, Any]:
        """
        Create a new DEX liquidity pool

        Args:
            token_a: First token symbol
            token_b: Second token symbol
            amount_a: Amount of token A to provide
            wallet_id: Wallet providing liquidity

        Returns:
            Pool creation result
        """
        try:
            dex = self._load_dex()
            if not dex:
                return {'success': False, 'error': 'DEX not available'}

            wallet_data = self.load_wallet(wallet_id)
            if 'error' in wallet_data:
                return wallet_data

            # For now, assume equal value amounts (would need price oracle in production)
            amount_b = amount_a  # Simplified assumption

            result = dex.create_liquidity_pool(token_a, token_b, amount_a, wallet_id)

            if result.get('success', False):
                # Deduct tokens from wallet (simplified - would need token balance checking)
                pass

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def add_liquidity(self, pool_id: str, amount_a: float, amount_b: float,
                     wallet_id: str) -> Dict[str, Any]:
        """
        Add liquidity to an existing DEX pool

        Args:
            pool_id: Pool identifier
            amount_a: Amount of token A
            amount_b: Amount of token B
            wallet_id: Wallet providing liquidity

        Returns:
            Liquidity addition result
        """
        try:
            dex = self._load_dex()
            if not dex:
                return {'success': False, 'error': 'DEX not available'}

            result = dex.add_liquidity(pool_id, amount_a, amount_b, wallet_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def swap_tokens(self, pool_id: str, token_in: str, amount_in: float,
                   min_out: float, wallet_id: str) -> Dict[str, Any]:
        """
        Execute token swap on DEX

        Args:
            pool_id: Pool to use for swap
            token_in: Input token symbol
            amount_in: Amount to swap
            min_out: Minimum output amount
            wallet_id: Wallet executing swap

        Returns:
            Swap result
        """
        try:
            dex = self._load_dex()
            if not dex:
                return {'success': False, 'error': 'DEX not available'}

            result = dex.swap_tokens(pool_id, token_in, amount_in, min_out, wallet_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_dex_stats(self) -> Dict[str, Any]:
        """Get DEX statistics and market data from bootstrap or local"""
        # Try bootstrap DEX stats first
        bootstrap_stats = self._get_bootstrap_dex_stats()
        if bootstrap_stats:
            return bootstrap_stats

        # Fallback to local DEX
        try:
            dex = self._load_dex()
            if not dex:
                return {'error': 'DEX not available'}

            return dex.get_market_overview()

        except Exception as e:
            return {'error': str(e)}

    # === UTILITY METHODS ===

    def _save_wallet_data(self, wallet_id: str, wallet_data: Dict[str, Any]):
        """Save wallet data to file and update cache"""
        wallet_file = self.wallet_dir / f"{wallet_id}.json"

        # Remove non-serializable objects
        save_data = wallet_data.copy()
        save_data.pop('private_key', None)

        with open(wallet_file, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)

        # Update cache
        self._wallet_cache[wallet_id] = wallet_data
        self._cache_timestamps[wallet_id] = time.time()

    def _record_transaction(self, wallet_id: str, transaction: Dict[str, Any], tx_hash: str):
        """Record a transaction in wallet history"""
        wallet_data = self.load_wallet(wallet_id)
        if 'error' in wallet_data:
            return

        if 'transactions' not in wallet_data:
            wallet_data['transactions'] = []

        # Determine transaction direction
        sender_address = transaction.get('sender_address')
        recipient_address = transaction.get('recipient_address')
        wallet_address = wallet_data.get('address')

        if sender_address == wallet_address:
            direction = 'outgoing'
            amount = -transaction.get('amount', 0)
        elif recipient_address == wallet_address:
            direction = 'incoming'
            amount = transaction.get('amount', 0)
        else:
            direction = 'unknown'
            amount = 0

        # Create transaction record
        tx_record = {
            'tx_hash': tx_hash,
            'type': transaction.get('type', 'transfer'),
            'amount': abs(amount),
            'direction': direction,
            'timestamp': transaction.get('timestamp', time.time()),
            'confirmations': 0,
            'fee': transaction.get('fee', 0.0)
        }

        wallet_data['transactions'].append(tx_record)

        # Update balance
        wallet_data['balance'] += amount

        self._save_wallet_data(wallet_id, wallet_data)

    def _calculate_tx_hash(self, transaction: Dict[str, Any]) -> str:
        """Calculate transaction hash"""
        tx_copy = transaction.copy()
        tx_copy.pop('signature', None)
        tx_string = json.dumps(tx_copy, sort_keys=True, default=str)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def _encrypt_with_passphrase(self, data: bytes, passphrase: str) -> bytes:
        """Encrypt data with passphrase using Fernet"""
        key = hashlib.sha256(passphrase.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)
        return fernet.encrypt(data)

    def _decrypt_with_passphrase(self, data: bytes, passphrase: str) -> bytes:
        """Decrypt data with passphrase using Fernet"""
        key = hashlib.sha256(passphrase.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)
        return fernet.decrypt(data)


class WalletAPI:
    """High-level wallet API for applications"""

    def __init__(self, wallet_manager: WalletManager = None):
        self.wallet_manager = wallet_manager or WalletManager()

    def create_wallet(self, name: str, passphrase: str = None) -> Dict[str, Any]:
        """Create a new wallet with a generated ID"""
        wallet_id = f"wallet_{secrets.token_hex(4)}"
        return self.wallet_manager.create_wallet(wallet_id, name, passphrase)

    def get_wallets(self) -> List[Dict[str, Any]]:
        """Get list of all wallets"""
        wallets = self.wallet_manager.list_wallets()
        return [asdict(wallet) for wallet in wallets]

    def get_wallet(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed wallet information"""
        wallet_info = self.wallet_manager.get_wallet_info(wallet_id)
        return asdict(wallet_info) if wallet_info else None

    def send_tokens(self, wallet_id: str, recipient: str, amount: float,
                   memo: str = "") -> Dict[str, Any]:
        """Send tokens to another address"""
        return self.wallet_manager.send_transaction(wallet_id, recipient, amount, memo)

    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance"""
        return self.wallet_manager.get_balance(wallet_id)

    def get_transactions(self, wallet_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        transactions = self.wallet_manager.get_transaction_history(wallet_id, limit)
        return [asdict(tx) for tx in transactions]

    def backup_wallet(self, wallet_id: str, passphrase: str = None) -> Dict[str, Any]:
        """Create wallet backup"""
        return self.wallet_manager.create_wallet_backup(wallet_id, passphrase=passphrase)

    def security_check(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet security status"""
        status = self.wallet_manager.get_security_status(wallet_id)
        return asdict(status)


# === UTILITY FUNCTIONS ===

def create_wallet_manager(wallet_dir: str = None) -> WalletManager:
    """Create and return a configured wallet manager"""
    return WalletManager(wallet_dir)


def create_wallet_api(wallet_dir: str = None) -> WalletAPI:
    """Create and return a configured wallet API"""
    manager = create_wallet_manager(wallet_dir)
    return WalletAPI(manager)


# === CLI INTEGRATION ===

def main():
    """Command-line interface for wallet management"""
    import argparse

    parser = argparse.ArgumentParser(description='PiSecure Wallet Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create wallet
    create_parser = subparsers.add_parser('create', help='Create a new wallet')
    create_parser.add_argument('name', help='Wallet name')
    create_parser.add_argument('--passphrase', help='Encryption passphrase')

    # List wallets
    subparsers.add_parser('list', help='List all wallets')

    # Show wallet info
    info_parser = subparsers.add_parser('info', help='Show wallet information')
    info_parser.add_argument('wallet_id', help='Wallet ID')

    # Send tokens
    send_parser = subparsers.add_parser('send', help='Send tokens')
    send_parser.add_argument('wallet_id', help='Sender wallet ID')
    send_parser.add_argument('recipient', help='Recipient address')
    send_parser.add_argument('amount', type=float, help='Amount to send')
    send_parser.add_argument('--memo', default='', help='Transaction memo')

    # Backup wallet
    backup_parser = subparsers.add_parser('backup', help='Backup wallet')
    backup_parser.add_argument('wallet_id', help='Wallet ID')
    backup_parser.add_argument('--passphrase', help='Encryption passphrase')

    # Security check
    security_parser = subparsers.add_parser('security', help='Check wallet security')
    security_parser.add_argument('wallet_id', help='Wallet ID')

    # Foundation and Trust commands
    trust_parser = subparsers.add_parser('trust-create', help='Create a trust fund')
    trust_parser.add_argument('wallet_id', help='Developer wallet ID')
    trust_parser.add_argument('trust_type', choices=['public', 'private', 'foundation', 'exchange'],
                            help='Type of trust fund')
    trust_parser.add_argument('--funding', type=float, default=0.0, help='Initial funding amount')

    fund_parser = subparsers.add_parser('trust-fund', help='Fund a trust fund')
    fund_parser.add_argument('wallet_id', help='Funding wallet ID')
    fund_parser.add_argument('trust_id', help='Trust fund ID')
    fund_parser.add_argument('amount', type=float, help='Amount to fund')

    plan_parser = subparsers.add_parser('plan-create', help='Create subscription plan')
    plan_parser.add_argument('wallet_id', help='Developer wallet ID')
    plan_parser.add_argument('trust_id', help='Trust fund ID')
    plan_parser.add_argument('name', help='Plan name')
    plan_parser.add_argument('monthly_cost', type=float, help='Monthly cost')

    subscribe_parser = subparsers.add_parser('subscribe', help='Subscribe to trust plan')
    subscribe_parser.add_argument('wallet_id', help='Subscriber wallet ID')
    subscribe_parser.add_argument('trust_id', help='Trust fund ID')
    subscribe_parser.add_argument('plan_id', help='Plan ID')

    grant_parser = subparsers.add_parser('grant-create', help='Create foundation grant')
    grant_parser.add_argument('wallet_id', help='Proposer wallet ID')
    grant_parser.add_argument('title', help='Grant title')
    grant_parser.add_argument('--description', default='', help='Grant description')
    grant_parser.add_argument('amount', type=float, help='Requested amount')
    grant_parser.add_argument('--months', type=int, default=12, help='Duration in months')

    vote_parser = subparsers.add_parser('grant-vote', help='Vote on foundation grant')
    vote_parser.add_argument('wallet_id', help='Voter wallet ID')
    vote_parser.add_argument('grant_id', help='Grant ID')
    vote_parser.add_argument('vote', choices=['yes', 'no'], help='Vote (yes/no)')

    trusts_parser = subparsers.add_parser('trusts', help='List trust funds')

    # PiNS (Pi Name System) commands
    check_name_parser = subparsers.add_parser('check-name', help='Check name availability')
    check_name_parser.add_argument('name', help='Name to check')

    resolve_parser = subparsers.add_parser('resolve', help='Resolve name to address')
    resolve_parser.add_argument('name', help='Name to resolve')

    register_parser = subparsers.add_parser('register-name', help='Register PiNS name')
    register_parser.add_argument('name', help='Name to register')
    register_parser.add_argument('wallet_id', help='Wallet ID to own the name')
    register_parser.add_argument('--years', type=int, default=1, help='Registration years')

    wallet_names_parser = subparsers.add_parser('wallet-names', help='List names owned by wallet')
    wallet_names_parser.add_argument('wallet_id', help='Wallet ID to check')

    # DEX commands (basic)
    dex_stats_parser = subparsers.add_parser('dex-stats', help='Get DEX statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize wallet manager
    wallet_manager = WalletManager()

    try:
        if args.command == 'create':
            result = wallet_manager.create_wallet(
                f"wallet_{secrets.token_hex(4)}",
                args.name,
                args.passphrase
            )
            if result['success']:
                print(f"✅ Wallet created: {result['wallet_id']}")
                print(f"   Address: {result['address']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'list':
            wallets = wallet_manager.list_wallets()
            if wallets:
                print("Available wallets:")
                for wallet in wallets:
                    print(f"  {wallet.wallet_id}: {wallet.name} - {wallet.balance:.2f} tokens")
            else:
                print("No wallets found")

        elif args.command == 'info':
            wallet_info = wallet_manager.get_wallet_info(args.wallet_id)
            if wallet_info:
                print(f"Wallet: {wallet_info.name}")
                print(f"ID: {wallet_info.wallet_id}")
                print(f"Address: {wallet_info.address}")
                print(f"Balance: {wallet_info.balance:.2f} tokens")
                print(f"Transactions: {wallet_info.transaction_count}")
                print(f"Cold Storage: {'Yes' if wallet_info.cold_storage else 'No'}")
            else:
                print("Wallet not found")

        elif args.command == 'send':
            result = wallet_manager.send_transaction(
                args.wallet_id, args.recipient, args.amount, args.memo
            )
            if result['success']:
                print(f"✅ Transaction sent: {result['tx_hash']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'backup':
            result = wallet_manager.create_wallet_backup(
                args.wallet_id, passphrase=args.passphrase
            )
            if result['success']:
                print(f"✅ Backup created: {result['backup_path']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'security':
            status = wallet_manager.get_security_status(args.wallet_id)
            print(f"Security Score: {status.security_score}/100")
            print(f"Private Key: {'Present' if status.private_key_present else 'Missing'}")
            print(f"Backup: {'Exists' if status.backup_exists else 'Missing'}")
            print(f"Cold Storage: {'Enabled' if status.cold_storage else 'Disabled'}")
            if status.vulnerabilities:
                print("Vulnerabilities:")
                for vuln in status.vulnerabilities:
                    print(f"  - {vuln}")

        elif args.command == 'trust-create':
            result = wallet_manager.create_trust_fund(
                args.wallet_id, args.trust_type, args.funding
            )
            if result['success']:
                print(f"✅ Trust fund created: {result['trust_id']}")
                print(f"   Type: {result['trust_type']}")
                print(f"   Initial funding: {result['initial_funding']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'trust-fund':
            result = wallet_manager.fund_trust(args.wallet_id, args.trust_id, args.amount)
            if result['success']:
                print(f"✅ Trust funded: {result['amount']} tokens")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'plan-create':
            plan_data = {
                'name': args.name,
                'monthly_cost': args.monthly_cost,
                'features': ['basic_access'],
                'active_subscribers': 0
            }
            result = wallet_manager.create_subscription_plan(
                args.wallet_id, args.trust_id, plan_data
            )
            if result['success']:
                print(f"✅ Plan created: {result['plan_id']}")
                print(f"   Name: {args.name}")
                print(f"   Cost: {args.monthly_cost} tokens/month")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'subscribe':
            result = wallet_manager.subscribe_to_plan(
                args.wallet_id, args.trust_id, args.plan_id
            )
            if result['success']:
                print(f"✅ Subscribed to plan: {result['plan_id']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'grant-create':
            result = wallet_manager.create_foundation_grant(
                args.wallet_id, args.title, args.description,
                args.amount, args.months
            )
            if result['success']:
                print(f"✅ Grant proposal created: {result['grant_id']}")
                print(f"   Title: {result['title']}")
                print(f"   Amount: {result['amount']} tokens")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'grant-vote':
            vote_bool = args.vote == 'yes'
            result = wallet_manager.vote_on_grant(args.wallet_id, args.grant_id, vote_bool)
            if result['success']:
                print(f"✅ Vote cast: {result['vote']}")
            else:
                print(f"❌ Failed: {result['error']}")

        elif args.command == 'trusts':
            trusts = wallet_manager.get_trust_funds()
            if trusts:
                print("Available trust funds:")
                for trust in trusts:
                    print(f"  {trust.get('trust_id', 'unknown')}: {trust.get('balance', 0)} tokens")
            else:
                print("No trust funds available")

        elif args.command == 'check-name':
            result = wallet_manager.check_name_availability(args.name)
            if result.get('available', False):
                print(f"✅ Name '{args.name}' is available")
                print(f"   Registration fee: {result['registration_fee']} tokens")
                print(f"   Estimated confirmation: {result['estimated_confirmation']} seconds")
            else:
                if result.get('registered', False):
                    print(f"❌ Name '{args.name}' is already registered")
                    print(f"   Owner: {result.get('owner', 'unknown')}")
                    print(f"   Registered: {time.ctime(result.get('registered_at', 0))}")
                    if result.get('expires_at'):
                        print(f"   Expires: {time.ctime(result['expires_at'])}")
                else:
                    print(f"❌ Name '{args.name}' is not available: {result.get('error', 'Unknown error')}")

        elif args.command == 'resolve':
            result = wallet_manager.resolve_name(args.name)
            if result.get('resolved', False):
                print(f"✅ Name '{result['name']}' resolves to:")
                print(f"   Address: {result['address']}")
                print(f"   Registered: {time.ctime(result.get('registered_at', 0))}")
                if result.get('expires_at'):
                    print(f"   Expires: {time.ctime(result['expires_at'])}")
            else:
                print(f"❌ Failed to resolve name '{args.name}': {result.get('error', 'Unknown error')}")

        elif args.command == 'register-name':
            result = wallet_manager.register_name(args.name, args.wallet_id, args.years)
            if result.get('success', False):
                print(f"✅ Name '{result['name']}' registered successfully!")
                print(f"   Wallet: {result['wallet_id']}")
                print(f"   Address: {result['address']}")
                print(f"   Fee paid: {result['fee_paid']} tokens")
                print(f"   Years: {result['years']}")
                print(f"   Expires: {time.ctime(result['expires_at'])}")
                print(f"   Status: {result['status']}")
            else:
                print(f"❌ Failed to register name: {result.get('error', 'Unknown error')}")

        elif args.command == 'wallet-names':
            names = wallet_manager.get_wallet_names(args.wallet_id)
            if names:
                print(f"Names registered to wallet {args.wallet_id}:")
                for name_info in names:
                    status = name_info.get('status', 'unknown')
                    status_icon = "✅" if status == 'active' else "⏰"
                    print(f"  {status_icon} {name_info['name']} ({status})")
                    if name_info.get('expires_at'):
                        print(f"     Expires: {time.ctime(name_info['expires_at'])}")
            else:
                print(f"No names registered to wallet {args.wallet_id}")

        elif args.command == 'dex-stats':
            stats = wallet_manager.get_dex_stats()
            if 'error' not in stats:
                print("DEX Statistics:")
                print(f"  Total Pools: {stats.get('total_pools', 0)}")
                print(f"  Total Liquidity: {stats.get('total_liquidity', 0):.2f} tokens")
                print(f"  24h Volume: {stats.get('volume_24h', 0):.2f} tokens")
            else:
                print(f"❌ Failed to get DEX stats: {stats['error']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()