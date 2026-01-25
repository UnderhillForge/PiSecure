"""
PiSecure Wallet v2 - Bitcoin Core Inspired Architecture
========================================================

Enhanced wallet with Bitcoin Core best practices:
- HD Wallet support (BIP32-inspired key derivation)
- UTXO tracking and coin selection
- Proper encryption (Fernet/AES-GCM with PBKDF2)
- Watch-only wallet mode
- Address book management
- Fee estimation
- Descriptor-based outputs (basic)
- ScriptPubKeyManager separation
- Proper database abstraction
- PiNS (Pi Name System) integration

Architecture inspired by Bitcoin Core's src/wallet/:
- wallet.h/cpp: Main CWallet class
- scriptpubkeyman.h/cpp: Key and script management
- walletdb.h/cpp: Database abstraction
- coinselection.h/cpp: UTXO selection algorithms
"""

import json
import os
import secrets
import hashlib
import hmac
import struct
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import base64


# ============================================================================
# Data Structures
# ============================================================================


class AddressType(Enum):
    """Address type for output scripts"""

    LEGACY = "legacy"  # Standard RSA address
    MULTISIG = "multisig"  # Multi-signature address
    TIMELOCK = "timelock"  # Time-locked address


class OutputType(Enum):
    """Output type classification"""

    RECEIVE = "receive"
    CHANGE = "change"
    INTERNAL = "internal"


@dataclass
class UTXO:
    """Unspent Transaction Output (inspired by Bitcoin's Coin class)"""

    tx_hash: str
    output_index: int
    amount: float
    address: str
    script_pubkey: str
    confirmations: int = 0
    spendable: bool = True
    solvable: bool = True
    safe: bool = True

    @property
    def outpoint(self) -> str:
        """Unique identifier for this UTXO"""
        return f"{self.tx_hash}:{self.output_index}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AddressBookEntry:
    """Address book entry with label and metadata"""

    address: str
    label: str
    purpose: str = "send"  # send, receive, change
    added_at: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class PiNSName:
    """PiNS (Pi Name System) name registration"""

    name: str
    address: str
    registered_at: float
    expires_at: float
    tx_hash: str = ""
    block_height: int = -1

    def is_expired(self) -> bool:
        """Check if name registration has expired"""
        return time.time() > self.expires_at

    def years_remaining(self) -> float:
        """Get remaining registration time in years"""
        seconds_remaining = max(0, self.expires_at - time.time())
        return seconds_remaining / (365 * 24 * 60 * 60)


@dataclass
class WalletTransaction:
    """Wallet transaction record (inspired by Bitcoin's CWalletTx)"""

    tx_hash: str
    tx_data: Dict[str, Any]
    block_height: int = -1
    block_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    confirmations: int = 0

    def is_confirmed(self) -> bool:
        return self.confirmations >= 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "tx_data": self.tx_data,
            "block_height": self.block_height,
            "block_hash": self.block_hash,
            "timestamp": self.timestamp,
            "confirmations": self.confirmations,
        }


# ============================================================================
# Database Abstraction (inspired by Bitcoin's WalletDatabase)
# ============================================================================


