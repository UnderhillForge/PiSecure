"""
Comprehensive tests for wallet_v2.py
=====================================

Tests all Bitcoin Core inspired features:
- HD wallet derivation
- UTXO tracking
- Coin selection algorithms
- Proper encryption
- Address book
- Watch-only mode
- Fee estimation
- SQLite database
- Descriptors
"""

import pytest
import tempfile
import shutil
import secrets
import time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from pisecure.core.wallet_v2 import (
    PiSecureWallet,
    WalletManager,
    HDWalletDerivation,
    CoinSelector,
    UTXO,
    AddressBookEntry,
    SQLiteWalletDB,
    AddressType,
    LegacyScriptPubKeyMan,
    DescriptorScriptPubKeyMan,
)


@pytest.fixture
def temp_wallet_dir():
    """Create temporary directory for test wallets"""
    temp_dir = tempfile.mkdtemp(prefix="pisecure_test_wallet_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def wallet_manager(temp_wallet_dir):
    """Create wallet manager with temp directory"""
    return WalletManager(data_dir=temp_wallet_dir)


@pytest.fixture
def test_wallet(temp_wallet_dir):
    """Create test wallet"""
    return PiSecureWallet("test_wallet", data_dir=temp_wallet_dir)


@pytest.fixture
def master_key():
    """Generate master key for testing"""
    return rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )


# ============================================================================
# HD Wallet Tests
# ============================================================================


class TestHDWallet:
    """Test HD wallet derivation"""

    def test_mnemonic_generation(self):
        """Test mnemonic phrase generation"""
        mnemonic = HDWalletDerivation.generate_mnemonic(256)
        assert mnemonic
        assert len(mnemonic.split()) > 0

    def test_mnemonic_to_seed(self):
        """Test mnemonic to seed conversion"""
        mnemonic = "word0001 word0002 word0003 word0004"
        seed = HDWalletDerivation.mnemonic_to_seed(mnemonic)
        assert len(seed) == 64  # 512 bits

        # Test with passphrase
        seed_with_pass = HDWalletDerivation.mnemonic_to_seed(mnemonic, "test123")
        assert seed != seed_with_pass

    def test_child_key_derivation(self, master_key):
        """Test child key derivation"""
        child1 = HDWalletDerivation.derive_child_key(master_key, 0)
        child2 = HDWalletDerivation.derive_child_key(master_key, 1)

        assert child1 != child2

        # Test hardened derivation
        child_hardened = HDWalletDerivation.derive_child_key(
            master_key, 0, hardened=True
        )
        assert child_hardened != child1

    def test_path_derivation(self, master_key):
        """Test BIP32-style path derivation"""
        # Test standard path
        key1 = HDWalletDerivation.derive_path(master_key, "m/44'/314'/0'/0/0")
        key2 = HDWalletDerivation.derive_path(master_key, "m/44'/314'/0'/0/1")

        assert key1 != key2

        # Test account separation
        account0 = HDWalletDerivation.derive_path(master_key, "m/44'/314'/0'")
        account1 = HDWalletDerivation.derive_path(master_key, "m/44'/314'/1'")
        assert account0 != account1


# ============================================================================
# UTXO Tests
# ============================================================================


class TestUTXO:
    """Test UTXO dataclass and operations"""

    def test_utxo_creation(self):
        """Test UTXO creation"""
        utxo = UTXO(
            tx_hash="abc123",
            output_index=0,
            amount=10.5,
            address="test_address",
            script_pubkey="script",
            confirmations=5,
        )

        assert utxo.outpoint == "abc123:0"
        assert utxo.amount == 10.5
        assert utxo.spendable

    def test_utxo_serialization(self):
        """Test UTXO to_dict"""
        utxo = UTXO(
            tx_hash="abc123",
            output_index=0,
            amount=10.5,
            address="test_address",
            script_pubkey="script",
        )

        utxo_dict = utxo.to_dict()
        assert utxo_dict["tx_hash"] == "abc123"
        assert utxo_dict["amount"] == 10.5


# ============================================================================
# Coin Selection Tests
# ============================================================================