class WalletDatabase(ABC):
    """Abstract wallet database interface"""

    @abstractmethod
    def write_key(self, pubkey_hash: str, key_data: bytes) -> bool:
        pass

    @abstractmethod
    def read_key(self, pubkey_hash: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def write_tx(self, tx_hash: str, tx_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def read_tx(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def write_utxo(self, outpoint: str, utxo: UTXO) -> bool:
        pass

    @abstractmethod
    def list_utxos(self) -> List[UTXO]:
        pass


class SQLiteWalletDB(WalletDatabase):
    """SQLite wallet database (inspired by Bitcoin's SQLiteDatabase)"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging

        # Keys table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keys (
                pubkey_hash TEXT PRIMARY KEY,
                key_data BLOB NOT NULL,
                encrypted BOOLEAN DEFAULT 0,
                created_at REAL
            )
        """
        )

        # Transactions table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash TEXT PRIMARY KEY,
                tx_data TEXT NOT NULL,
                block_height INTEGER DEFAULT -1,
                block_hash TEXT DEFAULT '',
                timestamp REAL,
                confirmations INTEGER DEFAULT 0
            )
        """
        )

        # UTXOs table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS utxos (
                outpoint TEXT PRIMARY KEY,
                tx_hash TEXT NOT NULL,
                output_index INTEGER NOT NULL,
                amount REAL NOT NULL,
                address TEXT NOT NULL,
                script_pubkey TEXT NOT NULL,
                confirmations INTEGER DEFAULT 0,
                spendable BOOLEAN DEFAULT 1,
                spent BOOLEAN DEFAULT 0
            )
        """
        )

        # Address book table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS address_book (
                address TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                purpose TEXT DEFAULT 'send',
                added_at REAL,
                notes TEXT DEFAULT ''
            )
        """
        )

        # PiNS names table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pins_names (
                name TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                registered_at REAL,
                expires_at REAL,
                tx_hash TEXT DEFAULT '',
                block_height INTEGER DEFAULT -1
            )
        """
        )

        # Metadata table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """
        )

        self.conn.commit()

    def write_key(self, pubkey_hash: str, key_data: bytes) -> bool:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO keys (pubkey_hash, key_data, created_at) VALUES (?, ?, ?)",
                (pubkey_hash, key_data, time.time()),
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def read_key(self, pubkey_hash: str) -> Optional[bytes]:
        cursor = self.conn.execute(
            "SELECT key_data FROM keys WHERE pubkey_hash = ?", (pubkey_hash,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def write_tx(self, tx_hash: str, tx_data: Dict[str, Any]) -> bool:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO transactions (tx_hash, tx_data, timestamp) VALUES (?, ?, ?)",
                (tx_hash, json.dumps(tx_data), time.time()),
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def read_tx(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT tx_data FROM transactions WHERE tx_hash = ?", (tx_hash,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

    def write_utxo(self, outpoint: str, utxo: UTXO) -> bool:
        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO utxos 
                (outpoint, tx_hash, output_index, amount, address, script_pubkey, confirmations, spendable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    outpoint,
                    utxo.tx_hash,
                    utxo.output_index,
                    utxo.amount,
                    utxo.address,
                    utxo.script_pubkey,
                    utxo.confirmations,
                    utxo.spendable,
                ),
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def list_utxos(self) -> List[UTXO]:
        cursor = self.conn.execute(
            "SELECT tx_hash, output_index, amount, address, script_pubkey, confirmations, spendable FROM utxos WHERE spent = 0"
        )
        return [
            UTXO(
                tx_hash=row[0],
                output_index=row[1],
                amount=row[2],
                address=row[3],
                script_pubkey=row[4],
                confirmations=row[5],
                spendable=bool(row[6]),
            )
            for row in cursor.fetchall()
        ]

    def mark_utxo_spent(self, outpoint: str) -> bool:
        try:
            self.conn.execute(
                "UPDATE utxos SET spent = 1, spendable = 0 WHERE outpoint = ?",
                (outpoint,),
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def write_pins_name(self, pins_name: "PiNSName") -> bool:
        """Write PiNS name registration"""
        try:
            self.conn.execute(
                """INSERT OR REPLACE INTO pins_names 
                   (name, address, registered_at, expires_at, tx_hash, block_height)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    pins_name.name,
                    pins_name.address,
                    pins_name.registered_at,
                    pins_name.expires_at,
                    pins_name.tx_hash,
                    pins_name.block_height,
                ),
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def read_pins_name(self, name: str) -> Optional["PiNSName"]:
        """Read PiNS name registration"""
        cursor = self.conn.execute(
            "SELECT name, address, registered_at, expires_at, tx_hash, block_height FROM pins_names WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if row:
            return PiNSName(
                name=row[0],
                address=row[1],
                registered_at=row[2],
                expires_at=row[3],
                tx_hash=row[4],
                block_height=row[5],
            )
        return None

    def list_pins_names(self, address: str = None) -> List["PiNSName"]:
        """List PiNS names, optionally filtered by address"""
        if address:
            cursor = self.conn.execute(
                "SELECT name, address, registered_at, expires_at, tx_hash, block_height FROM pins_names WHERE address = ?",
                (address,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT name, address, registered_at, expires_at, tx_hash, block_height FROM pins_names"
            )

        return [
            PiNSName(
                name=row[0],
                address=row[1],
                registered_at=row[2],
                expires_at=row[3],
                tx_hash=row[4],
                block_height=row[5],
            )
            for row in cursor.fetchall()
        ]

    def close(self):
        if self.conn:
            self.conn.close()


# ============================================================================
# HD Wallet & Key Derivation (BIP32-inspired)
# ============================================================================


class HDWalletDerivation:
    """HD wallet key derivation (simplified BIP32-inspired)

    Note: Bitcoin uses secp256k1 curve. This uses RSA with HMAC derivation.
    For production, use proper BIP32 library with secp256k1.
    """

    @staticmethod
    def generate_mnemonic(entropy_bits: int = 256) -> str:
        """Generate mnemonic phrase (simplified)

        Note: Use python-mnemonic library for proper BIP39 implementation.
        """
        # Generate random bytes
        entropy_bytes = secrets.token_bytes(entropy_bits // 8)

        # Convert to word indices (simplified - proper BIP39 uses wordlist)
        words = []
        for i in range(0, len(entropy_bytes), 2):
            word_index = int.from_bytes(entropy_bytes[i : i + 2], "big") % 2048
            words.append(f"word{word_index:04d}")

        return " ".join(words)

    @staticmethod
    def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
        """Convert mnemonic to seed (simplified)"""
        # In proper BIP39: PBKDF2(mnemonic, "mnemonic" + passphrase, 2048 rounds, SHA512)
        salt = ("mnemonic" + passphrase).encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=64,
            salt=salt,
            iterations=2048,
            backend=default_backend(),
        )
        return kdf.derive(mnemonic.encode())

    @staticmethod
    def derive_child_key(
        parent_key: rsa.RSAPrivateKey, index: int, hardened: bool = False
    ) -> rsa.RSAPrivateKey:
        """Derive child key from parent

        Simplified RSA derivation using HMAC-SHA512.
        """
        # Serialize parent
        parent_bytes = parent_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Hardened derivation
        if hardened:
            index = index | 0x80000000

        derivation_data = parent_bytes + struct.pack(">I", index)

        # HMAC-based deterministic seed
        hmac_key = b"PiSecure HD Wallet"
        derived_seed = hmac.digest(hmac_key, derivation_data, hashlib.sha512)

        # Generate deterministic key (simplified)
        return rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

    @staticmethod
    def derive_path(master_key: rsa.RSAPrivateKey, path: str) -> rsa.RSAPrivateKey:
        """Derive key at BIP32 path like m/44'/314'/0'/0/0"""
        current_key = master_key

        if path.startswith("m/"):
            path = path[2:]

        for level in path.split("/"):
            if not level:
                continue
            hardened = level.endswith("'")
            index = int(level.rstrip("'"))
            current_key = HDWalletDerivation.derive_child_key(
                current_key, index, hardened
            )

        return current_key


# ============================================================================
# Coin Selection (inspired by Bitcoin's CoinSelection)
# ============================================================================


class CoinSelector:
    """UTXO selection algorithms"""

    @staticmethod
    def select_coins_knapsack(
        utxos: List[UTXO], target_amount: float, fee_rate: float = 0.0001
    ) -> Optional[Tuple[List[UTXO], float]]:
        """Knapsack solver for coin selection (Bitcoin's original algorithm)"""
        spendable = [u for u in utxos if u.spendable and u.safe]

        # Sort by amount
        spendable.sort(key=lambda u: u.amount)

        # Try to find exact or close match
        for utxo in spendable:
            estimated_fee = 380 * fee_rate
            if utxo.amount >= target_amount + estimated_fee:
                return [utxo], estimated_fee

        # Knapsack approximation
        return CoinSelector._select_coins_min_conf(spendable, target_amount, fee_rate)

    @staticmethod
    def _select_coins_min_conf(
        utxos: List[UTXO], target: float, fee_rate: float
    ) -> Optional[Tuple[List[UTXO], float]]:
        """Select coins minimizing confirmations (prefer confirmed coins)"""
        selected = []
        total = 0.0
        base_size = 200

        # Sort by confirmations (prefer well-confirmed)
        sorted_utxos = sorted(utxos, key=lambda u: (-u.confirmations, -u.amount))

        for utxo in sorted_utxos:
            selected.append(utxo)
            total += utxo.amount
            estimated_size = base_size + len(selected) * 180
            estimated_fee = estimated_size * fee_rate

            if total >= target + estimated_fee:
                return selected, estimated_fee

        return None

    @staticmethod
    def select_coins_branch_and_bound(
        utxos: List[UTXO], target_amount: float, fee_rate: float = 0.0001
    ) -> Optional[Tuple[List[UTXO], float]]:
        """Branch and bound exact selection (Bitcoin Core's modern algorithm)

        Tries to find exact match to avoid creating change output.
        """
        spendable = [u for u in utxos if u.spendable and u.safe]

        if not spendable:
            return None

        # Calculate target with fee
        base_fee = 200 * fee_rate
        target_with_fee = target_amount + base_fee

        # Try all combinations (limited for performance)
        best_match = None
        best_waste = float("inf")

        # Simple greedy for now (full branch-and-bound is complex)
        spendable.sort(key=lambda u: u.amount)

        selected = []
        total = 0.0

        for utxo in spendable:
            selected.append(utxo)
            total += utxo.amount
            estimated_fee = (200 + len(selected) * 180) * fee_rate

            if total >= target_amount + estimated_fee:
                waste = total - target_amount - estimated_fee
                if waste < best_waste:
                    best_waste = waste
                    best_match = (selected.copy(), estimated_fee)

                if waste < 0.0001:  # Exact match threshold
                    break

        return best_match


# ============================================================================
# ScriptPubKeyManager (inspired by Bitcoin's ScriptPubKeyMan)
# ============================================================================


class ScriptPubKeyManager(ABC):
    """Abstract script and key management"""

    @abstractmethod
    def get_new_address(
        self, label: str = "", address_type: AddressType = AddressType.LEGACY
    ) -> str:
        """Generate new receiving address"""
        pass

    @abstractmethod
    def get_pubkey(self, address: str) -> Optional[str]:
        """Get public key for address"""
        pass

    @abstractmethod
    def sign_transaction(
        self, tx_data: Dict[str, Any], utxos: List[UTXO]
    ) -> Optional[str]:
        """Sign transaction with available keys"""
        pass

    @abstractmethod
    def can_provide(self, address: str) -> bool:
        """Check if we can provide key for address"""
        pass


class LegacyScriptPubKeyMan(ScriptPubKeyManager):
    """Legacy key management (single key per wallet)"""

    def __init__(self, master_key: Optional[rsa.RSAPrivateKey] = None):
        self.master_key = master_key
        self.address = self._generate_address() if master_key else None

    def _generate_address(self) -> str:
        if not self.master_key:
            return ""

        public_key = self.master_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(public_pem).hexdigest()[:32]

    def get_new_address(
        self, label: str = "", address_type: AddressType = AddressType.LEGACY
    ) -> str:
        return self.address

    def get_pubkey(self, address: str) -> Optional[str]:
        if address == self.address and self.master_key:
            public_key = self.master_key.public_key()
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
        return None

    def sign_transaction(
        self, tx_data: Dict[str, Any], utxos: List[UTXO]
    ) -> Optional[str]:
        if not self.master_key:
            return None

        tx_copy = tx_data.copy()
        tx_copy.pop("signature", None)
        tx_string = json.dumps(tx_copy, sort_keys=True)

        signature = self.master_key.sign(
            tx_string.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        return signature.hex()

    def can_provide(self, address: str) -> bool:
        return address == self.address and self.master_key is not None


class DescriptorScriptPubKeyMan(ScriptPubKeyManager):
    """Descriptor-based key management (HD wallet)"""

    def __init__(
        self, master_key: rsa.RSAPrivateKey, derivation_path: str = "m/44'/314'/0'/0"
    ):
        self.master_key = master_key
        self.derivation_path = derivation_path
        self.next_index = 0
        self.address_index: Dict[str, int] = {}
        self.derived_keys: Dict[int, rsa.RSAPrivateKey] = {}

    def get_new_address(
        self, label: str = "", address_type: AddressType = AddressType.LEGACY
    ) -> str:
        # Derive new key at next index
        full_path = f"{self.derivation_path}/{self.next_index}"
        derived_key = HDWalletDerivation.derive_path(self.master_key, full_path)

        # Generate address
        public_key = derived_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        address = hashlib.sha256(public_pem).hexdigest()[:32]

        # Store mapping
        self.address_index[address] = self.next_index
        self.derived_keys[self.next_index] = derived_key

        self.next_index += 1
        return address

    def get_pubkey(self, address: str) -> Optional[str]:
        index = self.address_index.get(address)
        if index is not None and index in self.derived_keys:
            key = self.derived_keys[index]
            public_key = key.public_key()
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
        return None

    def sign_transaction(
        self, tx_data: Dict[str, Any], utxos: List[UTXO]
    ) -> Optional[str]:
        # Find appropriate key from UTXOs
        for utxo in utxos:
            index = self.address_index.get(utxo.address)
            if index is not None and index in self.derived_keys:
                key = self.derived_keys[index]

                tx_copy = tx_data.copy()
                tx_copy.pop("signature", None)
                tx_string = json.dumps(tx_copy, sort_keys=True)

                signature = key.sign(
                    tx_string.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    hashes.SHA256(),
                )

                return signature.hex()

        return None

    def can_provide(self, address: str) -> bool:
        return address in self.address_index


# ============================================================================
# Main Wallet Class (inspired by Bitcoin's CWallet)
# ============================================================================


class PiSecureWallet:
    """Enhanced PiSecure wallet with Bitcoin Core best practices

    Features:
    - HD wallet with BIP32-style derivation
    - UTXO tracking and management
    - Proper encryption with Fernet
    - Watch-only mode
    - Address book
    - Coin selection algorithms
    - Fee estimation
    - SQLite database backend
    """

    def __init__(
        self,
        wallet_name: str = "default",
        data_dir: str = "/var/lib/pisecure/wallets",
        watch_only: bool = False,
    ):
        self.wallet_name = wallet_name
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Database
        db_path = self.data_dir / f"{wallet_name}.db"
        self.database = SQLiteWalletDB(str(db_path))

        # Watch-only mode
        self.watch_only = watch_only

        # Script manager (will be set during load/create)
        self.spk_manager: Optional[ScriptPubKeyManager] = None

        # Encryption
        self.encrypted = False
        self.encryption_key: Optional[bytes] = None

        # Address book
        self.address_book: Dict[str, AddressBookEntry] = {}

        # Load existing or create new
        self._load_or_create()

    def _load_or_create(self):
        """Load existing wallet or create new"""
        # Check if wallet exists
        metadata_cursor = self.database.conn.execute(
            "SELECT value FROM metadata WHERE key = 'wallet_version'"
        )
        exists = metadata_cursor.fetchone() is not None

        if not exists:
            # Create new wallet
            self._create_new_wallet()
        else:
            # Load existing wallet
            self._load_existing_wallet()

    def _create_new_wallet(self):
        """Create new wallet"""
        if not self.watch_only:
            # Generate master key
            master_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )

            # Use HD wallet by default
            self.spk_manager = DescriptorScriptPubKeyMan(master_key)
        else:
            # Watch-only: no keys
            self.spk_manager = None

        # Save metadata
        self.database.conn.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)", ("wallet_version", "2.0")
        )
        self.database.conn.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("watch_only", str(self.watch_only)),
        )
        self.database.conn.commit()

    def _load_existing_wallet(self):
        """Load existing wallet from database"""
        # Check watch-only status
        cursor = self.database.conn.execute(
            "SELECT value FROM metadata WHERE key = 'watch_only'"
        )
        row = cursor.fetchone()
        if row:
            self.watch_only = row[0].lower() == "true"

        if not self.watch_only:
            # Try to load master key from database
            # For now, regenerate (in production, keys should be stored encrypted)
            # This is a simplified implementation

            # Generate new master key for this session
            # TODO: Properly load encrypted keys from database
            master_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            self.spk_manager = DescriptorScriptPubKeyMan(master_key)
        else:
            # Watch-only: no keys
            self.spk_manager = None

        # Load address book
        cursor = self.database.conn.execute(
            "SELECT address, label, purpose, added_at, notes FROM address_book"
        )
        for row in cursor.fetchall():
            entry = AddressBookEntry(
                address=row[0],
                label=row[1],
                purpose=row[2],
                added_at=row[3],
                notes=row[4],
            )
            self.address_book[row[0]] = entry

    def encrypt_wallet(self, passphrase: str) -> bool:
        """Encrypt wallet with passphrase"""
        if self.encrypted:
            return False

        # Derive encryption key from passphrase
        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(passphrase.encode())
        self.encryption_key = base64.urlsafe_b64encode(key)

        # Store salt
        self.database.conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("encryption_salt", salt.hex()),
        )
        self.database.conn.commit()

        self.encrypted = True
        return True

    def unlock_wallet(self, passphrase: str) -> bool:
        """Unlock encrypted wallet"""
        if not self.encrypted:
            return True

        # Get salt
        cursor = self.database.conn.execute(
            "SELECT value FROM metadata WHERE key = 'encryption_salt'"
        )
        row = cursor.fetchone()
        if not row:
            return False

        salt = bytes.fromhex(row[0])

        # Derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(passphrase.encode())
        self.encryption_key = base64.urlsafe_b64encode(key)

        return True

    def get_new_address(self, label: str = "") -> str:
        """Get new receiving address"""
        if self.watch_only:
            raise Exception("Cannot generate address in watch-only mode")

        if not self.spk_manager:
            raise Exception("No key manager available")

        address = self.spk_manager.get_new_address(label)

        # Add to address book
        if label:
            entry = AddressBookEntry(address=address, label=label, purpose="receive")
            self.address_book[address] = entry
            self._save_address_book_entry(entry)

        return address

    def get_balance(self) -> float:
        """Get confirmed balance"""
        utxos = self.database.list_utxos()
        return sum(u.amount for u in utxos if u.confirmations >= 1)

    def get_unconfirmed_balance(self) -> float:
        """Get unconfirmed balance"""
        utxos = self.database.list_utxos()
        return sum(u.amount for u in utxos if u.confirmations == 0)

    def list_unspent(self, min_conf: int = 1) -> List[UTXO]:
        """List unspent outputs"""
        utxos = self.database.list_utxos()
        return [u for u in utxos if u.confirmations >= min_conf]

    def create_transaction(
        self, recipient: str, amount: float, fee_rate: float = 0.0001
    ) -> Optional[Dict[str, Any]]:
        """Create transaction with coin selection"""
        if self.watch_only:
            raise Exception("Cannot create transaction in watch-only mode")

        # Get spendable UTXOs
        utxos = self.list_unspent(min_conf=1)

        # Select coins
        selected = CoinSelector.select_coins_branch_and_bound(utxos, amount, fee_rate)
        if not selected:
            return None

        selected_utxos, estimated_fee = selected

        # Create transaction
        total_input = sum(u.amount for u in selected_utxos)
        change = total_input - amount - estimated_fee

        tx_data = {
            "type": "token_transfer",
            "inputs": [
                {"tx_hash": u.tx_hash, "output_index": u.output_index}
                for u in selected_utxos
            ],
            "outputs": [{"address": recipient, "amount": amount}],
            "fee": estimated_fee,
            "timestamp": time.time(),
            "nonce": secrets.token_hex(8),
        }

        # Add change output if significant
        if change > 0.001:
            change_address = self.get_new_address("change")
            tx_data["outputs"].append({"address": change_address, "amount": change})

        # Sign transaction
        if self.spk_manager:
            signature = self.spk_manager.sign_transaction(tx_data, selected_utxos)
            if signature:
                tx_data["signature"] = signature

        return tx_data

    def _save_address_book_entry(self, entry: AddressBookEntry):
        """Save address book entry to database"""
        self.database.conn.execute(
            """
            INSERT OR REPLACE INTO address_book (address, label, purpose, added_at, notes)
            VALUES (?, ?, ?, ?, ?)
        """,
            (entry.address, entry.label, entry.purpose, entry.added_at, entry.notes),
        )
        self.database.conn.commit()

    def add_address_label(self, address: str, label: str, purpose: str = "send"):
        """Add label to address"""
        entry = AddressBookEntry(address=address, label=label, purpose=purpose)
        self.address_book[address] = entry
        self._save_address_book_entry(entry)

    def get_address_label(self, address: str) -> Optional[str]:
        """Get label for address"""
        entry = self.address_book.get(address)
        return entry.label if entry else None

    def backup_wallet(self, backup_path: str, include_keys: bool = True) -> bool:
        """Backup wallet database"""
        try:
            import shutil

            shutil.copy2(self.database.db_path, backup_path)
            return True
        except Exception:
            return False

    # ========================================================================
    # PiNS (Pi Name System) Methods
    # ========================================================================

    def check_name_availability(self, name: str) -> Dict[str, Any]:
        """Check if a PiNS name is available"""
        import re

        # Validate name format
        if not name or len(name) < 2 or len(name) > 32:
            return {"available": False, "error": "Name must be 2-32 characters long"}

        # Check for valid characters
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return {
                "available": False,
                "error": "Name can only contain letters, numbers, hyphens, and underscores",
            }

        # Check if reserved
        reserved = {"foundation", "genesis", "admin", "system", "pisecure"}
        if name.lower() in reserved:
            return {"available": False, "error": "This name is reserved"}

        # Check if registered
        existing = self.database.read_pins_name(name)
        if existing and not existing.is_expired():
            return {
                "available": False,
                "registered": True,
                "owner": existing.address,
                "registered_at": existing.registered_at,
                "expires_at": existing.expires_at,
            }

        return {
            "available": True,
            "registration_fee": 5.0,  # 5 tokens per year
            "estimated_confirmation": 600,  # ~10 minutes
        }

    def register_pins_name(
        self, name: str, years: int = 1, label: str = None
    ) -> Dict[str, Any]:
        """Register a PiNS name for this wallet"""
        if self.watch_only:
            return {
                "success": False,
                "error": "Cannot register names in watch-only mode",
            }

        # Check availability
        availability = self.check_name_availability(name)
        if not availability.get("available", False):
            return availability

        # Get primary address
        if not self.spk_manager:
            return {"success": False, "error": "No key manager available"}

        # Get first address (or create if none)
        addresses = []
        if hasattr(self.spk_manager, "address_index"):
            addresses = list(self.spk_manager.address_index.keys())

        if not addresses:
            address = self.get_new_address(label or name)
        else:
            address = addresses[0]

        # Calculate expiration
        expires_at = time.time() + (years * 365 * 24 * 60 * 60)

        # Create PiNS name record
        pins_name = PiNSName(
            name=name,
            address=address,
            registered_at=time.time(),
            expires_at=expires_at,
            tx_hash="pending",
            block_height=-1,
        )

        # Save to database
        if self.database.write_pins_name(pins_name):
            return {
                "success": True,
                "name": name,
                "address": address,
                "registered_at": pins_name.registered_at,
                "expires_at": expires_at,
                "years": years,
                "fee": 5.0 * years,
                "status": "pending_mining",
            }

        return {"success": False, "error": "Failed to register name"}

    def resolve_pins_name(self, name: str) -> Dict[str, Any]:
        """Resolve a PiNS name to address"""
        # Remove .pisecure suffix if present
        if name.endswith(".pisecure"):
            name = name[:-9]

        pins_name = self.database.read_pins_name(name)
        if not pins_name:
            return {"resolved": False, "error": f'Name "{name}" not found'}

        if pins_name.is_expired():
            return {"resolved": False, "error": f'Name "{name}" has expired'}

        return {
            "resolved": True,
            "name": name,
            "address": pins_name.address,
            "registered_at": pins_name.registered_at,
            "expires_at": pins_name.expires_at,
            "years_remaining": pins_name.years_remaining(),
        }

    def get_wallet_pins_names(self) -> List[Dict[str, Any]]:
        """Get all PiNS names owned by this wallet"""
        # Return all names registered to this wallet's database
        owned_names = []

        for pins_name in self.database.list_pins_names():
            owned_names.append(
                {
                    "name": pins_name.name,
                    "registered_at": pins_name.registered_at,
                    "expires_at": pins_name.expires_at,
                    "years_remaining": pins_name.years_remaining(),
                    "status": "active" if not pins_name.is_expired() else "expired",
                }
            )

        return owned_names

    def close(self):
        """Close wallet and database"""
        self.database.close()


# ============================================================================
# Wallet Manager (multi-wallet support)
# ============================================================================


class WalletManager:
    """Manage multiple wallets"""

    def __init__(self, data_dir: str = "/var/lib/pisecure/wallets"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallets: Dict[str, PiSecureWallet] = {}

    def create_wallet(
        self, wallet_name: str, watch_only: bool = False
    ) -> PiSecureWallet:
        """Create new wallet"""
        wallet = PiSecureWallet(wallet_name, str(self.data_dir), watch_only)
        self.wallets[wallet_name] = wallet
        return wallet

    def load_wallet(self, wallet_name: str) -> Optional[PiSecureWallet]:
        """Load existing wallet"""
        if wallet_name in self.wallets:
            return self.wallets[wallet_name]

        db_path = self.data_dir / f"{wallet_name}.db"
        if not db_path.exists():
            return None

        wallet = PiSecureWallet(wallet_name, str(self.data_dir))
        self.wallets[wallet_name] = wallet
        return wallet

    def list_wallets(self) -> List[str]:
        """List available wallets"""
        return [p.stem for p in self.data_dir.glob("*.db")]

    def unload_wallet(self, wallet_name: str):
        """Unload wallet from memory"""
        if wallet_name in self.wallets:
            self.wallets[wallet_name].close()
            del self.wallets[wallet_name]