class TestCoinSelection:
    """Test coin selection algorithms"""

    def test_knapsack_selection(self):
        """Test knapsack coin selection"""
        utxos = [
            UTXO("tx1", 0, 1.0, "addr1", "script1", confirmations=6),
            UTXO("tx2", 0, 2.5, "addr2", "script2", confirmations=6),
            UTXO("tx3", 0, 5.0, "addr3", "script3", confirmations=6),
            UTXO("tx4", 0, 10.0, "addr4", "script4", confirmations=6),
        ]

        # Select for 3.0 target
        result = CoinSelector.select_coins_knapsack(utxos, 3.0, fee_rate=0.0001)
        assert result is not None

        selected_utxos, fee = result
        total = sum(u.amount for u in selected_utxos)
        assert total >= 3.0 + fee

    def test_branch_and_bound_selection(self):
        """Test branch and bound (exact match) selection"""
        utxos = [
            UTXO("tx1", 0, 1.0, "addr1", "script1", confirmations=6),
            UTXO("tx2", 0, 2.0, "addr2", "script2", confirmations=6),
            UTXO("tx3", 0, 5.0, "addr3", "script3", confirmations=6),
        ]

        result = CoinSelector.select_coins_branch_and_bound(utxos, 3.0, fee_rate=0.0001)
        assert result is not None

        selected_utxos, fee = result
        total = sum(u.amount for u in selected_utxos)
        assert total >= 3.0

    def test_insufficient_funds(self):
        """Test selection with insufficient funds"""
        utxos = [
            UTXO("tx1", 0, 1.0, "addr1", "script1", confirmations=6),
        ]

        result = CoinSelector.select_coins_knapsack(utxos, 10.0, fee_rate=0.0001)
        # Should return None or select all available
        if result:
            selected_utxos, fee = result
            assert sum(u.amount for u in selected_utxos) < 10.0


# ============================================================================
# Database Tests
# ============================================================================


class TestSQLiteDatabase:
    """Test SQLite database operations"""

    def test_database_creation(self, temp_wallet_dir):
        """Test database initialization"""
        db_path = Path(temp_wallet_dir) / "test.db"
        db = SQLiteWalletDB(str(db_path))

        assert db_path.exists()
        assert db.conn is not None

        db.close()

    def test_key_storage(self, temp_wallet_dir):
        """Test key read/write"""
        db_path = Path(temp_wallet_dir) / "test.db"
        db = SQLiteWalletDB(str(db_path))

        key_data = b"test_key_data"
        assert db.write_key("pubkey_hash_123", key_data)

        retrieved = db.read_key("pubkey_hash_123")
        assert retrieved == key_data

        db.close()

    def test_utxo_storage(self, temp_wallet_dir):
        """Test UTXO read/write"""
        db_path = Path(temp_wallet_dir) / "test.db"
        db = SQLiteWalletDB(str(db_path))

        utxo = UTXO("tx123", 0, 5.0, "addr1", "script1", confirmations=3)
        assert db.write_utxo(utxo.outpoint, utxo)

        utxos = db.list_utxos()
        assert len(utxos) == 1
        assert utxos[0].tx_hash == "tx123"
        assert utxos[0].amount == 5.0

        db.close()

    def test_utxo_marking_spent(self, temp_wallet_dir):
        """Test marking UTXO as spent"""
        db_path = Path(temp_wallet_dir) / "test.db"
        db = SQLiteWalletDB(str(db_path))

        utxo = UTXO("tx123", 0, 5.0, "addr1", "script1")
        db.write_utxo(utxo.outpoint, utxo)

        assert db.mark_utxo_spent(utxo.outpoint)

        utxos = db.list_utxos()
        assert len(utxos) == 0  # Spent UTXOs not returned

        db.close()


# ============================================================================
# ScriptPubKeyManager Tests
# ============================================================================


class TestScriptPubKeyManager:
    """Test key manager implementations"""

    def test_legacy_manager(self, master_key):
        """Test legacy single-key manager"""
        manager = LegacyScriptPubKeyMan(master_key)

        address1 = manager.get_new_address()
        address2 = manager.get_new_address()

        # Legacy manager returns same address
        assert address1 == address2
        assert manager.can_provide(address1)

        pubkey = manager.get_pubkey(address1)
        assert pubkey is not None

    def test_descriptor_manager(self, master_key):
        """Test descriptor-based HD manager"""
        manager = DescriptorScriptPubKeyMan(master_key, "m/44'/314'/0'/0")

        address1 = manager.get_new_address()
        address2 = manager.get_new_address()

        # HD manager returns different addresses
        assert address1 != address2
        assert manager.can_provide(address1)
        assert manager.can_provide(address2)

        pubkey1 = manager.get_pubkey(address1)
        pubkey2 = manager.get_pubkey(address2)
        assert pubkey1 != pubkey2


# ============================================================================
# Wallet Tests
# ============================================================================


class TestWallet:
    """Test main wallet functionality"""

    def test_wallet_creation(self, temp_wallet_dir):
        """Test wallet creation"""
        wallet = PiSecureWallet("test", data_dir=temp_wallet_dir)
        assert wallet.wallet_name == "test"
        assert wallet.database is not None

    def test_watch_only_wallet(self, temp_wallet_dir):
        """Test watch-only wallet"""
        wallet = PiSecureWallet("watch", data_dir=temp_wallet_dir, watch_only=True)
        assert wallet.watch_only

        # Cannot generate addresses in watch-only mode
        with pytest.raises(Exception):
            wallet.get_new_address()

    def test_wallet_encryption(self, test_wallet):
        """Test wallet encryption"""
        passphrase = "test_passphrase_123"

        assert test_wallet.encrypt_wallet(passphrase)
        assert test_wallet.encrypted

        # Cannot encrypt twice
        assert not test_wallet.encrypt_wallet(passphrase)

    def test_wallet_unlock(self, test_wallet):
        """Test wallet unlocking"""
        passphrase = "test_passphrase_123"

        test_wallet.encrypt_wallet(passphrase)
        assert test_wallet.unlock_wallet(passphrase)

    def test_address_generation(self, test_wallet):
        """Test address generation"""
        addr1 = test_wallet.get_new_address("Primary")
        addr2 = test_wallet.get_new_address("Savings")

        # HD wallet generates different addresses
        assert addr1 != addr2

    def test_address_book(self, test_wallet):
        """Test address book operations"""
        test_wallet.add_address_label("addr123", "Alice", "send")

        label = test_wallet.get_address_label("addr123")
        assert label == "Alice"

        # Non-existent address
        assert test_wallet.get_address_label("nonexistent") is None

    def test_balance_calculation(self, test_wallet):
        """Test balance calculation from UTXOs"""
        # Initially zero
        assert test_wallet.get_balance() == 0.0

        # Add test UTXOs to database
        utxo1 = UTXO("tx1", 0, 5.0, "addr1", "script1", confirmations=6)
        utxo2 = UTXO("tx2", 0, 3.5, "addr2", "script2", confirmations=6)

        test_wallet.database.write_utxo(utxo1.outpoint, utxo1)
        test_wallet.database.write_utxo(utxo2.outpoint, utxo2)

        balance = test_wallet.get_balance()
        assert balance == 8.5

    def test_unconfirmed_balance(self, test_wallet):
        """Test unconfirmed balance tracking"""
        # Add confirmed UTXO
        utxo1 = UTXO("tx1", 0, 5.0, "addr1", "script1", confirmations=6)
        test_wallet.database.write_utxo(utxo1.outpoint, utxo1)

        # Add unconfirmed UTXO
        utxo2 = UTXO("tx2", 0, 3.0, "addr2", "script2", confirmations=0)
        test_wallet.database.write_utxo(utxo2.outpoint, utxo2)

        confirmed = test_wallet.get_balance()
        unconfirmed = test_wallet.get_unconfirmed_balance()

        assert confirmed == 5.0
        assert unconfirmed == 3.0

    def test_list_unspent(self, test_wallet):
        """Test listing unspent outputs"""
        utxo1 = UTXO("tx1", 0, 5.0, "addr1", "script1", confirmations=6)
        utxo2 = UTXO("tx2", 0, 3.0, "addr2", "script2", confirmations=0)

        test_wallet.database.write_utxo(utxo1.outpoint, utxo1)
        test_wallet.database.write_utxo(utxo2.outpoint, utxo2)

        # With min_conf=1
        confirmed_utxos = test_wallet.list_unspent(min_conf=1)
        assert len(confirmed_utxos) == 1
        assert confirmed_utxos[0].tx_hash == "tx1"

        # With min_conf=0
        all_utxos = test_wallet.list_unspent(min_conf=0)
        assert len(all_utxos) == 2

    def test_transaction_creation(self, test_wallet):
        """Test transaction creation with coin selection"""
        # Add UTXOs
        utxo1 = UTXO("tx1", 0, 5.0, "addr1", "script1", confirmations=6)
        utxo2 = UTXO("tx2", 0, 3.0, "addr2", "script2", confirmations=6)

        test_wallet.database.write_utxo(utxo1.outpoint, utxo1)
        test_wallet.database.write_utxo(utxo2.outpoint, utxo2)

        # Create transaction
        tx = test_wallet.create_transaction("recipient123", 4.0, fee_rate=0.0001)

        assert tx is not None
        assert tx["type"] == "token_transfer"
        assert len(tx["outputs"]) >= 1  # At least recipient output
        assert any(out["address"] == "recipient123" for out in tx["outputs"])
        assert "signature" in tx or not test_wallet.watch_only

    def test_transaction_with_change(self, test_wallet):
        """Test transaction creates change output"""
        # Add large UTXO
        utxo = UTXO("tx1", 0, 10.0, "addr1", "script1", confirmations=6)
        test_wallet.database.write_utxo(utxo.outpoint, utxo)

        # Send small amount
        tx = test_wallet.create_transaction("recipient123", 2.0, fee_rate=0.0001)

        assert tx is not None
        assert len(tx["outputs"]) == 2  # Recipient + change

        # Find change output
        change_outputs = [
            out for out in tx["outputs"] if out["address"] != "recipient123"
        ]
        assert len(change_outputs) == 1
        assert change_outputs[0]["amount"] > 0

    def test_wallet_backup(self, test_wallet, temp_wallet_dir):
        """Test wallet backup"""
        backup_path = Path(temp_wallet_dir) / "backup.db"

        assert test_wallet.backup_wallet(str(backup_path))
        assert backup_path.exists()


# ============================================================================
# WalletManager Tests
# ============================================================================


class TestWalletManager:
    """Test multi-wallet management"""

    def test_create_wallet(self, wallet_manager):
        """Test wallet creation via manager"""
        wallet = wallet_manager.create_wallet("wallet1")
        assert wallet.wallet_name == "wallet1"
        assert "wallet1" in wallet_manager.wallets

    def test_list_wallets(self, wallet_manager):
        """Test listing wallets"""
        wallet_manager.create_wallet("wallet1")
        wallet_manager.create_wallet("wallet2")

        wallets = wallet_manager.list_wallets()
        assert "wallet1" in wallets
        assert "wallet2" in wallets

    def test_load_wallet(self, wallet_manager):
        """Test loading existing wallet"""
        wallet_manager.create_wallet("wallet1")
        wallet_manager.unload_wallet("wallet1")

        loaded = wallet_manager.load_wallet("wallet1")
        assert loaded is not None
        assert loaded.wallet_name == "wallet1"

    def test_unload_wallet(self, wallet_manager):
        """Test unloading wallet"""
        wallet_manager.create_wallet("wallet1")
        wallet_manager.unload_wallet("wallet1")

        assert "wallet1" not in wallet_manager.wallets


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """End-to-end integration tests"""

    def test_full_wallet_workflow(self, wallet_manager):
        """Test complete wallet workflow"""
        # 1. Create wallet
        wallet = wallet_manager.create_wallet("my_wallet")

        # 2. Encrypt it
        wallet.encrypt_wallet("secure_pass")

        # 3. Generate addresses
        addr1 = wallet.get_new_address("Savings")
        addr2 = wallet.get_new_address("Spending")
        assert addr1 != addr2

        # 4. Add to address book
        wallet.add_address_label("external_addr", "Alice", "send")
        assert wallet.get_address_label("external_addr") == "Alice"

        # 5. Simulate receiving funds (add UTXOs)
        utxo1 = UTXO("tx1", 0, 10.0, addr1, "script1", confirmations=6)
        utxo2 = UTXO("tx2", 0, 5.0, addr2, "script2", confirmations=6)
        wallet.database.write_utxo(utxo1.outpoint, utxo1)
        wallet.database.write_utxo(utxo2.outpoint, utxo2)

        # 6. Check balance
        balance = wallet.get_balance()
        assert balance == 15.0

        # 7. Create transaction
        tx = wallet.create_transaction("recipient", 8.0)
        assert tx is not None
        assert "signature" in tx

        # 8. Backup
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            backup_path = f.name

        assert wallet.backup_wallet(backup_path)

        # Cleanup
        Path(backup_path).unlink()

    def test_watch_only_workflow(self, wallet_manager):
        """Test watch-only wallet workflow"""
        # Create watch-only wallet
        wallet = wallet_manager.create_wallet("watch_wallet", watch_only=True)

        assert wallet.watch_only

        # Can add addresses to watch (simulated)
        wallet.add_address_label("addr_to_watch", "Cold Storage", "receive")

        # Cannot create transactions
        with pytest.raises(Exception):
            wallet.create_transaction("recipient", 5.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
